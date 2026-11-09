"""PREPARED, GPU UNVALIDATED. Same task physics; scripted slow world-Z approach, not a VR replay."""
import argparse,json,sys,time,hashlib,traceback,fcntl,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from view_make_toast_scenario import resolve_selection
from toast_recording_metadata import DEFAULT_MANIFEST
from toast_overview import overview_cfg,position_overview
from auto_contact_protocol import Protocol
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--bridge-dir',type=Path,required=True,help='Existing simulation lock only; no input read/write')
p.add_argument('--operator',default='operator_B',choices=['operator_B'])
p.add_argument('--scenario_index',type=int,default=1)
p.add_argument('--scenario_id',default=None)
p.add_argument('--scenario_manifest',default=str(DEFAULT_MANIFEST))
p.add_argument('--seed',type=int,default=1)
p.add_argument('--readback-only',action='store_true',help='No commanded env.step; only initialization/reset and settings lookup')
p.add_argument('--geometry-plan-only',action='store_true',help='Export missing collider geometry after reset, then close; no commanded env.step or automatic contact')
p.add_argument('--approach-plan',type=Path,help='Validated geometry-derived horizontal/vertical route JSON; default diagnostic path unchanged')
p.add_argument('--speed',type=float,default=.01)
p.add_argument('--max-down',type=float,default=.25)
p.add_argument('--stop-excess-rad',type=float,default=.05)
from isaaclab.app import AppLauncher
AppLauncher.add_app_launcher_args(p);args=p.parse_args();args.enable_cameras=True
if not .005<=args.stop_excess_rad<=.10:p.error('stop-excess-rad must be .005.. .10; detection threshold only')
protocol=Protocol(args.speed,args.max_down)
plan=None
if args.approach_plan:
    if args.readback_only or args.geometry_plan_only or args.max_down!=.25:p.error('approach-plan cannot combine with readback/geometry-only or a max-down override')
    from auto_contact_protocol import PlannedProtocol
    plan=json.loads(args.approach_plan.read_text());protocol=PlannedProtocol(plan,args.speed)
    if 1+2*(protocol.length+protocol.max_down)/args.speed+.4>150:p.error('planned duration exceeds 150 simulation seconds; choose supported speed .01 or .02')
