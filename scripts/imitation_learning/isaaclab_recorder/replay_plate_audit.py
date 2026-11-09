"""Read-only plate checkpoints; no extra step, force, or state write."""
import json
from replay_scene_audit import emit, runtime_properties


def plate_checkpoint(env, stage, reference=None, raw_only=False):
    plate=env.scene['plate']
    raw=plate.root_physx_view.get_velocities()[0].detach().cpu()
    report=dict(stage=stage,physics_dt=env.physics_dt,decimation=env.cfg.decimation,
                velocity_order=['vx','vy','vz','wx','wy','wz'],units=['m/s']*3+['rad/s']*3,
                physx_com_velocity_world=raw.tolist())
    if not raw_only:
        cached=plate.data.root_vel_w[0].detach().cpu()
        pose=plate.data.root_state_w[0,:7].detach().clone()
        pose[:3]-=env.scene.env_origins[0]
        report.update(cached_com_velocity_world=cached.tolist(),pose=pose.cpu().tolist(),
                      cached_vs_physx_max_abs=float((cached-raw).abs().max()))
        if reference is not None:
            target=reference['rigid_object']['plate']
            wanted=target['root_velocity']
            if wanted.ndim!=2 or wanted.shape!=(1,6):raise ValueError(f'Plate reference velocity shape {wanted.shape}')
            wanted=wanted[0].detach().cpu()
            report.update(recorded_velocity=wanted.tolist(),
                          velocity_abs_error=(cached-wanted).abs().tolist(),
                          physx_vs_recorded_abs_error=(raw-wanted).abs().tolist())
        if 'plate_contact' in env.scene.sensors:
            report['contact_net_force_world_N']=env.scene['plate_contact'].data.net_forces_w[0].detach().cpu().tolist()
            report['contact_note']='sensor sample only; reset may retain stale force; not solver/contact-cache state'
    else:
        # scene.update() has not yet run inside env.step; avoid comparing stale caches.
        report['reference_note']='no recorded substep-1 state; compare only control-step end to HDF5 states[0]'
    emit(env,'plate_checkpoint',report)
    print('PLATE_CHECKPOINT '+json.dumps(report),flush=True)


def step_with_first_physics_checkpoint(env, actions):
    original=env.sim.step;count=0
    def observed_step(*args,**kwargs):
        nonlocal count
        result=original(*args,**kwargs);count+=1
        if count==1:plate_checkpoint(env,'after_first_physics_step',raw_only=True)
        return result
    env.sim.step=observed_step
    try:return env.step(actions)
    finally:env.sim.step=original


def plate_configuration(env, recorded_timing):
    runtime_properties(env)
    cfg=env.cfg.scene.plate
    print('PLATE_CONFIGURATION '+json.dumps(dict(
        recorded_timing=recorded_timing,current_timing=dict(dt=env.physics_dt,decimation=env.cfg.decimation,render_interval=env.cfg.sim.render_interval),
        rigid=cfg.spawn.rigid_props.to_dict(),collision=cfg.spawn.collision_props.to_dict(),mass=cfg.spawn.mass_props.to_dict(),
        sim=env.cfg.sim.to_dict(),
        note='CONFIG INTENT ONLY: null means unspecified, not actual PhysX zero/default. See RUNTIME_PHYSICS for separate USD and queried values.'),default=str),flush=True)
