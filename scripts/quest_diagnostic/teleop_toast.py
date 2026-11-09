"""Explicit bounded Quest episodes on fixed toast layouts; standard diagnostic recorder."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import queue
import secrets
import sys
import threading
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from view_make_toast_scenario import resolve_selection, add_group_arguments
from toast_recording_metadata import (DEFAULT_MANIFEST,create_diagnostic,finalize_diagnostic,
    validate_recording_args,applied_reset_poses,manifest_bytes)
from toast_overview import overview_cfg,position_overview
from bridge import read_input
from preview import publish_preview,stop_preview
from preview_encoding import encode_native_preview
from control import BoundedTeleop,norm,sub,qrotate,qinv
from episode_control import EpisodeLifecycle,ButtonEdges,can_start
from display_status import display_status,start_blockers
from diagnostic_recorder import DiagnosticRecorder
from practice_options import add_arguments,options,configure
from teleop_gripper_options import configure_right_j3_speed,configure_right_j1_speed
from teleop_slave_gains import configure as configure_slave_gains, readback as gripper_readback, validate_options as validate_gripper_options
from performance_probe import PerformanceProbe
from tracking_monitor import TrackingMonitor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'imitation_learning/isaaclab_recorder'))
from replay_scene_audit import TimelineProbe
from replay_plate_audit import plate_checkpoint,plate_configuration,step_with_first_physics_checkpoint

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bridge-dir',required=True,type=Path)
parser.add_argument('--duration',type=float,default=90)
parser.add_argument('--keep-open',action='store_true',help='Ignore wall duration; wait between episodes until Ctrl+C/q')
parser.add_argument('--preview-only',action='store_true')
parser.add_argument('--enable-grippers',action='store_true')
gripper_speed_options=parser.add_mutually_exclusive_group()
gripper_speed_options.add_argument('--right-gripper-j3-speed-2p2',action='store_true',
                    help='VR comparison B: only right gripper joint3 simulation speed limit becomes 2.2 rad/s; default is unchanged')
gripper_speed_options.add_argument('--right-gripper-j1-speed-6p5',action='store_true',
                    help='Legacy comparison C: keeps right master at 6.5 rad/s; v2 now defaults both masters to 6.5')
parser.add_argument('--gripper-trigger-official-binary',action='store_true',help='VR input only: trigger <0.5 opens to 0rad, otherwise closes to 1rad through existing toast action')
parser.add_argument('--gripper-slave-gains-official',action='store_true',help='Retired soft-gain option: rejected; current v2 slave gains are fixed at 100/4')
parser.add_argument('--operator',choices=('operator_A','operator_B'))
parser.add_argument('--scenario_index',type=int)
parser.add_argument('--scenario_id')
parser.add_argument('--scenario_manifest',default=str(DEFAULT_MANIFEST))
add_group_arguments(parser)
parser.add_argument('--seed',type=int,default=1)
parser.add_argument('--contact-diagnostic',type=Path,help='Opt-in per-physics-step gripper audit JSONL; new file only')
parser.add_argument('--diagnostic-log',type=Path,help='New JSONL trace of decision inputs/states; not demonstration data')
parser.add_argument('--record-dir',type=Path,help='New test-only output directory; never overwrite')
parser.add_argument('--record-seconds',type=float,default=8,help='Auto-save each short test after this many wall seconds')
add_arguments(parser)
known,_=parser.parse_known_args()
try:
    validate_gripper_options(known.gripper_slave_gains_official,known.right_gripper_j1_speed_6p5,known.right_gripper_j3_speed_2p2)
    if known.gripper_trigger_official_binary and (not known.enable_grippers or known.gripper_slave_gains_official or known.right_gripper_j1_speed_6p5 or known.right_gripper_j3_speed_2p2):
        raise ValueError('Binary trigger comparison requires --enable-grippers and baseline gains/speeds')
    selected_id=resolve_selection(known)
    validate_recording_args(known)
    control_settings=options(known)
    if (Path(known.scenario_manifest).resolve()==DEFAULT_MANIFEST.resolve()
            and known.operator=='operator_B' and known.scenario_index==1 and selected_id!='batch02_toast_001'):
        raise ValueError('Operator B first assignment differs from batch02_toast_001')
except (ValueError,KeyError,OSError) as error:parser.error(str(error))
if not (known.bridge_dir/'input.json').exists():parser.error('Start the input server with this --bridge-dir first')
lock=(known.bridge_dir/'.simulation.lock').open('a')
try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:parser.error('A test already owns this bridge; it was not stopped')
from isaaclab.app import AppLauncher
AppLauncher.add_app_launcher_args(parser)
args=parser.parse_args()
# Fresh argparse namespace: also resolve group into parent operator/index for recording.
selected_id=resolve_selection(args)
if args.duration<=0:parser.error('--duration must be positive (or use --keep-open)')
record_dir=metadata=None
if args.record_dir:
    record_dir,metadata=create_diagnostic(args.record_dir,args.scenario_manifest,args.operator,
                                         selected_id,args.scenario_index,seed=args.seed)
    args.scenario_manifest=str(record_dir/'manifest.json')
raw,_=manifest_bytes(args.scenario_manifest)
manifest_hash=hashlib.sha256(raw).hexdigest()
print(f'SCENARIO_SELECTED operator={args.operator} index={args.scenario_index} id={selected_id or "original"} seed={args.seed} manifest={args.scenario_manifest} manifest_sha256={manifest_hash}',flush=True)
args.enable_cameras=True
app=AppLauncher(args).app
import gymnasium as gym
import torch
from PIL import Image
import cyclo_lab  # noqa: F401
from isaaclab_tasks.utils.parse_cfg import parse_env_cfg

TASK='Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2'
env=recorder=timeline=diagnostic_log=perf=contact_probe=None
episode_steps=0
run_id=secrets.token_hex(12);frame_id=0;last_capture=None;exit_reason='normal_exit'
lifecycle=EpisodeLifecycle();edges=ButtonEdges();commands=queue.Queue()

def console():
    for line in sys.stdin:
        if line.strip().lower() in ('n','s','q'):commands.put(line.strip().lower())

try:
    if args.diagnostic_log:
        args.diagnostic_log.parent.mkdir(parents=True,exist_ok=True)
        diagnostic_log=args.diagnostic_log.open('x',buffering=1)
        diagnostic_log.write(json.dumps(dict(event='begin',run_id=run_id,scenario_id=selected_id,seed=args.seed))+ '\n')
    cfg=parse_env_cfg(TASK,device=args.device,num_envs=1)
    cfg.scenario_id=selected_id;cfg.scenario_manifest=args.scenario_manifest;cfg.seed=args.seed
    # Observation-only extra camera; original cameras and policy observations untouched.
    cfg.scene.replay_overview=overview_cfg()
    configure_slave_gains(cfg,args.gripper_slave_gains_official)
    configure_right_j3_speed(cfg,args.right_gripper_j3_speed_2p2)
    configure_right_j1_speed(cfg,args.right_gripper_j1_speed_6p5)
    if record_dir:
        from isaaclab.envs.mdp.recorders.recorders_cfg import ActionStateRecorderManagerCfg
        from isaaclab.managers import DatasetExportMode
        cfg.env_name=TASK;cfg.recorders=ActionStateRecorderManagerCfg()
        cfg.recorders.dataset_export_dir_path=str(record_dir);cfg.recorders.dataset_filename='dataset'
        cfg.recorders.dataset_export_mode=DatasetExportMode.EXPORT_ALL
        cfg.recorders.export_in_record_pre_reset=False
        metadata['timing']=dict(physics_dt=cfg.sim.dt,decimation=cfg.decimation,
            render_interval=cfg.sim.render_interval,control_dt=cfg.sim.dt*cfg.decimation)
    # Original physics, rewards, 240-second timeout and success/failure predicates remain.
    env=gym.make(TASK,cfg=cfg).unwrapped
    if record_dir:
        audit_dir=record_dir/'record_audit';audit_dir.mkdir()
        env._replay_audit_dir=str(audit_dir)
        timeline=TimelineProbe(env);timeline.mark('before_startup_reset')
    env.reset(seed=args.seed)
    gripper_reference=None
    def report_gripper_runtime(phase):
        global gripper_reference
        row=gripper_readback(env.scene['robot'],phase,args.gripper_slave_gains_official,
            args.right_gripper_j1_speed_6p5,args.right_gripper_j3_speed_2p2,gripper_reference,
            slave_gains=(cfg.scene.robot.actuators['gripper_slave'].stiffness,
                         cfg.scene.robot.actuators['gripper_slave'].damping))
        if gripper_reference is None:gripper_reference=row
        print('GRIPPER_RUNTIME_OK '+json.dumps(row),flush=True)
        if diagnostic_log:diagnostic_log.write(json.dumps(row)+'\n')
    report_gripper_runtime('after_startup_reset')
    if timeline:timeline.mark('after_startup_reset')
    reset_poses=applied_reset_poses(env,args.scenario_manifest,selected_id)
    position_overview(env)
    assert env.action_manager.active_terms==['left_arm','right_arm','left_gripper','right_gripper','lift']
    assert env.action_manager.total_action_dim==15
    for side in ('left','right'):
        term=env.action_manager.get_term(side+'_arm')
        assert term.cfg.controller.use_relative_mode and term.cfg.controller.command_type=='pose'
        assert term.cfg.controller.ik_method=='dls' and term.cfg.scale==.3
    dt=env.step_dt;robot=env.scene['robot']
    assert env.action_manager.get_term('lift').cfg.scale==.25 and env.action_manager.get_term('lift').cfg.offset==-.25
    def poses():
        result={}
        for side in ('left','right'):
            p,q=env.action_manager.get_term(side+'_arm')._compute_frame_pose()
            q=q[0].tolist();result[side]=(p[0].tolist(),q[1:]+q[:1])
        return result
    def new_controller():
        lift=float(robot.data.joint_pos[0,robot.joint_names.index('lift_joint')])
        result=configure(BoundedTeleop(poses(),max(-1.,min(1.,(lift+.25)/.25)),args.enable_grippers),control_settings)
        result.gripper_trigger_official_binary=args.gripper_trigger_official_binary
        root_pos=(robot.data.root_pos_w[0]-env.scene.env_origins[0]).tolist()
        root_q=robot.data.root_quat_w[0].tolist();root_q=root_q[1:]+root_q[:1]
        bread={n:qrotate(qinv(root_q),sub(v['position_m'],root_pos)) for n,v in reset_poses.items() if n.startswith('bread_') and n!='bread_shelf'}
        print('WORKSPACE_RESET '+json.dumps(dict(frame='robot root',wrists=result.home,bread_centers=bread,
            center_distances={s:{n:norm(sub(p,result.home[s][0])) for n,p in bread.items()} for s in result.home})),flush=True)
        return result
    gripper_ids=[robot.joint_names.index(f'gripper_{s}_joint{i}') for s in ('l','r') for i in range(1,5)]
    right_names=[f'gripper_r_joint{i}' for i in range(1,5)]
    right_ids=[robot.joint_names.index(name) for name in right_names]
    right_limits=robot.root_physx_view.get_dof_max_velocities()[0,right_ids].detach().cpu().tolist()
    print('RIGHT_GRIPPER_VELOCITY_LIMIT_RAD_S '+json.dumps(dict(zip(right_names,right_limits))),flush=True)
    if diagnostic_log:
        diagnostic_log.write(json.dumps(dict(event='joint_configuration',joint_names=list(robot.joint_names),
            soft_position_limits=robot.data.soft_joint_pos_limits[0].detach().cpu().tolist(),
            velocity_limits=robot.data.joint_vel_limits[0].detach().cpu().tolist()))+'\n')
    gripper_audit_time=0.
    controller=new_controller()
    tracking=TrackingMonitor(control_settings['tracking_stall_seconds'])
    print('CONTROL_SETTINGS '+json.dumps(control_settings),flush=True)
    print('GRIPPER_INPUT '+json.dumps(dict(mode='binary_0_1rad' if args.gripper_trigger_official_binary else 'existing_analog',threshold=.5,closed_action=1.-2./1.1 if args.gripper_trigger_official_binary else -1.)),flush=True)
    if args.gripper_trigger_official_binary:
        for side in ('left','right'):
            term=env.action_manager.get_term(side+'_gripper')
            for trigger in (0.,.49,.5,1.):
                command=controller.gripper_command(trigger)
                term.process_actions(torch.tensor([[command]],device=env.device))
                torch.testing.assert_close(term.processed_actions,torch.full_like(term.processed_actions,0. if trigger<.5 else 1.),rtol=0,atol=2e-7)
            term.process_actions(torch.ones((1,1),device=env.device))
        print('GRIPPER_BINARY_TARGET_CONTRACT_OK: actual processor 0/1rad; no physics step',flush=True)
    for left_grip,right_grip in ((1,1),(-1,1),(1,-1),(.25,-.75)):
        sample=torch.tensor([[.001,-.002,.003,.004,-.005,.006]*2+[left_grip,right_grip,controller.lift_action]],device=env.device)
        targets=env.action_to_target_eef_pose(sample)
        restored=env.target_eef_pose_to_action({k:v[0] for k,v in targets.items()},
            {k:v[0] for k,v in env.actions_to_gripper_actions(sample).items()})
        torch.testing.assert_close(restored,sample[0],atol=3e-5,rtol=5e-4)
    print('ACTION_CONTRACT_OK: unchanged 15D arms + independent analog grippers + lift',flush=True)
    if metadata:
        metadata.update(applied_reset_poses=reset_poses,seed=args.seed,
                        position_scale=controller.position_scale,rotation_scale=controller.rotation_scale,
                        max_translation_m=controller.max_translation,max_rotation_deg=control_settings['max_rotation_deg'],
                        control_settings=control_settings,grippers=('trigger_binary_0_1rad' if args.gripper_trigger_official_binary else 'trigger_analog') if args.enable_grippers else 'open',lift='fixed_at_reset')
        recorder=DiagnosticRecorder(env,metadata)
    def begin_waiting_audit():
        if timeline:
            env._replay_audit_episode=f'demo_{recorder.saved}'
            timeline.mark('before_waiting_renders')
    begin_waiting_audit()
    if sys.stdin.isatty():threading.Thread(target=console,daemon=True).start()
    print('READY / WAITING: X(left) or n+Enter = RESET & START; A(right) or s+Enter = SAVE & WAIT; Ctrl+C/q = exit.',flush=True)
    print('PREVIEW ONLY; no controller motion or recording' if args.preview_only else 'Release both squeezes before START, then re-squeeze to move.',flush=True)
    perf=PerformanceProbe(env)
    if args.contact_diagnostic:
        from contact_probe import ContactProbe
        contact_probe=ContactProbe(env,args.contact_diagnostic,run_id)
    start=previous=time.monotonic();preview_time=report_time=0.;episode_start=None
    start_blocked=False
    with torch.inference_mode():
        while app.is_running() and (args.keep_open or time.monotonic()-start<args.duration):
            tick=time.monotonic();snapshot=read_input(args.bridge_dir)
            phase_before=lifecycle.state
            reasons_before={s:v['reason'] for s,v in controller.states.items()}
            current=None;action_values=None;measured_time=None;target_generated_time=None
            requested=edges.commands(snapshot)
            while not commands.empty():requested.append(commands.get_nowait())
            if record_dir:
                for filename,cmd in (('start_recording','n'),('stop_recording','s')):
                    path=record_dir/filename
                    if path.exists():path.unlink();requested.append(cmd)
            if 'q' in requested:exit_reason='operator_exit';break
            expired=recorder and recorder.active and args.record_seconds>0 and tick-episode_start>=args.record_seconds
            if lifecycle.state=='RUNNING' and ('s' in requested or expired):
                reason='short_test_duration' if expired else 'manual_stop'
                if recorder:recorder.finish(reason)
                if timeline:timeline.mark('after_record_finish')
                begin_waiting_audit()
                lifecycle.finish(reason)
                for side in controller.states:controller.hold(side,'episode_waiting')
                print('EPISODE_WAITING '+reason,flush=True)
            elif 'n' in requested and lifecycle.state=='WAITING':
                allowed=args.preview_only or can_start(snapshot)
                if lifecycle.start(allowed):
                    start_blocked=False
                    if timeline:
                        env._replay_audit_episode=f'demo_{recorder.saved}'
                        timeline.mark('after_waiting_renders');timeline.mark('before_episode_reset')
                    env.reset(seed=args.seed)
                    report_gripper_runtime('after_episode_reset')
                    if timeline:timeline.mark('after_episode_reset')
                    reset_poses=applied_reset_poses(env,args.scenario_manifest,selected_id)
                    position_overview(env);controller=new_controller();episode_steps=0
                    tracking=TrackingMonitor(control_settings['tracking_stall_seconds'])
                    if timeline:
                        plate_configuration(env,metadata['timing'])
                        plate_checkpoint(env,'after_reset_before_physics',env.scene.get_state(is_relative=True))
                    if recorder:recorder.start(lifecycle.number,reset_poses,args.seed)
                    episode_start=time.monotonic()
                    print(f'EPISODE_STARTED {lifecycle.number} seed={args.seed}; release/re-squeeze required',flush=True)
                else:
                    start_blocked=True
                    print('START_BLOCKED: '+', '.join(start_blockers(snapshot)),flush=True)
            perf.begin()
            step_start=time.monotonic()
            decision_time=time.monotonic()
            if lifecycle.state=='RUNNING':
                current=poses()
                measured_time=time.monotonic()
                snapshot=read_input(args.bridge_dir)
                decision_time=time.monotonic()
                perf.received=snapshot.get('received_monotonic')
                if not args.preview_only:controller.update(snapshot,loop_gap=tick-previous>.25,measured=current)
                target_generated_time=time.monotonic()
                if controller.practice:
                    fault=tracking.check(controller,current,time.monotonic())
                    if fault:
                        if recorder:recorder.finish(fault[1])
                        lifecycle.finish(fault[1])
                        for side in controller.states:controller.hold(side,fault[1])
                        print('PRACTICE_STOP '+json.dumps(dict(side=fault[0],reason=fault[1],tracking=tracking.stats)),flush=True)
                        if diagnostic_log:diagnostic_log.write(json.dumps(dict(event='tracking_stop',reason=fault[1],tracking=tracking.stats))+'\n')
                        continue  # Do not apply the offending target or take another physics step.
                elif any(norm(sub(controller.targets[s][0],current[s][0]))>.08 for s in current):
                    raise RuntimeError('Wrist target error >8 cm')
                action_values=controller.action(current,dt)
                action=torch.tensor([action_values],device=env.device,dtype=torch.float32)
                if not torch.isfinite(action).all():raise RuntimeError('Nonfinite action')
                if recorder and recorder.active:
                    env.recorder_manager.add_to_episodes('timing/wall_monotonic',torch.tensor([[tick]],dtype=torch.float64,device=env.device))
                    env.recorder_manager.add_to_episodes('timing/simulation_time',env.episode_length_buf[:,None]*dt)
                if contact_probe:
                    contact_probe.begin(dict(episode_number=lifecycle.number,control_index=episode_steps,
                        recording=bool(recorder and recorder.active),expected_demo=None if not recorder else f'demo_{recorder.saved}',
                        action=action_values,input_snapshot=snapshot,control_states=controller.states,
                        latest_preview_frame_id=frame_id))
                try:
                    result=step_with_first_physics_checkpoint(env,action) if timeline and episode_steps==0 else env.step(action)
                finally:
                    if contact_probe:contact_probe.end()
                if timeline and episode_steps==0:
                    plate_checkpoint(env,'after_first_control_step');timeline.mark('after_first_control_step')
                episode_steps+=1
                if bool(result[2].any() or result[3].any()):
                    # Standard pre_reset already exported the terminal episode before automatic reset.
                    if timeline:timeline.mark('after_record_finish')
                    begin_waiting_audit()
                    report_gripper_runtime('after_automatic_episode_reset')
                    lifecycle.finish('environment_termination')
                    for side in controller.states:controller.hold(side,'episode_waiting')
                    print('EPISODE_WAITING: original termination fired; no further physics steps until START',flush=True)
            else:
                # Render only: no physics, rewards, episode clock or recorder rows in WAITING.
                if tick-preview_time>=1/args.preview_hz:env.sim.render()
            loop_gap=tick-previous>.25
            previous=tick;step_ms=(time.monotonic()-step_start)*1000
            telemetry=display_status(snapshot,controller,lifecycle,args.preview_only,start_blocked,current)
            telemetry['recording']=bool(recorder and recorder.active)
            telemetry['limits_hit']=controller.limits_hit
            if diagnostic_log and current is not None and tick-gripper_audit_time>=.5:
                gripper_audit_time=tick;grip_read_start=time.monotonic()
                # One small transfer at <=2 Hz, never an extra per-frame synchronization.
                joint_values=torch.stack([robot.data.joint_pos[0],robot.data.joint_pos_target[0],
                                         robot.data.joint_vel[0]]).detach().cpu().tolist()
                grip_values=[[row[i] for i in gripper_ids] for row in joint_values]
                diagnostic_log.write(json.dumps(dict(event='joint_sample',tick_monotonic=tick,
                    sampled_monotonic=time.monotonic(),input_seq=telemetry['input_seq'],
                    position=joint_values[0],target=joint_values[1],velocity=joint_values[2]))+'\n')
                diagnostic_log.write(json.dumps(dict(event='gripper_sample',tick_monotonic=tick,input_seq=telemetry['input_seq'],
                    trigger={s:telemetry['hands'][s]['trigger'] for s in ('left','right')},
                    command=dict(controller.grippers),measured_joint_rad=grip_values[0],joint_target_rad=grip_values[1],
                    joint_velocity_rad_s=grip_values[2],sample_read_ms=(time.monotonic()-grip_read_start)*1000))+'\n')
            telemetry['tracking_monitor']=tracking.stats if controller.practice else None
            stages=perf.report()
            stages['receive_to_target_ms']=None if target_generated_time is None or snapshot.get('received_monotonic') is None else (target_generated_time-snapshot['received_monotonic'])*1000
            stages['simulation_dt']=dt if lifecycle.state=='RUNNING' else 0
            if diagnostic_log and (lifecycle.state=='RUNNING' or requested or tick-preview_time>=1/args.preview_hz):
                diagnostic_log.write(json.dumps(dict(event='decision',tick_monotonic=tick,
                    phase_before=phase_before,requested=requested,reasons_before=reasons_before,
                    decision_monotonic=decision_time,
                    input_age_at_decision_ms=None if snapshot.get('received_monotonic') is None else (decision_time-snapshot['received_monotonic'])*1000,
                    loop_gap=loop_gap,step_ms=step_ms,frame_id=frame_id,teleop=telemetry,performance=stages,
                    input_snapshot=snapshot,measured_before_step=current,measured_sample_monotonic=measured_time,
                    target_generated_monotonic=target_generated_time,action=action_values,targets=controller.targets,
                    raw_targets=controller.raw_targets if action_values is not None else {},
                    reference_changes=controller.reference_changes if action_values is not None else [],
                    gripper_commands=dict(controller.grippers),
                    limits=dict(translation_m=controller.max_translation,rotation_rad=controller.max_rotation)))+'\n')
            if tick-preview_time>=1/args.preview_hz:
                preview_time=tick;captured=time.monotonic();pictures={};stats={}
                camera_start=time.monotonic()
                for name in ('head_cam','left_wrist_cam','right_wrist_cam'):
                    camera=env.scene.sensors[name]
                    if lifecycle.state=='WAITING':camera.update(dt,force_recompute=True)
                    rgb=camera.data.output['rgb'][0,:,:,:3].detach().cpu().numpy()
                    if rgb.dtype.name!='uint8' or rgb.ndim!=3 or rgb.shape[-1]!=3:raise RuntimeError(f'Unexpected camera format: {name}')
                    stats[name]=dict(shape=list(rgb.shape),dtype=str(rgb.dtype),minimum=int(rgb.min()),maximum=int(rgb.max()))
                    pictures[name]=Image.fromarray(rgb)
                stages['camera_readback_ms']=(time.monotonic()-camera_start)*1000
                encoded,encoding=encode_native_preview([pictures[n] for n in ('head_cam','left_wrist_cam','right_wrist_cam')])
                frame_id+=1
                if contact_probe:contact_probe.preview(frame_id,captured,{n:env.scene.sensors[n] for n in pictures})
                timings=dict(step_ms=step_ms,frame_interval_ms=None if last_capture is None else (captured-last_capture)*1000,
                             episode_state=lifecycle.state,episode_number=lifecycle.number,
                             teleop=telemetry,encoding=encoding,performance=stages,
                             simulation_time_s=float(env.episode_length_buf[0])*dt)
                last_capture=captured
                publish_preview(args.bridge_dir,encoded,run_id,frame_id,stats,timings,captured)
                if diagnostic_log:diagnostic_log.write(json.dumps(dict(event='preview',frame_id=frame_id,timings=timings))+'\n')
            if tick-report_time>=1:
                report_time=tick
                print(json.dumps(dict(scenario_id=selected_id,seed=args.seed,episode_state=lifecycle.state,
                    episode_number=lifecycle.number,recording=bool(recorder and recorder.active),
                    live=snapshot['live'],states={s:v['reason'] for s,v in controller.states.items()},frame_id=frame_id)),flush=True)
            time.sleep(max(0.,dt-(time.monotonic()-tick)))
except KeyboardInterrupt:
    exit_reason='KeyboardInterrupt';print('Ctrl+C: saving active diagnostic and closing.',flush=True)
except BaseException as error:
    exit_reason=f'{type(error).__name__}: {error}';print('TEST ERROR: '+exit_reason,flush=True);raise
finally:
    try:
        if diagnostic_log:
            diagnostic_log.write(json.dumps(dict(event='end',reason=exit_reason,monotonic=time.monotonic()))+'\n')
            diagnostic_log.close()
        if recorder:
            try:recorder.finish(exit_reason)
            finally:recorder.close()
        if record_dir:
            metadata['exit_reason']=exit_reason
            metadata=finalize_diagnostic(record_dir,metadata)
            print('RECORD_FINALIZED: '+json.dumps(metadata),flush=True)
    finally:
        try:stop_preview(args.bridge_dir,run_id,exit_reason)
        finally:
            if contact_probe:contact_probe.close()
            if perf:perf.close()
            if timeline:timeline.close()
            if env is not None:env.close()
            app.close()
