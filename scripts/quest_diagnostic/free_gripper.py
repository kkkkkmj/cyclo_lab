"""Reset/open/close diagnostic reusing ContactProbe. GPU execution still required.

Default: no actuator/asset changes. Optional j3-only runtime velocity experiment.
A scripted trigger replaces Quest packets; the existing
right_gripper action still processes it. Does not claim official-task reproduction.
"""
import argparse
import json
from pathlib import Path


class VelocityCondition:
    """Read back all DOFs by name; the only optional write is right j3 max speed."""
    GETTERS = dict(velocity='get_dof_max_velocities', effort='get_dof_max_forces',
                   stiffness='get_dof_stiffnesses', damping='get_dof_dampings',
                   limits='get_dof_limits', armature='get_dof_armatures')
    JOINT = 'gripper_r_joint3'

    def __init__(self, robot, candidate=False):
        import numpy as np
        self.robot = robot
        self.names = list(robot.joint_names)
        if len(set(self.names)) != len(self.names): raise ValueError('Duplicate DOF names')
        self.index = self.names.index(self.JOINT)
        self.before = self.snapshot()
        self.expected = {k:v.copy() for k,v in self.before.items()}
        if candidate:
            if not np.allclose(self.before['velocity'][:,self.index], 6.5, atol=1e-6, rtol=0):
                raise ValueError('Expected original right j3 velocity limit 6.5 rad/s')
            # Public setter updates Isaac Lab cache and the actual PhysX max velocity.
            # No actuator group split, USD edit, or target/effort/gain setter.
            robot.write_joint_velocity_limit_to_sim(2.2, joint_ids=[self.index])
            self.expected['velocity'][:,self.index] = 2.2
        self.candidate = candidate

    def read(self, getter):
        import numpy as np
        x = getattr(self.robot.root_physx_view, getter)()
        if hasattr(x, 'detach'): x = x.detach().cpu().numpy()
        a = np.asarray(x, dtype=float).copy()
        if a.ndim < 2 or a.shape[1] != len(self.names) or not np.isfinite(a).all():
            raise ValueError('Invalid runtime readback '+getter)
        return a

    def snapshot(self):
        return {key:self.read(getter) for key,getter in self.GETTERS.items()}

    def check(self, snapshot):
        import numpy as np
        if list(self.robot.joint_names) != self.names: raise ValueError('DOF order changed')
        for key, actual in snapshot.items():
            if actual.shape != self.expected[key].shape or not np.allclose(actual,self.expected[key],atol=1e-6,rtol=0):
                raise ValueError('Unexpected runtime setting change: '+key)

    def named(self, snapshot):
        return {key:{n:values[:,i].tolist() for i,n in enumerate(self.names)}
                for key,values in snapshot.items()}


def command(t):
    """Two identical cycles, then caller resets and repeats. Simulation seconds."""
    t = t % 12.0
    if t < 1: return 'open_hold', 0.0
    if t < 3: return 'ramp_close', (t-1)/2
    if t < 4: return 'closed_hold', 1.0
    if t < 6: return 'ramp_open', 1-(t-4)/2
    if t < 7: return 'open_hold', 0.0
    if t < 9: return 'step_close', 1.0
    return 'step_open', 0.0


def metrics(row):
    """Name order is j1,j2,j3,j4, never PhysX traversal order."""
    import numpy as np
    q = np.asarray(row['direct_q']['value'], dtype=float)
    v = np.asarray(row['direct_velocity']['value'], dtype=float)
    target = np.asarray(row['target']['value'], dtype=float)
    if q.shape != (4,) or v.shape != (4,) or target.shape != (4,):
        raise ValueError('Missing four-joint measurements')
    return dict(target_spread_rad=float(np.ptp(target)),
                proximal_error_rad=float(q[0]-q[2]), distal_error_rad=float(q[1]-q[3]),
                proximal_velocity_error=float(v[0]-v[2]), distal_velocity_error=float(v[1]-v[3]),
                tracking_error_rad=(target-q).tolist())


