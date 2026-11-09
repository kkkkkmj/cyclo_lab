"""Isolated diagnostic scene. Robot/actions/sim from final task cfg; not full task test."""
import sys,argparse,json,time,traceback,fcntl,inspect,os,signal,faulthandler
from pathlib import Path
from types import SimpleNamespace as N
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE))
from common import SHA,sha,verify_checkout,table_plan,check_geometry
p=argparse.ArgumentParser();p.add_argument('--current-right-j3-speed-2p2',action='store_true');p.add_argument('--condition',choices=['current','official'],required=True);p.add_argument('--official-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--shared',type=Path,required=True);p.add_argument('--mode',choices=['plan','run'],required=True);p.add_argument('--bridge-dir',type=Path,required=True)
a,rest=p.parse_known_args()
repo=BASE.parents[1]
source=verify_checkout(a.official_root) if a.condition=='official' else repo
sys.path.insert(0,str(source/'source/cyclo_lab'))
from isaaclab.app import AppLauncher
AppLauncher.add_app_launcher_args(p);a=p.parse_args()
lock=(a.bridge_dir/'.simulation.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
a.output.mkdir(parents=True,exist_ok=False)
timeout_stacks=(a.output/'timeout_python_stacks.log').open('x')
faulthandler.register(signal.SIGUSR1,file=timeout_stacks,all_threads=True)
(a.output/'child_ready.json').write_text(json.dumps({'pid':os.getpid()}))
app=None;env=None;probe=None;code=1;state={'status':'failed','reason':'initialization'}
def save(name,x): (a.output/name).write_text(json.dumps(x,indent=2,default=str))
try:
 app=AppLauncher(a,fast_shutdown=False).app
 import torch,numpy as np,cyclo_lab,gymnasium as gym
 from pxr import Usd,UsdUtils,UsdGeom,UsdPhysics
 from isaaclab_tasks.utils.parse_cfg import parse_env_cfg
 from isaaclab.scene import InteractiveScene,InteractiveSceneCfg
 from isaaclab.assets import AssetBaseCfg
 import isaaclab.sim as sim_utils
 from isaaclab.managers import ActionManager
 import isaaclab.utils.math as math
 from contact_probe import ContactProbe,DiagnosticStop,value
 from contact_filter import read_contact
 from contact_geometry_snapshot import snapshot,geometry_record
 from auto_contact_protocol import Protocol
 task='Cyclo-PickPlace-FFW-BG2-IK-Rel-v0' if a.condition=='official' else 'Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2'
 if not Path(cyclo_lab.__file__).resolve().is_relative_to(source.resolve()):raise RuntimeError('Wrong cyclo_lab import path')
 cfg=parse_env_cfg(task,device=a.device,num_envs=1)
 if a.current_right_j3_speed_2p2:
  if a.condition!='current':raise ValueError('Current-only speed option cannot change official condition')
  from teleop_gripper_options import configure_right_j3_speed
  configure_right_j3_speed(cfg,True)
 save('task_final_config.json',cfg.to_dict());save('imports.json',{'cyclo_lab':cyclo_lab.__file__,'cfg':inspect.getfile(type(cfg)),'task':task,'sha':SHA if a.condition=='official' else None})
 # Capture composed dependencies; never replace missing official assets with local files.
 from asset_dependencies import audit
 usd=Path(cfg.scene.robot.spawn.usd_path)
 hashes=audit(usd,source,a.condition=='official',a.output/'asset_dependency_audit.json')
 save('asset_hashes.json',hashes)
 shared=json.loads(a.shared.read_text()) if a.shared.exists() else None
 if shared is None:
  if a.condition!='current' or a.mode!='plan':raise RuntimeError('Current geometry planning must run first')
  joint=dict(cfg.scene.robot.init_state.joint_pos);joint.update(cfg.events.init_ffw_bg2_pose.params['joint_positions'])
  joint.update({f'gripper_{side}_joint{i}':0. for side in ('l','r') for i in range(1,5)})
  shared={'joint_positions':joint,'robot_root':dict(pos=cfg.scene.robot.init_state.pos,rot=cfg.scene.robot.init_state.rot),'table':None}
 if shared.get('expected_robot_usd_sha256') and sha(usd)!=shared['expected_robot_usd_sha256']:raise RuntimeError('Frozen plan robot asset hash mismatch')
 # Common diagnostic starting posture, not the official reset/randomization scenario.
 robot_cfg=cfg.scene.robot.copy();robot_cfg.prim_path='{ENV_REGEX_NS}/Robot';robot_cfg.init_state.joint_pos=shared['joint_positions'];robot_cfg.init_state.pos=shared['robot_root']['pos'];robot_cfg.init_state.rot=shared['robot_root']['rot']
 table=shared['table'] or dict(center=[0,0,-10],size=[.1,.1,.02],material=dict(static_friction=1.,dynamic_friction=.8,restitution=0.,friction_combine_mode='max',restitution_combine_mode='max'))
 scene_cfg=InteractiveSceneCfg(num_envs=1,env_spacing=3.);scene_cfg.robot=robot_cfg
 scene_cfg.table=AssetBaseCfg(prim_path='{ENV_REGEX_NS}/DiagnosticTable',spawn=sim_utils.CuboidCfg(size=tuple(table['size']),collision_props=sim_utils.CollisionPropertiesCfg(contact_offset=.001,rest_offset=0.),physics_material=sim_utils.RigidBodyMaterialCfg(**table['material'])),init_state=AssetBaseCfg.InitialStateCfg(pos=tuple(table['center'])))
 sim=sim_utils.SimulationContext(cfg.sim);scene=InteractiveScene(scene_cfg);sim.reset();scene.reset();scene.update(cfg.sim.dt)
 class Harness:
  def __init__(self):
   self.cfg=N(scene=scene_cfg,decimation=cfg.decimation);self.scene=scene;self.sim=sim;self.physics_dt=cfg.sim.dt;self.step_dt=cfg.sim.dt*cfg.decimation;self.device=sim.device;self.num_envs=1;self._sim_step_counter=0
  def close(self):self.sim.clear_all_callbacks()
 env=Harness();manager=ActionManager(cfg.actions,env);env.action_manager=manager
 original_get=manager.get_term
 manager.get_term=lambda name:original_get('gripper_action' if a.condition=='official' and name=='right_gripper' else name)
 robot=scene['robot']
 # Initial state placement only, before any diagnostic physics step. Never repeated in loop.
 robot.write_root_pose_to_sim(robot.data.default_root_state[:,:7].clone())
 robot.write_root_velocity_to_sim(torch.zeros_like(robot.data.default_root_state[:,7:]))
 robot.write_joint_state_to_sim(robot.data.default_joint_pos.clone(),torch.zeros_like(robot.data.default_joint_vel))
 robot.set_joint_position_target(robot.data.default_joint_pos.clone())
 robot.set_joint_velocity_target(torch.zeros_like(robot.data.default_joint_vel))
 robot._physics_sim_view.update_articulations_kinematic();scene.reset();scene.update(0.)
 def pose(name):
  index=robot.body_names.index({'right':'arm_r_link7','left':'arm_l_link7','body':'arm_base_link'}[name]);return math.make_pose(robot.data.body_link_pos_w[0,index],math.matrix_from_quat(robot.data.body_link_quat_w[0,index]))
 initial={name:pose(name).clone() for name in ('right','left','body')}
 class Probe(ContactProbe):
  def sample(self):
   super().sample()
   if any(l['relative'] is None or abs(l['relative']['minus_direct_wrapped_rad'])>.001 or l['relative']['off_axis_residual_rad']>.01 for l in self.latest['links']):raise DiagnosticStop('link_angle_measurement_disagreement')
   contacts=[read_contact(v,s,env.physics_dt,self.native,details=True) for v,s in zip(self.contacts,self.contact_setup)]
   self.emit(dict(event='contact_details',physics_step_global=env._sim_step_counter,contacts=contacts,wrist_actual=pose('right').tolist()))
   if any(c['validation'] is None for c in contacts):raise DiagnosticStop('detailed_contact_invalid')
 probe=Probe(env,a.output/'contact.jsonl',a.condition,stop_on_excess=.05,require_contact=True)
 geometry=snapshot(env,probe,initial);save('geometry.json',geometry)
 # Do not assume mesh bounds are the cooked PhysX shape. Require resolved collider source.
 if shared['table'] is None:
  shared['table']=table_plan(geometry);shared['initial_right_wrist']=initial['right'].tolist();shared['condition_note']='shared diagnostic start/table, not official task objects/reset/observations'
  with a.shared.open('x') as f:json.dump(shared,f,indent=2)
 save('geometry_gate.json',check_geometry(geometry,shared['table']))
 if np.linalg.norm(np.array(shared['initial_right_wrist'])[:3,3]-initial['right'][:3,3].cpu().numpy())>.001:raise DiagnosticStop('initial_wrist_position_mismatch')
 if np.max(np.abs(np.array(shared['initial_right_wrist'])[:3,:3]-initial['right'][:3,:3].cpu().numpy()))>.001:raise DiagnosticStop('initial_wrist_orientation_mismatch')
 # Reject other robot collision bounds intersecting table during the short descent.
 from contact_geometry_snapshot import geometry_record
 transforms=robot.root_physx_view.get_link_transforms()[0].detach().cpu().numpy();others=[]
 for prim in Usd.PrimRange(sim.stage.GetPrimAtPath('/World/envs/env_0/Robot'),Usd.TraverseInstanceProxies()):
  if not prim.HasAPI(UsdPhysics.CollisionAPI):continue
  body=prim
  while body.IsValid() and not body.HasAPI(UsdPhysics.RigidBodyAPI):body=body.GetParent()
  if not body.IsValid():raise DiagnosticStop('collider_body_unresolved')
  bodyname=body.GetName();rec=geometry_record(sim.stage,str(prim.GetPath()),str(body.GetPath()),transforms[robot.body_names.index(bodyname)]);others.append(rec)
  if bodyname in [Path(f['bodies'][1]).name for f in probe.frames]:continue
  bounds=rec['world_vertex_bounds']
  if bounds is None:raise DiagnosticStop('other_robot_geometry_unresolved')
  from common import swept_aabb_evidence
  rec['swept_gate']=swept_aabb_evidence(bounds,shared['table'])
  rec['body_pose_xyzw']=transforms[robot.body_names.index(bodyname)].tolist()
  if rec['swept_gate']['swept_overlap']:
   save('other_robot_geometry.json',others)
   save('interference_failure.json',dict(body=str(body.GetPath()),collider=str(prim.GetPath()),evidence=rec['swept_gate'],reason='conservative_swept_bounds_overlap'))
   raise DiagnosticStop('other_robot_collider_in_swept_table_region')
 save('other_robot_geometry.json',others)
 runtime={k:value(fn) for k,fn in {'q':robot.root_physx_view.get_dof_positions,'limits':robot.root_physx_view.get_dof_limits,'motions':robot.root_physx_view.get_dof_motions,'stiffness':robot.root_physx_view.get_dof_stiffnesses,'damping':robot.root_physx_view.get_dof_dampings,'max_force':robot.root_physx_view.get_dof_max_forces,'max_velocity':robot.root_physx_view.get_dof_max_velocities}.items()}
 if any(v['value'] is None for v in runtime.values()):raise DiagnosticStop('runtime_readback_invalid')
 save('runtime.json',dict(joint_names=robot.joint_names,phase='after_sim_reset_before_commands',values=runtime,dt=env.physics_dt,decimation=cfg.decimation,solver=str(cfg.sim.physx),robot=str(robot_cfg),actions=str(cfg.actions),diagnostic_overrides=shared))
 # Adapt world target into each task's own action terms, not a 15D action passed to 7D.
 def action(target):
  parts=[]
  for name in manager.active_terms:
   term=original_get(name);tc=term.cfg
   if hasattr(tc,'controller'):
    side='left' if 'arm_l' in tc.body_name else 'right';cur=pose(side);want=target[side];bp=robot.data.root_pos_w[0];bq=robot.data.root_quat_w[0]
    cp,cq=math.subtract_frame_transforms(bp,bq,cur[:3,3],math.quat_from_matrix(cur[:3,:3]));tp,tq=math.subtract_frame_transforms(bp,bq,want[:3,3],math.quat_from_matrix(want[:3,:3]));dp,dr=math.compute_pose_error(cp[None],cq[None],tp[None],tq[None])
    if not tc.controller.use_relative_mode:raise DiagnosticStop('unsupported_absolute_action')
    parts.append(torch.cat((dp,dr),dim=-1)/float(tc.scale))
   elif 'gripper' in name:parts.append(torch.ones((1,term.action_dim),device=env.device))
   elif name=='lift':parts.append(((robot.data.joint_pos[:,robot.joint_names.index('lift_joint')]+.25)/.25)[:,None])
   else:raise DiagnosticStop('unsupported_action_term_'+name)
  return torch.cat(parts,dim=-1)
 protocol=Protocol(speed=.005,max_down=.025);index=0;last_contact=False
 if a.mode=='run':
  checks=[read_contact(v,s,env.physics_dt,probe.native,details=True) for v,s in zip(probe.contacts,probe.contact_setup)]
  if any(c['validation'] is None for c in checks):raise DiagnosticStop('contact_setup_invalid')
  while protocol.phase!='done':
   target={k:v.clone() for k,v in initial.items()};target['right'][2,3]-=protocol.down;measured=pose('right')
   if float(torch.linalg.vector_norm(target['right'][:3,3]-measured[:3,3]))>.01:raise DiagnosticStop('wrist_tracking_error_1cm')
   if shared['table'].get('support_mode')=='partial_distal' and float(torch.linalg.vector_norm(target['right'][:2,3]-measured[:2,3]))>.001:raise DiagnosticStop('partial_support_lateral_tracking_error_1mm')
   if shared['table'].get('support_mode')=='partial_distal' and float(torch.max(torch.abs(target['right'][:3,:3]-measured[:3,:3])))>.01:raise DiagnosticStop('partial_support_orientation_tracking_error')
   act=action(target);probe.begin(dict(episode_number=1,control_index=index,phase=protocol.phase,action=act[0].tolist(),target_wrist=target['right'].tolist(),actual_wrist_pre=measured.tolist()))
   try:
    manager.process_action(act)
    for _ in range(cfg.decimation):
     manager.apply_action();scene.write_data_to_sim();sim.step(render=False);env._sim_step_counter+=1;scene.update(env.physics_dt)
   finally:probe.end()
   last_contact=probe.control_contact
   if protocol.phase=='baseline' and (last_contact or any(np.linalg.norm(c['net']['value'])>1e-4 for c in probe.latest['contacts'])):raise DiagnosticStop('baseline_contact')
   protocol.advance(env.step_dt,last_contact);index+=1
   if index*env.step_dt>15:raise DiagnosticStop('protocol_budget')
  state=dict(status='completed',reason='contact_and_release' if protocol.contact_observed and not last_contact else 'contact_not_confirmed',contact_observed=protocol.contact_observed);code=0 if protocol.contact_observed and not last_contact else 3
 else:state=dict(status='completed',reason='geometry_only_no_physics_commands');code=0
except BaseException as e:
 traceback.print_exc();state=dict(status='limit_excess_captured' if str(e)=='joint_limit_excess' else 'failed',reason=f'{type(e).__name__}: {e}');code=2 if str(e)=='joint_limit_excess' else 1
finally:
 from auto_contact_shutdown import finish
 # Evidence only: no timeout, termination, skipped cleanup, or forced success.
 import faulthandler
 with (a.output/'shutdown_python_stacks.log').open('x') as stacks:
  try:
   if app is not None:
    try:save('installed_close_source.json',dict(path=inspect.getsourcefile(type(app)),source=inspect.getsource(type(app).close)))
    except Exception as e:save('installed_close_source.json',dict(error=repr(e)))
   faulthandler.dump_traceback_later(60,repeat=True,file=stacks)
   code=finish(app,env,probe,a.output/'outcome.json',state,code)
  finally:faulthandler.cancel_dump_traceback_later()
sys.exit(code)
