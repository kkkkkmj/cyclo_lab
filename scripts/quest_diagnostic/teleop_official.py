"""Official BG2 task + existing Quest transport; no demonstration recording."""
import argparse,fcntl,json,sys,time,secrets,inspect,subprocess,hashlib
from pathlib import Path
from bridge import read_input
from preview import stop_preview,publish_preview
from preview_encoding import encode_native_preview
from official_vr_control import OfficialController
from episode_control import EpisodeLifecycle,ButtonEdges,can_start
from display_status import display_status,start_blockers
from control import norm,sub

SHA='8ffc126b7c988c4e7ba20cfd5998eef50de27c01'
TASK='Cyclo-PickPlace-FFW-BG2-IK-Rel-v0'
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--official-root',type=Path,required=True)
p.add_argument('--bridge-dir',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--joint-log',action='store_true',help='Post control-step joint audit; not every physics substep')
p.add_argument('--preview-only',action='store_true')
a,_=p.parse_known_args();root=a.official_root.resolve()
def git(*args):return subprocess.check_output(['git','-c',f'safe.directory={root}','-C',str(root),*args],text=True).strip()
if git('rev-parse','HEAD')!=SHA or git('status','--porcelain','--untracked-files=no'):p.error('Official tracked checkout must match fixed clean commit')
if a.output.exists():p.error('New output directory required')
if not (a.bridge_dir/'input.json').exists():p.error('Start input server first')
lock=(a.bridge_dir/'.simulation.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
a.output.mkdir(parents=True);run=secrets.token_hex(12)
stop_preview(a.bridge_dir,run,'official_initializing_no_frames')
sys.path.insert(0,str(root/'source/cyclo_lab'))
from isaaclab.app import AppLauncher
AppLauncher.add_app_launcher_args(p);a=p.parse_args();a.enable_cameras=True
app=env=None;log=(a.output/'diagnostic.jsonl').open('x',buffering=1)
def emit(**x):log.write(json.dumps(x,default=str)+'\n')
try:
 app=AppLauncher(a).app
 import cyclo_lab,gymnasium as gym,torch
 from PIL import Image
 from isaaclab_tasks.utils.parse_cfg import parse_env_cfg
 from isaaclab.utils.math import subtract_frame_transforms
 source=(root/'source/cyclo_lab').resolve()
 def verify_imports():
  for name,m in list(sys.modules.items()):
   if name=='cyclo_lab' or name.startswith('cyclo_lab.'):
    f=getattr(m,'__file__',None)
    if f and not Path(f).resolve().is_relative_to(source):raise RuntimeError('Nonofficial import: '+str(f))
 verify_imports();cfg=parse_env_cfg(TASK,device=a.device,num_envs=1)
 # Presentation-only missing left sensor; never add it to policy observations.
 cfg.scene.left_wrist_cam=cfg.scene.right_wrist_cam.copy()
 cfg.scene.left_wrist_cam.prim_path=cfg.scene.right_wrist_cam.prim_path.replace('right_arm','left_arm').replace('arm_r_link7','arm_l_link7').replace('camera_r_','camera_l_').replace('right_wrist_cam','left_wrist_cam')
 (a.output/'config.json').write_text(json.dumps(cfg.to_dict(),default=str,indent=2))
 env=gym.make(TASK,cfg=cfg).unwrapped;env.reset();verify_imports()
 manager=env.action_manager;robot=env.scene['robot']
 assert manager.active_terms==['arm_action','gripper_action'] and manager.total_action_dim==7
 arm=manager.get_term('arm_action');grip=manager.get_term('gripper_action')
 assert arm.cfg.scale==.3 and arm.cfg.controller.use_relative_mode and arm.cfg.controller.ik_method=='dls'
 assert type(grip).__name__=='BinaryJointPositionAction'
 assert grip.cfg.open_command_expr=={'gripper_r_joint.*':0.} and grip.cfg.close_command_expr=={'gripper_r_joint.*':1.}
 names=[f'gripper_r_joint{i}' for i in range(1,5)];ids=[robot.joint_names.index(n) for n in names]
 def read(fn):
  try:return dict(value=fn().detach().cpu().tolist(),error=None)
  except Exception as e:return dict(value=None,error=repr(e))
 v=robot.root_physx_view
 emit(event='startup',robot_usd=cfg.scene.robot.spawn.usd_path,robot_usd_sha256=hashlib.sha256(Path(cfg.scene.robot.spawn.usd_path).read_bytes()).hexdigest(),task=TASK,sha=SHA,import_path=cyclo_lab.__file__,config_class=inspect.getfile(type(cfg)),action_terms=manager.active_terms,arm=str(arm.cfg),gripper=str(grip.cfg),gripper_type=type(grip).__name__,joint_names=names,indices=ids,dt=env.physics_dt,control_dt=env.step_dt,stiffness=read(lambda:v.get_dof_stiffnesses()[0,ids]),damping=read(lambda:v.get_dof_dampings()[0,ids]),max_force=read(lambda:v.get_dof_max_forces()[0,ids]),max_velocity=read(lambda:v.get_dof_max_velocities()[0,ids]),limits=read(lambda:v.get_dof_limits()[0,ids]))
 print('OFFICIAL_IMPORT_OK',cyclo_lab.__file__,flush=True)
 def poses():
  pos,q=arm._compute_frame_pose();q=q[0].tolist();right=(pos[0].tolist(),q[1:]+q[:1])
  i=robot.body_names.index('arm_l_link7');lp,lq=subtract_frame_transforms(robot.data.root_pos_w,robot.data.root_quat_w,robot.data.body_pos_w[:,i],robot.data.body_quat_w[:,i]);lq=lq[0].tolist()
  return dict(right=right,left=(lp[0].tolist(),lq[1:]+lq[:1]))
 lifecycle=EpisodeLifecycle();edges=ButtonEdges();controller=OfficialController(poses());frame=0;last_preview=0.;previous=time.monotonic();blocked=False;step=0
 print('READY WAITING: X reset/start; A stop; right squeeze clutch; trigger >=0.5 closes. NO REC',flush=True)
 with torch.inference_mode():
  while app.is_running():
   tick=time.monotonic();snapshot=read_input(a.bridge_dir);commands=edges.commands(snapshot)
   if 's' in commands:
    lifecycle.finish('manual_stop')
   elif 'n' in commands and lifecycle.state=='WAITING' and not a.preview_only:
    if can_start(snapshot):
     env.reset();controller=OfficialController(poses());lifecycle.start(True);blocked=False;step=0
    else:blocked=True;print('START_BLOCKED',start_blockers(snapshot),flush=True)
   current=poses();values=None
   if lifecycle.state=='RUNNING':
    controller.update(snapshot,loop_gap=tick-previous>.25,measured=current)
    if norm(sub(controller.targets['right'][0],current['right'][0]))>.08:
     lifecycle.finish('tracking_error_8cm')
    else:
     values=controller.action(current,env.step_dt)
     result=env.step(torch.tensor([values],device=env.device,dtype=torch.float32));step+=1
     if a.joint_log:
      emit(event='post_control_step',episode=lifecycle.number,control_step=step,physics_step=int(env._sim_step_counter),monotonic=time.monotonic(),simulation_elapsed_s=step*env.step_dt,input=snapshot,states=controller.states,action=values,joint_names=names,target=read(lambda:robot.data.joint_pos_target[0,ids]),position=read(lambda:robot.data.joint_pos[0,ids]),velocity=read(lambda:robot.data.joint_vel[0,ids]),limits=read(lambda:v.get_dof_limits()[0,ids]),terminal_step=bool(result[2].any() or result[3].any()),note='post env.step; terminal step may already auto-reset; not all substeps')
     if bool(result[2].any() or result[3].any()):lifecycle.finish('official_environment_termination')
   if lifecycle.state=='WAITING':
    for side in controller.states:controller.hold(side,'episode_waiting')
    if tick-last_preview>=.1:env.sim.render()
   previous=tick
   if tick-last_preview>=.1:
    last_preview=tick;captured=time.monotonic();pictures=[];stats={}
    for name in ('head_cam','left_wrist_cam','right_wrist_cam'):
     camera=env.scene.sensors[name]
     if lifecycle.state=='WAITING':camera.update(env.step_dt,force_recompute=True)
     rgb=camera.data.output['rgb'][0,:,:,:3].detach().cpu().numpy()
     if rgb.dtype.name!='uint8' or rgb.ndim!=3 or rgb.shape[-1]!=3:raise RuntimeError('Missing/invalid camera '+name)
     pictures.append(Image.fromarray(rgb));stats[name]=dict(shape=list(rgb.shape),dtype=str(rgb.dtype),minimum=int(rgb.min()),maximum=int(rgb.max()))
    encoded,encoding=encode_native_preview(pictures);frame+=1
    telemetry=display_status(snapshot,controller,lifecycle,a.preview_only,blocked,current);telemetry['recording']=False
    publish_preview(a.bridge_dir,encoded,run,frame,stats,dict(episode_state=lifecycle.state,episode_number=lifecycle.number,teleop=telemetry,encoding=encoding,task=TASK),captured)
   time.sleep(max(0.,env.step_dt-(time.monotonic()-tick)))
except KeyboardInterrupt:emit(event='exit',reason='KeyboardInterrupt')
finally:
 stop_preview(a.bridge_dir,run,'official_producer_stopped');log.close()
 if env is not None:env.close()
 if app is not None:app.close()