sid=resolve_selection(args)
if sid!='toast_v20261108_041':p.error('Expected B first scenario toast_v20261108_041')
# Refuse to run alongside existing teleop on the same bridge. Never acquire/modify input packets.
lock=(args.bridge_dir/'.simulation.lock').open('a')
try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:p.error('Bridge has an active simulator; no process was stopped')
args.output.mkdir(parents=True,exist_ok=False)
app=None;env=None;probe=None;status='failed';reason='initialization_not_completed';code=1
out=args.output
commands=(out/'commands.jsonl').open('x',buffering=1)
try:
    app=AppLauncher(args,fast_shutdown=False).app
    import inspect
    app_source=inspect.getsourcefile(type(app))
    app_info=dict(class_name=str(type(app)),source_file=app_source,config_fast_shutdown=getattr(app,'config',{}).get('fast_shutdown'))
    try:
        source_text=inspect.getsource(type(app).close)
        (out/'installed_simulation_app_close.py.txt').write_text(source_text)
        app_info['close_source_sha256']=hashlib.sha256(source_text.encode()).hexdigest()
    except Exception as e:app_info['source_error']=repr(e)
    (out/'application_implementation.json').write_text(json.dumps(app_info,indent=2))
    if app_info['config_fast_shutdown'] is not False:raise RuntimeError('fast_shutdown=False was not applied; refusing automatic approach')
    import gymnasium as gym,torch,cyclo_lab
    from isaaclab_tasks.utils.parse_cfg import parse_env_cfg
    from pxr import UsdPhysics
    from contact_probe import ContactProbe,DiagnosticStop
    task='Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2'
    cfg=parse_env_cfg(task,device=args.device,num_envs=1)
    cfg.scenario_id=sid;cfg.scenario_manifest=args.scenario_manifest;cfg.seed=args.seed
    cfg.scene.replay_overview=overview_cfg()
    env=gym.make(task,cfg=cfg).unwrapped
    from contact_probe import value
    def runtime_settings(phase):
        r=env.scene['robot'];v=r.root_physx_view;names=list(r.joint_names);ids=[names.index(f'gripper_r_joint{i}') for i in range(1,5)]
        item=dict(phase=phase,joint_names=names,right_indices=ids,
                  positions=value(lambda:v.get_dof_positions()[0,ids]),velocities=value(lambda:v.get_dof_velocities()[0,ids]),limits=value(lambda:v.get_dof_limits()[0,ids]),motions=value(lambda:v.get_dof_motions()[0,ids]),
                  stiffness=value(lambda:v.get_dof_stiffnesses()[0,ids]),damping=value(lambda:v.get_dof_dampings()[0,ids]),
                  masses=value(lambda:v.get_masses()[0]),inertias=value(lambda:v.get_inertias()[0]),max_force=value(lambda:v.get_dof_max_forces()[0,ids]),soft_limits=value(lambda:r.data.soft_joint_pos_limits[0,ids]))
        try:
            m=v.get_metatype(0)
            item['metatype']={k:getattr(m,k) for k in ('link_names','link_parents','joint_names','dof_names','joint_types','joint_dof_offsets','joint_dof_counts','dof_types','fixed_base')}
            item['dof_paths']=v.dof_paths;item['link_paths']=v.link_paths
        except Exception as e:item['metatype_error']=repr(e)
        (out/(phase+'.json')).write_text(json.dumps(item,indent=2,default=str));return item
    before=runtime_settings('before_startup_reset')
    env.reset(seed=args.seed);position_overview(env)
    startup=runtime_settings('after_startup_reset')
    env.reset(seed=args.seed);position_overview(env)
    after=runtime_settings('after_episode_reset')
    robot=env.scene['robot'];stage=env.sim.stage
    initial={k:env.get_robot_eef_pose(k)[0].clone() for k in ('left','right','body')}
    probe=ContactProbe(env,out/'contact.jsonl','automatic-baseline',stop_on_excess=args.stop_excess_rad,require_contact=True)
    from contact_geometry_snapshot import snapshot
    geometry=snapshot(env,probe,initial)
    (out/'collision_geometry.json').write_text(json.dumps(geometry,indent=2))
    if plan:
        from auto_contact_plan import validate_runtime
        check=validate_runtime(plan,geometry,env,Path(__file__).resolve().parents[2],sid,args.seed)
        (out/'approach_plan.json').write_text(json.dumps(plan,indent=2))
        (out/'plan_validation.json').write_text(json.dumps(check,indent=2))
    # Source of runtime evidence: composed scene USD opinions, and explicitly named PhysX getters.
    def dump_attrs(prim):return {a.GetName():dict(value=str(a.Get()),authored=a.HasAuthoredValueOpinion(),stack=[str(s.layer.identifier)+':'+str(s.path) for s in a.GetPropertyStack()]) for a in prim.GetAttributes() if a.GetName().startswith(('physics:','physx','drive:','state:'))}
    robot_prims={str(x.GetPath()):dict(type=x.GetTypeName(),schemas=str(x.GetMetadata('apiSchemas')),attrs=dump_attrs(x),relationships={r.GetName():[str(t) for t in r.GetTargets()] for r in x.GetRelationships()}) for x in stage.Traverse() if '/env_0/Robot' in str(x.GetPath()) and (x.IsA(UsdPhysics.Joint) or x.HasAPI(UsdPhysics.ArticulationRootAPI) or x.HasAPI(UsdPhysics.RigidBodyAPI))}
    import omni.kit.app
    extensions=omni.kit.app.get_app().get_extension_manager().get_extensions()
    provenance=dict(isaac_sim_version_file=Path('/isaac-sim/VERSION').read_text() if Path('/isaac-sim/VERSION').exists() else None,task=task,scenario=sid,seed=args.seed,physics_dt=env.physics_dt,decimation=cfg.decimation,
        solver_config=str(cfg.sim.physx),robot_spawn_config=str(cfg.scene.robot.spawn),actuators_config=str(cfg.scene.robot.actuators),
        actual_imports={n:getattr(m,'__file__',None) for n,m in list(sys.modules.items()) if n=='cyclo_lab' or n.startswith('cyclo_lab.manager_based.manipulation.make_toast') or n.startswith('omni.physics.tensors')},
        physics_extensions=[e for e in extensions if any(w in str(e.get('id','')) for w in ('physx','physics.tensors','isaacsim.simulation_app'))],
        stage_layers=[x.identifier for x in stage.GetLayerStack()],robot_stage=robot_prims,
        physics_scene={str(x.GetPath()):dump_attrs(x) for x in stage.Traverse() if x.IsA(UsdPhysics.Scene)},
        motion_mode=after['motions'],motion_enum=dict(Free=0,Limited=1,Locked=2,Invalid=255),
        protocol=dict(axis='world -Z',orientation='initial wrist orientation held',speed=args.speed,max_down=args.max_down,baseline_s=1,contact_hold_s=.2,stop_excess_rad=args.stop_excess_rad,
        note='Fresh reset, scripted command. Not claimed equivalent to prior VR collision/manifold. Original action/IK; no robot gain/limit/solver/asset changes.'))
    (out/'provenance.json').write_text(json.dumps(provenance,indent=2,default=str))
    if plan:
        provenance['protocol'].update(axis='world XY translate then -Z then retract and return XY',max_down=protocol.max_down,horizontal_offset_m=protocol.xy,plan_sha256=hashlib.sha256(args.approach_plan.read_bytes()).hexdigest())
        (out/'provenance.json').write_text(json.dumps(provenance,indent=2,default=str))
    # Verify API/path/native-error status before making any approach command.
    from contact_filter import read_contact
    checks=[read_contact(v,s,env.physics_dt,probe.native) for v,s in zip(probe.contacts,probe.contact_setup)]
    (out/'contact_setup_validation.json').write_text(json.dumps(checks,indent=2))
    no_commands=args.readback_only or args.geometry_plan_only
    if not no_commands and any(x['validation'] is None for x in checks):raise DiagnosticStop('contact_setup_unverified')
    if after['motions']['value']!=[1,1,1,1]:raise DiagnosticStop('dof_motion_not_confirmed_limited')
    dt=env.step_dt;index=0;contact=False;phase_start='baseline'
    while not no_commands and protocol.phase!='done':
        phase=protocol.phase;down=protocol.down
        offset=protocol.offset() if plan else [0.,0.,-down]
        target={k:v.clone() for k,v in initial.items()}
        target['right'][:3,3]+=torch.tensor(offset,device=target['right'].device)
        current=env.get_robot_eef_pose('right')[0]
        if float(torch.linalg.vector_norm(target['right'][:3,3]-current[:3,3]))>.04:raise DiagnosticStop('wrist_tracking_error')
        action=env.target_eef_pose_to_action(target,{'left':1.,'right':1.}).unsqueeze(0)
        row=dict(episode_number=1,control_index=index,phase=phase,recording=False,expected_demo=None,action=action[0].tolist(),
                 down_m=down,offset_m=offset,target_wrist=target['right'].tolist(),measured_wrist_pre_step=current.tolist(),input_snapshot=None,control_states={'right':{'reason':'scripted_'+phase}},monotonic=time.monotonic())
        commands.write(json.dumps(row)+'\n');probe.begin(row)
        try:result=env.step(action)
        finally:probe.end()
        if bool(result[2].any() or result[3].any()):raise DiagnosticStop('original_task_termination')
        contact=probe.control_contact
        if plan and not contact and any(c['net']['value'] is not None and any(abs(v)>1e-4 for v in c['net']['value'][0]) for c in probe.latest['contacts']):raise DiagnosticStop('non_table_or_unattributed_finger_contact')
        if phase=='baseline' and any(c['net']['value'] is not None and any(abs(v)>1e-4 for v in c['net']['value'][0]) for c in probe.latest['contacts']):raise DiagnosticStop('unexpected_baseline_net_contact')
        protocol.advance(dt,contact);index+=1
        if index>(4000 if plan else 2000):raise DiagnosticStop('protocol_budget_exceeded')
    status='completed';reason='contact_and_release_observed' if protocol.contact_observed and not contact else 'contact_or_release_not_confirmed';code=0 if reason=='contact_and_release_observed' else 3
    if args.readback_only:reason='readback_only_limited_confirmed';code=0
    if args.geometry_plan_only:reason='geometry_snapshot_only_no_contact_attempt';code=0
except BaseException as error:
    reason=f'{type(error).__name__}: {error}';traceback.print_exc()
    if type(error).__name__=='DiagnosticStop' and str(error)=='joint_limit_excess':status='limit_excess_captured';code=2
finally:
    commands.close()
    # No success flag is written before the actual close returns.
    from auto_contact_shutdown import finish
    state=dict(status=status,reason=reason,contact_observed=protocol.contact_observed,phase=protocol.phase)
    code=finish(app,env,probe,out/'outcome.json',state,code)
sys.exit(code)
