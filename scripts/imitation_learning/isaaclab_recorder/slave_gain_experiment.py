"""Explicit experimental override; never used by default task/teleop."""
import copy,re,json
from pathlib import Path
import numpy as np
SLAVES=[f'gripper_{s}_joint{i}' for s in ('l','r') for i in (2,3,4)]
MASTERS=['gripper_l_joint1','gripper_r_joint1']
def override(cfg):
    if (cfg.sim.dt,cfg.decimation,cfg.sim.render_interval)!=(.01,4,4):raise ValueError('Expected original .01/4/4 timing')
    props=cfg.scene.robot.spawn.articulation_props
    if (props.solver_position_iteration_count,props.solver_velocity_iteration_count)!=(32,1):raise ValueError('Expected original 32/1 iterations')
    a=cfg.scene.robot.actuators['gripper_slave']
    if (a.stiffness,a.damping) not in ((100.,4.),(2.,.5)):raise ValueError('Expected slave100/4 or 2/0.5')
    if a.joint_names_expr!=['gripper_l_joint[2-4]','gripper_r_joint[2-4]']:raise ValueError('Unexpected slave mapping')
    before=copy.deepcopy(cfg.to_dict());a.stiffness=2.;a.damping=.5
    expected=copy.deepcopy(before);expected['scene']['robot']['actuators']['gripper_slave'].update(stiffness=2.,damping=.5)
    if cfg.to_dict()!=expected:raise ValueError('Unexpected configuration change')
    cfg._slave_gain_experiment=True

def readback(env,path,phase,reference=None):
    r=env.scene['robot'];v=r.root_physx_view;names=list(r.joint_names)
    def cpu(x):return x.detach().cpu().numpy()[0]
    k=cpu(v.get_dof_stiffnesses());d=cpu(v.get_dof_dampings())
    candidate=getattr(env.cfg,'_slave_gain_experiment',False)
    for n in SLAVES+MASTERS:
        i=names.index(n);expect=(2.,.5) if candidate and n in SLAVES else (100.,4.)
        if n in SLAVES and hasattr(env.cfg,'scene'):
            actuator=env.cfg.scene.robot.actuators['gripper_slave']
            expect=(actuator.stiffness,actuator.damping)
        if not np.allclose([k[i],d[i]],expect,rtol=0,atol=1e-6):raise ValueError('Runtime gain mismatch '+n)
    row=dict(phase=phase,source='PhysX get_dof_stiffnesses/get_dof_dampings',joint_names=names,stiffness=k.tolist(),damping=d.tolist(),limits=cpu(v.get_dof_limits()).tolist(),max_force=cpu(v.get_dof_max_forces()).tolist(),max_velocity=cpu(v.get_dof_max_velocities()).tolist())
    if reference is not None:
        for key in ('joint_names','stiffness','damping','limits','max_force','max_velocity'):
            if row[key]!=reference[key]:raise ValueError('Reset changed runtime '+key)
    with Path(path).open('a') as f:f.write(json.dumps(row)+'\n')
    return row


def canonical_repr(value):
    # Process-specific Python function addresses are not configuration values.
    return re.sub(r'(<function [^>]+) at 0x[0-9a-fA-F]+>', r'\1>', value) if isinstance(value,str) else value

def verify_baseline(cfg,path):
    import hashlib
    p=Path(path);b=json.loads(p.read_text())
    for key,current in [('physics_dt',cfg.sim.dt),('decimation',cfg.decimation),('render_interval',cfg.sim.render_interval),('robot_spawn_config',str(cfg.scene.robot.spawn)),('solver_config',str(cfg.sim.physx)),('task',cfg.env_name)]:
        if canonical_repr(b.get(key))!=canonical_repr(current):raise ValueError('Baseline config differs: '+key)
    summary=json.loads((p.parent/'physical_summary.json').read_text())
    if hashlib.sha256(Path(cfg.scene.robot.spawn.usd_path).read_bytes()).hexdigest()!=summary['usd_sha256']:raise ValueError('Baseline asset hash mismatch')
