"""Annotate the pinned Isaac Lab recorder's exports; no alternate trajectory format."""
import copy
from episode_control import episode_result
import json
import time
from pathlib import Path


def trim_complete_steps(data):
    """Ctrl+C may interrupt between pre_step and post_step. Keep only complete rows."""
    def leaves(value):
        if isinstance(value,dict):
            for child in value.values():yield from leaves(child)
        else:yield value
    if not all(k in data for k in ('actions','obs','states')):return 0
    def complete(schema,value):
        return all(k in value and (not isinstance(v,dict) or complete(v,value[k])) for k,v in schema.items())
    if not complete(data.get('initial_state',{}),data['states']):return 0
    groups=[k for k in ('actions','obs','states','processed_actions','timing') if k in data]
    lengths=[len(v) for k in groups for v in leaves(data[k])]
    n=min(lengths,default=0)
    def trim(value):
        return {k:trim(v) for k,v in value.items()} if isinstance(value,dict) else value[:n]
    for k in groups:data[k]=trim(data[k])
    return n


class DiagnosticRecorder:
    def __init__(self, env, metadata, lifecycle=None):
        self.lifecycle=lifecycle
        from episode_video import EpisodeVideo, CAMERAS
        self.video_type=EpisodeVideo;self.camera_names=CAMERAS
        self.env=env;self.manager=env.recorder_manager;self.metadata=metadata
        self.active=False;self.episode_meta=None;self.saved=0;self.reason=None
        self.video=None;self.episode_id=None
        self.directory=Path(metadata["record_directory"])
        self.original_post_step=self.manager.record_post_step
        self.manager.record_post_step=self.record_post_step
        self.original_export=self.manager.export_episodes
        # Intercept the standard export also used by automatic terminal pre_reset.
        self.manager.export_episodes=self.export
        self.manager.cfg.export_in_record_pre_reset=True
        self._header()

    def _header(self):
        handler=self.manager._dataset_file_handler
        handler._hdf5_file_stream.attrs['toast_scenario_metadata']=json.dumps(self.metadata)
        handler.flush()

    def record_post_step(self):
        self.original_post_step()
        if not self.active:return
        data=self.manager.get_episode(0).data
        images={name:data["obs"][name][-1].detach().cpu().numpy() for name in self.camera_names}
        self.video.submit(images,len(data["actions"])-1,
                          float(data["timing"]["wall_monotonic"][-1].item()),
                          float(data["timing"]["simulation_time"][-1].item()))

    def start(self, episode_number, poses, seed):
        if self.active:raise RuntimeError("Previous recording is still active")
        self.episode_id=f"episode_{episode_number:06d}"
        self.video=self.video_type(self.directory/self.episode_id,self.episode_id,self.metadata["timing"]["control_dt"])
        self.episode_meta=copy.deepcopy({k:v for k,v in self.metadata.items() if k!='episodes'})
        self.episode_meta.update(episode_id=self.episode_id,episode_number=episode_number,applied_reset_poses=poses,seed=seed,
                                 started_unix=time.time())
        self.metadata['applied_reset_poses']=poses
        self.manager.get_episode(0).seed=seed
        self.active=True;self.reason=None;self._header()
        print(f"RECORD_STARTED {self.episode_id} dataset={self.directory / 'dataset.hdf5'} video={self.video.directory / 'video.mp4'}",flush=True)

    def export(self, env_ids=None):
        if not self.active:
            self.manager.reset(env_ids);return
        ep=self.manager.get_episode(0)
        samples=trim_complete_steps(ep.data)
        terms={name:bool(self.env.termination_manager.get_term(name)[0])
               for name in self.env.termination_manager.active_terms}
        pending=self.lifecycle.pending_result if self.lifecycle else None
        result=episode_result(self.reason,terms) if self.reason else (pending or episode_result(terms=terms))
        terms=result['termination_terms'];reason=result['reason']
        ep.success=result['success']
        video=self.video.close()
        print("VIDEO_FINALIZED "+json.dumps(dict(path=str(self.video.directory),**video)),flush=True)
        info=dict(self.episode_meta,end_reason=reason,termination_terms=terms,ended_unix=time.time(),
                  task_success_observed=ep.success,episode_result=result,samples=samples,video=video)
        if not samples:
            info.update(data_group=None)
            self.metadata.setdefault('episodes',[]).append(info)
            (self.video.directory/'episode.json').write_text(json.dumps(info,indent=2)+'\n')
            self.manager.reset(env_ids);self.active=False;self._header();return
        handler=self.manager._dataset_file_handler
        index=handler.demo_count
        self.original_export(env_ids)
        group=handler._hdf5_file_stream['data'][f'demo_{index}']
        group.attrs['diagnostic']=True
        group.attrs['task_success_observed']=result['success']
        group.attrs['success']=result['success']
        group.attrs['episode_id']=self.episode_id
        group.attrs['video_file']=f'{self.episode_id}/video.mp4'
        for key in ('operator','scenario_id','manifest_sha256','seed'):
            group.attrs[key]=self.episode_meta[key]
        info['data_group']=f'demo_{index}'
        (self.video.directory/'episode.json').write_text(json.dumps(info,indent=2)+'\n')
        group.attrs['toast_episode_metadata']=json.dumps(info)
        self.metadata.setdefault('episodes',[]).append(info)
        self._header();self.active=False;self.saved+=1
        print(f'RECORD_SAVED demo_{index} frames={len(group["actions"])} success={bool(group.attrs["success"])} reason={reason} path={self.directory}',flush=True)

    def finish(self,reason):
        if self.active:
            self.reason=reason
            # Standard pre_reset evaluates the original success term before our export.
            self.manager.record_pre_reset([0],force_export_or_skip=True)

    def close(self):
        try:
            if self.video:self.video.close()
        finally:
            self.manager.record_post_step=self.original_post_step
            self.manager.export_episodes=self.original_export
            self.manager._dataset_file_handler.close()