def main():
    import sys, fcntl, hashlib, traceback
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
    from toast_recording_metadata import DEFAULT_MANIFEST
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--bridge-dir', type=Path, required=True)
    p.add_argument('--scenario_manifest', default=str(DEFAULT_MANIFEST))
    p.add_argument('--comparison-label', default='current_unmodified')
    p.add_argument('--j3-velocity-2p2', action='store_true',
                   help='Diagnostic only: right gripper_r_joint3 max velocity 6.5 -> 2.2 rad/s; all other settings unchanged.')
    p.add_argument('--observe-tip-contact', action='store_true',
                   help='Bounded 8s observation: permit only right r2/l2 contact, with force/separation/limit guards; requires j3 candidate.')
    p.add_argument('--close-angle', type=float, choices=(1.0, 1.1), default=1.0,
                   help='Command endpoint only; 1.0 avoids the near-touching 1.1 endpoint. No limit/gain change.')
    from isaaclab.app import AppLauncher
    AppLauncher.add_app_launcher_args(p)
    args = p.parse_args()
    if args.observe_tip_contact and not args.j3_velocity_2p2:
        p.error('Tip-contact observation requires the validated --j3-velocity-2p2 condition')
    if args.j3_velocity_2p2 and args.close_angle != 1.0 and not args.observe_tip_contact:
        p.error('The j3-only comparison requires the original 1.00 rad protocol')
    args.enable_cameras = True
    lock = (args.bridge_dir/'.simulation.lock').open('a')
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: p.error('Active simulator on bridge; no process stopped')
    args.output.mkdir(parents=True, exist_ok=False)
    app = env = probe = None
    code = 1
    state = dict(status='failed', reason='initialization_not_completed', gpu_validated=False)
    try:
        app = AppLauncher(args, fast_shutdown=False).app
        import gymnasium as gym, torch, numpy as np, cyclo_lab
        from pxr import Usd, UsdGeom, Gf
        from isaaclab_tasks.utils.parse_cfg import parse_env_cfg
        from contact_probe import ContactProbe, DiagnosticStop, rotation
        from contact_filter import exact_targets, validate_view, read_contact
        from tip_contact_observation import stop_reason as tip_stop_reason, DURATION_S
        task = 'Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2'
        cfg = parse_env_cfg(task, device=args.device, num_envs=1)
        cfg.scenario_id = 'toast_v20261108_041'
        cfg.scenario_manifest = args.scenario_manifest
        cfg.seed = 1
        env = gym.make(task, cfg=cfg).unwrapped
        robot = env.scene['robot']

        class FreeProbe(ContactProbe):
            def setup_free(self):
                stage = self.env.sim.stage
                # Exact collidable actors, including other fingers and robot links.
                targets = exact_targets(stage, '/World' if args.observe_tip_contact else '/World/envs/env_0')['targets']
                self.all_contacts = []
                self.vertices = {}
                self.wrist_reference = None
                self.allowed_tip_bodies = [self.frames[i]['bodies'][1] for i in (1,3)]
                cache = UsdGeom.XformCache()
                for f in self.frames:
                    body = f['bodies'][1]
                    filters = [x for x in targets if x != body]
                    view = robot._physics_sim_view.create_rigid_contact_view(
                        [body], filter_patterns=[filters], max_contact_data_count=4096)
                    validate_view(view, body, filters)
                    self.all_contacts.append((view, dict(body=body, filters=filters, reason=None)))
                    bp = stage.GetPrimAtPath(body)
                    points = []
                    for mesh in Usd.PrimRange(bp, Usd.TraverseInstanceProxies()):
                        if mesh.IsA(UsdGeom.Mesh) and '/collisions/' in str(mesh.GetPath()):
                            transform = cache.ComputeRelativeTransform(mesh, bp)[0]
                            points.extend([list(transform.Transform(Gf.Vec3d(*v)))
                                           for v in UsdGeom.Mesh(mesh).GetPointsAttr().Get()])
                    if not points: raise ValueError('Missing finger collision vertices '+body)
                    self.vertices[f['name']] = np.array(points)
                self.emit(dict(event='free_setup', filters=[s for _, s in self.all_contacts],
                    gap_definition='signed wrist-Y interval gap of distal collision mesh vertex projections; not cooked minimum surface distance',
                    contact_scope=('all enabled collidable owners under World, four right finger sensors'
                                   if args.observe_tip_contact else 'all enabled collidable owners under env_0; ground/outside env checked by net force only'),
                    permitted_contact_pair=self.allowed_tip_bodies if args.observe_tip_contact else None))
                if args.observe_tip_contact:
                    from pxr import UsdPhysics
                    colliders=[];filters=[]
                    for prim in Usd.PrimRange.Stage(stage,Usd.TraverseInstanceProxies()):
                        path=str(prim.GetPath())
                        if any(path.startswith(f['bodies'][1]+'/') for f in self.frames) and prim.HasAPI(UsdPhysics.CollisionAPI):
                            colliders.append(dict(path=path,schemas=str(prim.GetMetadata('apiSchemas')),
                                attributes={a.GetName():dict(value=str(a.Get()),authored=a.HasAuthoredValueOpinion(),
                                    sources=[str(s.layer.identifier) for s in a.GetPropertyStack()])
                                    for a in prim.GetAttributes() if a.GetName().startswith(('physics:','physx'))}))
                        for rel in prim.GetRelationships():
                            if 'filtered' in rel.GetName().lower():
                                filters.append(dict(path=path,name=rel.GetName(),targets=[str(t) for t in rel.GetTargets()]))
                    (args.output/'observation_geometry.json').write_text(json.dumps(dict(
                        colliders=colliders,filtered_pair_relationships=filters,frames=self.frames,
                        robot_spawn=str(cfg.scene.robot.spawn),solver=str(cfg.sim.physx),
                        body_local_collision_vertices={k:v.tolist() for k,v in self.vertices.items()},
                        semantics='Composed USD attributes and source vertices, not cooked PhysX shape readback'),indent=2))

            def emit(self, row):
                if row.get('event') == 'physics':
                    velocity = {'velocity':condition.read('get_dof_max_velocities')}
                    row['runtime_velocity_limit_by_name'] = condition.named(velocity)['velocity']
                    try: condition.check(velocity)
                    except ValueError as error:
                        row['runtime_settings_error'] = str(error)
                        super().emit(row)
                        raise DiagnosticStop(str(error))
                    row['symmetry'] = metrics(row)
                    contact = [read_contact(v, s, self.env.physics_dt, self.native,details=args.observe_tip_contact) for v, s in self.all_contacts]
                    row['all_pair_contacts'] = contact
                    points = []
                    wrist = row['links'][0]['parent']
                    if wrist is None: raise DiagnosticStop('missing_wrist_transform')
                    if args.observe_tip_contact:
                        row['wrist_drift_m'] = float(np.linalg.norm(np.asarray(wrist[:3])-self.wrist_reference))
                    wr = rotation([wrist[6], *wrist[3:6]])
                    for index in (1, 3):
                        pose = row['links'][index]['child']
                        if pose is None: raise DiagnosticStop('missing_finger_transform')
                        rot = rotation([pose[6], *pose[3:6]])
                        world = self.vertices[self.frames[index]['name']] @ rot.T + pose[:3]
                        points.append((world-np.asarray(wrist[:3])) @ wr)
                    # r2 lies at positive wrist Y in this USD at reset.
                    row['symmetry']['tip_projected_gap_m'] = float(points[0][:,1].min()-points[1][:,1].max())
                    row['symmetry']['tip_centers_wrist_m'] = [x.mean(0).tolist() for x in points]
                    invalid = any(c['validation'] is None for c in contact)
                    pairs = []
                    for c, (_, setup) in zip(contact, self.all_contacts):
                        if c['counts'] is not None:
                            pairs.extend([dict(body=setup['body'], other=other, points=int(count))
                                          for other, count in zip(setup['filters'], c['counts'][0]) if count > 0])
                    row['contact_pairs'] = pairs
                    if args.observe_tip_contact:
                        reason=tip_stop_reason(row,self.allowed_tip_bodies)
                        row['tip_observation_stop_reason']=reason
                        super().emit(row)
                        if reason:raise DiagnosticStop(reason)
                        return
                    super().emit(row)  # Preserve first contact/invalid sample before stopping.
                    if invalid: raise DiagnosticStop('all_pair_contact_measurement_invalid')
                    if pairs: raise DiagnosticStop('contact_detected_free_motion_segment_ended')
                    if any(np.linalg.norm(c['net']['value']) > 1e-4 for c in contact):
                        raise DiagnosticStop('unattributed_net_contact')
                    return
                super().emit(row)

        env.reset(seed=1)
        condition = VelocityCondition(robot, args.j3_velocity_2p2)
        def verify_settings(phase):
            actual = condition.snapshot()
            row = dict(event='runtime_settings', phase=phase, candidate=args.j3_velocity_2p2,
                       before=condition.named(condition.before), actual=condition.named(actual))
            try: condition.check(actual)
            except ValueError as error:
                row.update(verified=False, error=str(error))
                with (args.output/'runtime_settings.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
                raise
            row['verified'] = True
            with (args.output/'runtime_settings.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        verify_settings('after_optional_velocity_write')
        probe = FreeProbe(env, args.output/'contact.jsonl', args.comparison_label,
                          stop_on_excess=.01, require_contact=True)
        probe.setup_free()
        usd = Path(cfg.scene.robot.spawn.usd_path)
        root = Path(__file__).resolve().parents[2]
        files = [Path(__file__), root/'source/cyclo_lab/cyclo_lab/assets/robots/FFW_BG2.py']
        files += [Path(__file__).with_name(n) for n in ('contact_probe.py','contact_filter.py','tip_contact_observation.py')]
        files += list((root/'source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2').glob('*.py'))
        provenance = dict(task=task, scenario=cfg.scenario_id, seed=1, label=args.comparison_label,
            usd=str(usd), usd_sha256=hashlib.sha256(usd.read_bytes()).hexdigest(),
            code_sha256={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
            dt=env.step_dt, physics_dt=env.physics_dt, actuators=str(cfg.scene.robot.actuators),
            protocol='two resets; each 24s: 12s ramp+step sequence repeated twice without intervening reset',
            close_angle=args.close_angle,
            velocity_condition='right_j3_2p2' if args.j3_velocity_2p2 else 'original',
            modifications=('right gripper_r_joint3 runtime velocity limit only: 6.5 -> 2.2 rad/s'
                           if args.j3_velocity_2p2 else 'none to robot drives, assets, limits, collision, solver or task terminations'),
            command_source='scripted scalar trigger; current CoupledGripperPositionAction; CPU test covers practice teleop mapping')
        (args.output/'provenance.json').write_text(json.dumps(provenance, indent=2))
        if args.observe_tip_contact:
            from tip_contact_observation import MAX_FORCE_N, MAX_PENETRATION_M, MAX_LIMIT_EXCESS_RAD, MAX_WRIST_DRIFT_M, MAX_PAIR_ANGLE_ERROR_RAD
            provenance.update(protocol='two fresh resets; each 8s: open1s, ramp-close2s, hold1s, ramp-open2s, settle-open2s',
                observation_only_contact_allowance=True,allowed_tip_bodies=probe.allowed_tip_bodies,
                diagnostic_budgets=dict(max_pair_normal_force_n=MAX_FORCE_N,max_reported_penetration_m=MAX_PENETRATION_M,
                    max_limit_excess_rad=MAX_LIMIT_EXCESS_RAD,max_wrist_drift_m=MAX_WRIST_DRIFT_M,max_pair_angle_error_rad=MAX_PAIR_ANGLE_ERROR_RAD),
                distance_semantics='PhysX contact-point signed separation; not global minimum surface distance or independently calibrated penetration')
            (args.output/'provenance.json').write_text(json.dumps(provenance,indent=2))
        with torch.inference_mode():
            for episode in (1, 2):
                env.reset(seed=1)
                verify_settings(f'after_episode_reset_{episode}')
                q = robot.data.joint_pos[0, probe.ids].cpu().tolist()
                v = robot.data.joint_vel[0, probe.ids].cpu().tolist()
                probe.emit(dict(event='fresh_reset', episode=episode, q=q, velocity=v))
                if max(map(abs, q+v)) > 1e-5: raise DiagnosticStop('reset_not_zero')
                initial = {k:env.get_robot_eef_pose(k)[0].clone() for k in ('left','right','body')}
                if args.observe_tip_contact:
                    probe.wrist_reference=robot.root_physx_view.get_link_transforms()[0,probe.frames[0]['body_indices'][0],:3].detach().cpu().numpy().copy()
                for index in range(round((DURATION_S if args.observe_tip_contact else 24)/env.step_dt)):
                    phase, trigger = command(index*env.step_dt)
                    if args.observe_tip_contact and index*env.step_dt>=6:phase,trigger='settle_open',0.
                    trigger *= args.close_angle/1.1
                    action = env.target_eef_pose_to_action(initial, {'left':1., 'right':1-2*trigger}).unsqueeze(0)
                    probe.begin(dict(episode_number=episode, control_index=index, phase=phase,
                                     trigger=trigger, action=action[0].tolist(), recording=False))
                    try: result = env.step(action)
                    finally: probe.end()
                    if bool(result[2].any() or result[3].any()): raise DiagnosticStop('task_termination')
                verify_settings(f'after_episode_{episode}')
        state.update(status='completed', reason=('bounded_tip_observation_completed' if args.observe_tip_contact else 'protocol_completed_no_reported_contacts'), gpu_validated=True)
        code = 0
    except BaseException as error:
        state['reason'] = f'{type(error).__name__}: {error}'
        if type(error).__name__=='DiagnosticStop':
            state.update(status='diagnostic_stop',reason=str(error));code=2
            print('DIAGNOSTIC_STOP '+str(error),flush=True)
        else:traceback.print_exc()
    finally:
        from auto_contact_shutdown import finish
        code = finish(app, env, probe, args.output/'outcome.json', state, code)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
