"""Annotate the pinned Isaac Lab recorder's exports; no alternate trajectory format."""
import copy
import json
import time


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
    def __init__(self, env, metadata):
        self.env=env;self.manager=env.recorder_manager;self.metadata=metadata
        self.active=False;self.episode_meta=None;self.saved=0;self.reason=None
        self.original_export=self.manager.export_episodes
        # Intercept the standard export also used by automatic terminal pre_reset.
        self.manager.export_episodes=self.export
        self.manager.cfg.export_in_record_pre_reset=True
        self._header()

    def _header(self):
        handler=self.manager._dataset_file_handler
        handler._hdf5_file_stream.attrs['toast_scenario_metadata']=json.dumps(self.metadata)
        handler.flush()

    def start(self, episode_number, poses, seed):
        self.episode_meta=copy.deepcopy({k:v for k,v in self.metadata.items() if k!='episodes'})
        self.episode_meta.update(episode_number=episode_number,applied_reset_poses=poses,seed=seed,
                                 started_unix=time.time())
        self.metadata['applied_reset_poses']=poses
        self.manager.get_episode(0).seed=seed
        self.active=True;self.reason=None;self._header()

    def export(self, env_ids=None):
        if not self.active:
            self.manager.reset(env_ids);return
        ep=self.manager.get_episode(0)
        if trim_complete_steps(ep.data)==0:
            self.manager.reset(env_ids);self.active=False;return
        observed=bool(ep.success)
        terms={}
        for name in self.env.termination_manager.active_terms:
            terms[name]=bool(self.env.termination_manager.get_term(name)[0])
        reason=self.reason or ('environment_termination' if any(terms.values()) else 'manual_stop')
        ep.success=False  # diagnostic data is never presented as a success demonstration
        handler=self.manager._dataset_file_handler
        index=handler.demo_count
        self.original_export(env_ids)
        group=handler._hdf5_file_stream['data'][f'demo_{index}']
        group.attrs['diagnostic']=True
        group.attrs['task_success_observed']=observed or bool(terms.get('success'))
        group.attrs['success']=False
        for key in ('operator','scenario_id','manifest_sha256','seed'):
            group.attrs[key]=self.episode_meta[key]
        info=dict(self.episode_meta,end_reason=reason,termination_terms=terms,ended_unix=time.time())
        group.attrs['toast_episode_metadata']=json.dumps(info)
        self.metadata.setdefault('episodes',[]).append(info)
        self._header();self.active=False;self.saved+=1
        print(f'RECORD_SAVED demo_{index} frames={len(group["actions"])} success=False reason={reason}',flush=True)

    def finish(self,reason):
        if self.active:
            self.reason=reason
            # Standard pre_reset evaluates the original success term before our export.
            self.manager.record_pre_reset([0],force_export_or_skip=True)

    def close(self):
        self.manager._dataset_file_handler.close()
