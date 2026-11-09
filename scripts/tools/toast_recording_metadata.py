"""Scenario provenance for standard Isaac Lab HDF5 diagnostics; no alternate recorder."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / 'scenario_delivery/manifest_bread_slot.json'
TASK = 'Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2'
ATTRIBUTE = 'toast_scenario_metadata'


def validate_recording_args(args):
    if args.record_dir and (args.operator is None or args.scenario_index is None):
        raise ValueError('Diagnostic recording requires --operator and --scenario_index')
    if args.record_dir and args.preview_only:
        raise ValueError('Recording requires active control, not --preview-only')
    if not 0 <= args.record_seconds <= 3600:
        raise ValueError('--record-seconds must be in [0,3600]; 0 means manual stop')
    if args.record_dir and Path(args.record_dir).exists():
        raise ValueError('Record directory already exists; choose a new path')


def ready_to_record(snapshot, states):
    return bool(snapshot.get('live') and (snapshot.get('packet') or {}).get('preview_ok')
                and set(states)=={'left','right'} and all(s['reason']=='ready' for s in states.values()))


def verify_static_rack(env, metadata):
    import torch
    position,quaternion=env.scene['bread_shelf'].get_world_poses()
    target=metadata['initial_static_rack_pose']
    p=torch.tensor([target['position_m']],device=env.device).expand(env.num_envs,-1)
    q=torch.tensor([target['quaternion_wxyz']],device=env.device).expand(env.num_envs,-1)
    torch.testing.assert_close(position-env.scene.env_origins,p,atol=5e-5,rtol=0)
    alignment=(quaternion*q).sum(-1).abs()
    torch.testing.assert_close(alignment,torch.ones_like(alignment),atol=5e-5,rtol=0)
    print('STATIC_RACK_POSE_OK '+metadata['scenario_id'],flush=True)


def manifest_bytes(path):
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    ids = [s['id'] for s in data['scenarios']]
    if data['schema_version'] != 2 or len(ids) != len(set(ids)):
        raise ValueError('Invalid fixed scenario manifest')
    return raw, data


def create_diagnostic(directory, manifest, operator, scenario_id, scenario_index, seed=None):
    raw, data = manifest_bytes(manifest)
    entries = [s for s in data['scenarios'] if s['id'] == scenario_id]
    if len(entries) != 1 or entries[0]['operator'] != operator:
        raise ValueError('Selected scenario/operator does not match manifest')
    metadata = dict(schema_version=1, kind='quest_diagnostic_not_success_demonstration',
                    task=TASK, operator=operator, scenario_index=scenario_index, seed=seed,
                    scenario_id=scenario_id, manifest_sha256=hashlib.sha256(raw).hexdigest(),
                    manifest_file='manifest.json', initial_static_rack_pose=entries[0]['poses']['bread_shelf'],
                    action_order=['left_wrist_delta_6','right_wrist_delta_6','left_gripper','right_gripper','lift'],
                    observation_timing='pre_action', state_timing='post_action',
                    recording_state='WAITING_FOR_START', diagnostic_success=False)
    if 'scenario_group' in entries[0]:
        metadata.update({k: entries[0][k] for k in ('scenario_group','group_index','operator_index')})
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    (directory/'manifest.json').write_bytes(raw)
    (directory/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return directory, metadata


def scenario_for_replay(directory, metadata, task):
    if metadata.get('schema_version') != 1 or metadata.get('task') != task or task != TASK:
        raise ValueError('Diagnostic metadata task/schema mismatch')
    if metadata.get('manifest_file') != 'manifest.json':
        raise ValueError('Expected adjacent manifest.json snapshot')
    path = Path(directory).resolve()/'manifest.json'
    raw, data = manifest_bytes(path)
    if hashlib.sha256(raw).hexdigest() != metadata['manifest_sha256']:
        raise ValueError('Manifest snapshot hash mismatch; refusing default-layout replay')
    entry = next((s for s in data['scenarios'] if s['id']==metadata['scenario_id']), None)
    if entry is None or entry['operator'] != metadata['operator']:
        raise ValueError('Scenario/operator metadata mismatch')
    if entry['poses']['bread_shelf'] != metadata['initial_static_rack_pose']:
        raise ValueError('Static rack metadata mismatch')
    return metadata['scenario_id'], str(path)


def configure_replay(dataset_file, cfg, task):
    import h5py
    with h5py.File(dataset_file,'r') as dataset:
        if ATTRIBUTE not in dataset.attrs:
            # New diagnostic files also carry an episode flag; fail closed if provenance was lost.
            if any(ep.attrs.get('diagnostic',False) for ep in dataset['data'].values()):
                raise ValueError('Diagnostic scenario metadata is missing')
            sidecar=Path(dataset_file).parent/'metadata.json'
            if sidecar.exists() and json.loads(sidecar.read_text()).get('kind')=='quest_diagnostic_not_success_demonstration':
                raise ValueError('Diagnostic metadata sidecar exists but HDF5 is not finalized')
            return  # Legacy recordings retain their existing behavior.
        metadata=json.loads(dataset.attrs[ATTRIBUTE])
    scenario_id, manifest = scenario_for_replay(Path(dataset_file).parent,metadata,task)
    cfg.scenario_id, cfg.scenario_manifest = scenario_id, manifest
    if metadata.get('seed') is not None: cfg.seed = metadata['seed']
    cfg.diagnostic_scenario_metadata = metadata
    timing=metadata['timing']
    actual=dict(physics_dt=cfg.sim.dt,decimation=cfg.decimation,render_interval=cfg.sim.render_interval)
    if any(actual[k]!=timing[k] for k in actual):
        raise ValueError(f'Replay timing mismatch: {actual} != {timing}')
    print(f'SCENARIO_REPLAY {scenario_id} seed={metadata.get("seed")} manifest={manifest} manifest_sha256={metadata["manifest_sha256"]}',flush=True)
    return metadata


def finalize_diagnostic(directory, metadata):
    """Annotate the existing recorder output AFTER the recorder writer is closed, never replace it."""
    import h5py
    directory=Path(directory);dataset_file=directory/'dataset.hdf5'
    metadata=dict(metadata)
    if dataset_file.exists():
        with h5py.File(dataset_file,'r+') as dataset:
            for episode in dataset['data'].values():
                # Keep the actual task outcome separately; diagnostic export never claims a success demo.
                episode.attrs['task_success_observed']=bool(episode.attrs.get('task_success_observed',episode.attrs.get('success',False)))
                episode.attrs['success']=False
                episode.attrs['diagnostic']=True
                for key in ('operator','scenario_id','manifest_sha256'):
                    episode.attrs[key]=metadata[key]
            metadata['episode_count']=len(dataset['data'])
            metadata['frames']=sum(len(ep['actions']) for ep in dataset['data'].values() if 'actions' in ep)
            metadata['recording_state']='SAVED' if metadata['frames'] else 'NO_FRAMES_SAVED'
            dataset.attrs[ATTRIBUTE]=json.dumps(metadata)
    else:
        metadata['recording_state']='NO_DATASET_CREATED'
    (directory/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata


def inspect_diagnostic(dataset_file):
    import h5py
    import numpy as np
    report={'file':str(Path(dataset_file).resolve()),'episodes':{}}
    with h5py.File(dataset_file,'r') as dataset:
        metadata=json.loads(dataset.attrs[ATTRIBUTE])
        scenario_for_replay(Path(dataset_file).parent,metadata,metadata['task'])
        report['metadata']=metadata
        for name,ep in dataset['data'].items():
            n=len(ep['actions']);assert n>0 and ep['actions'].shape==(n,15)
            assert not bool(ep.attrs['success']) and bool(ep.attrs['diagnostic'])
            for key in ('scenario_id','manifest_sha256','seed'):
                assert ep.attrs[key]==metadata[key],(name,key,'metadata mismatch')
            assert 'toast_episode_metadata' in ep.attrs
            for key in ('wall_monotonic','simulation_time'):
                times=ep['timing/'+key][:].reshape(-1)
                assert len(times)==n and np.isfinite(times).all()
                assert (np.diff(times)>0).all(),(name,key,'non-increasing time')
            assert 'initial_state/toast_cycle' in ep and 'states/toast_cycle' in ep
            assert 'initial_state/articulation/robot/root_pose' in ep
            assert 'states/rigid_object/bread_0/root_pose' in ep
            shapes={}
            def visit(key,value):
                if isinstance(value,h5py.Dataset):
                    shapes[key]={'shape':list(value.shape),'dtype':str(value.dtype)}
                    if key.startswith(('obs/','states/')):assert len(value)==n,(name,key,value.shape,n)
            ep.visititems(visit)
            cameras={}
            for cam in ('head_cam','left_wrist_cam','right_wrist_cam'):
                image=ep['obs/'+cam];assert image.shape==(n,244,244,3) and image.dtype==np.uint8
                frame=image[0];cameras[cam]={'first_min':int(frame.min()),'first_max':int(frame.max()),'first_std':float(frame.std())}
            action=ep['actions'][:];assert np.isfinite(action).all()
            report['episodes'][name]={'frames':n,'shapes':shapes,'cameras':cameras,
                                     'max_abs_arm_action':float(np.abs(action[:,:12]).max()),
                                     'nonzero_arm_action_frames':int(np.any(np.abs(action[:,:12])>1e-8,axis=1).sum())}
        assert report['episodes'],'No episodes saved'
    return report


def applied_reset_poses(env, manifest=None, scenario_id=None):
    """Check all seven object reset poses and return measured values, not just cfg."""
    import torch
    expected = None
    if scenario_id:
        _,data=manifest_bytes(manifest)
        expected=next(s['poses'] for s in data['scenarios'] if s['id']==scenario_id)
    result={}
    for name in ('toaster','plate','bread_shelf',*(f'bread_{i}' for i in range(4))):
        if name=='bread_shelf': p,q=env.scene[name].get_world_poses()
        else:
            state=env.scene[name].data.root_state_w
            p,q=state[:,:3],state[:,3:7]
        p=p-env.scene.env_origins
        target=expected[name] if expected else dict(position_m=getattr(env.cfg.scene,name).init_state.pos,
                                                   quaternion_wxyz=getattr(env.cfg.scene,name).init_state.rot)
        torch.testing.assert_close(p,torch.tensor([target['position_m']],device=env.device),atol=5e-5,rtol=0)
        tq=torch.tensor([target['quaternion_wxyz']],device=env.device)
        torch.testing.assert_close((q*tq).sum(-1).abs(),torch.ones(env.num_envs,device=env.device),atol=5e-5,rtol=0)
        result[name]=dict(position_m=p[0].tolist(),quaternion_wxyz=q[0].tolist())
    print('RESET_POSES_OK '+json.dumps(result),flush=True)
    return result


def verify_initial_state(env, initial, env_id=0, include_cycle=True):
    """After reset_to, compare recorded robot/object state in environment coordinates."""
    import torch
    actual=env.scene.get_state(is_relative=True)
    if include_cycle and 'toast_cycle' in initial:
        actual['toast_cycle']=env.toast_cycle.state()
    def walk(saved,current,path):
        for key,value in saved.items():
            if key=='toast_cycle' and not include_cycle: continue
            if isinstance(value,dict): walk(value,current[key],path+'/'+key)
            else:
                target=value if value.ndim>1 else value.unsqueeze(0)
                got=current[key][env_id:env_id+1]
                torch.testing.assert_close(got,target.to(device=env.device),atol=5e-5,rtol=1e-5,msg=path+'/'+key)
    walk(initial,actual,'initial_state')
    print('REPLAY_INITIAL_STATE_OK',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Inspect an existing Quest diagnostic HDF5 without running simulation')
    parser.add_argument('dataset_file',type=Path)
    args=parser.parse_args()
    print(json.dumps(inspect_diagnostic(args.dataset_file),indent=2))
