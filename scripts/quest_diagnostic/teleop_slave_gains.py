"""Validate current toast VR gains; no state writes or physics stepping."""
import math
NAMES=[f'gripper_{side}_joint{i}' for side in ('l','r') for i in range(1,5)]

def validate_options(slave=False,j1=False,j3=False):
    if slave:
        raise ValueError('--gripper-slave-gains-official is retired: v2 requires slave 100/4; remove this option')

def configure(cfg,enabled=False):
    validate_options(enabled)
    a=cfg.scene.robot.actuators['gripper_slave']
    if a.joint_names_expr!=['gripper_l_joint[2-4]','gripper_r_joint[2-4]'] or (a.stiffness,a.damping)!=(100.,4.):
        raise ValueError('Expected v2 toast six-slave mapping with stiffness=100 and damping=4')

def readback(robot,phase,enabled=False,j1=False,j3=False,reference=None,slave_gains=None):
    """Actual PhysX API readback once per reset; rad/s and simulator force units."""
    validate_options(enabled,j1,j3)
    if slave_gains is not None and tuple(slave_gains)!=(100.,4.):
        raise RuntimeError('Configured slave gains differ from required 100/4')
    ids=[robot.joint_names.index(n) for n in NAMES];v=robot.root_physx_view
    row=dict(event='gripper_runtime',phase=phase,source='PhysX tensor API',joint_names=NAMES)
    for key,method in [('stiffness','get_dof_stiffnesses'),('damping','get_dof_dampings'),('effort_limit','get_dof_max_forces'),('velocity_limit_rad_s','get_dof_max_velocities')]:
        row[key]=getattr(v,method)()[0,ids].detach().cpu().tolist()
    for index,name in enumerate(NAMES):
        master=name.endswith('joint1')
        expected=[100.,4.,30. if master else 20.,6.5]
        if j3 and name=='gripper_r_joint3':expected[3]=2.2
        for key,want in zip(('stiffness','damping','effort_limit','velocity_limit_rad_s'),expected):
            if not math.isclose(row[key][index],want,rel_tol=0,abs_tol=1e-5):raise RuntimeError(f'{phase}: unexpected {name} {key}: {row[key][index]} != {want}')
    if reference:
        for key in ('joint_names','stiffness','damping','effort_limit','velocity_limit_rad_s'):
            if row[key]!=reference[key]:raise RuntimeError('Reset changed gripper '+key)
    return row
