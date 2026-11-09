"""Fail-closed checks for a geometry-derived trial; no joint/physics setters."""
import hashlib,json
from pathlib import Path
import numpy as np

def validate_geometry(plan,geometry,scenario,seed):
    if plan['schema_version']!=1 or plan['scenario']!=scenario or plan['seed']!=seed:raise ValueError('plan scenario/seed mismatch')
    if geometry['errors'] or geometry['meters_per_unit']!=1 or geometry['up_axis']!='Z':raise ValueError('invalid geometry units/errors')
    if len(geometry['table'])!=1 or len(geometry['fingers'])!=4:raise ValueError('geometry counts mismatch')
    def same(a,b,tol=1e-5):
        a=np.asarray(a,float);b=np.asarray(b,float)
        if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all() or np.max(np.abs(a-b))>tol:raise ValueError('initial geometry/reset pose differs from plan')
    same(geometry['table'][0]['world_vertex_bounds'],plan['table_bounds'])
    same([f['world_vertex_bounds'] for f in geometry['fingers']],plan['finger_bounds'])
    for k in ('left','right','body'):same(geometry['initial_eef_poses'][k],plan['initial_eef_poses'][k])
    top=geometry['table'][0]['world_vertex_bounds'][1][2]
    low=min(f['world_vertex_bounds'][0][2] for f in geometry['fingers'])
    if abs(plan['contact_depth_m']-(low-top))>1e-5:raise ValueError('contact depth inconsistent with source bounds')
    extra=plan['max_down_m']-plan['contact_depth_m']
    if not 0<=extra<=.003000001:raise ValueError('plan overtravel exceeds 3mm')
    if not np.isfinite(plan['horizontal_offset_m']).all():raise ValueError('nonfinite offset')

def validate_runtime(plan,geometry,env,repo,scenario,seed):
    validate_geometry(plan,geometry,scenario,seed)
    digest=hashlib.sha256(json.dumps(geometry['table'][0]['meshes'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if digest!=plan['table_mesh_sha256']:raise ValueError('composed table source geometry changed')
    repo=Path(repo).resolve()
    for name,expected in plan['asset_hashes'].items():
        path=(repo/name).resolve()
        if not path.is_relative_to(repo) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('asset/manifest changed: '+name)
    for name,pose in plan['obstacle_reset_poses'].items():
        cfg=getattr(env.cfg.scene,name)
        for a,b in [(cfg.init_state.pos,pose['position_m']),(cfg.init_state.rot,pose['quaternion_wxyz']),(cfg.spawn.scale or (1,1,1),pose['scale'])]:
            if not np.allclose(a,b,rtol=0,atol=1e-6):raise ValueError('obstacle config mismatch: '+name)
        asset=env.scene[name]
        if hasattr(asset,'data') and hasattr(asset.data,'root_pos_w'):
            pos=(asset.data.root_pos_w[0]-env.scene.env_origins[0]).detach().cpu().numpy()
            quat=asset.data.root_quat_w[0].detach().cpu().numpy()
            if np.max(np.abs(pos-np.array(pose['position_m'])))>1e-4 or min(np.linalg.norm(quat-np.array(pose['quaternion_wxyz'])),np.linalg.norm(quat+np.array(pose['quaternion_wxyz'])))>1e-4:
                raise ValueError('actual obstacle reset pose mismatch: '+name)
    return dict(valid=True,checks='source geometry, initial wrist poses, asset+manifest hashes, obstacle config/root poses',limitation='not cooked shape or full-arm collision/IK proof')
