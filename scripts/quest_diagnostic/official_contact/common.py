"""Pure gates for independent robot+table diagnostic (not full official task)."""
import hashlib,json,subprocess
from pathlib import Path
import numpy as np
SHA='8ffc126b7c988c4e7ba20cfd5998eef50de27c01'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def verify_checkout(path):
 p=Path(path).resolve()
 def git(*args):return subprocess.check_output(['git','-C',str(p),*args],text=True).strip()
 if git('rev-parse','HEAD')!=SHA:raise ValueError('Official checkout SHA mismatch')
 if git('status','--porcelain','--untracked-files=no'):raise ValueError('Official tracked source modified')
 if any(l.startswith(('-', '+','U')) for l in git('submodule','status','--recursive').splitlines()):raise ValueError('Official submodule unresolved/mismatched')
 return p

def units(geometry):
 if geometry.get('meters_per_unit')!=1.0 or geometry.get('up_axis')!='Z':raise ValueError('Expected metre/Z-up geometry')

def table_plan(geometry):
 units(geometry)
 if geometry['errors'] or not geometry['fingers']:raise ValueError('Incomplete collider geometry')
 distal=[f['world_vertex_bounds'] for f in geometry['fingers'] if f['joint'] in ('gripper_r_joint2','gripper_r_joint4')]
 if len({f['joint'] for f in geometry['fingers'] if f['joint'] in ('gripper_r_joint2','gripper_r_joint4')})!=2:raise ValueError('Both distal geometries required')
 if any(x is None for x in distal):raise ValueError('Unresolved distal collision geometry')
 a=np.array(distal);lo=a[:,0].min(0);hi=a[:,1].max(0)
 if not np.isfinite(a).all() or np.any(hi<=lo):raise ValueError('Invalid geometry')
 if np.any((hi-lo)[:2]>.22):raise ValueError('Unexpected finger footprint')
 center=(lo+hi)/2;size=[float(hi[0]-lo[0]+.02),float(hi[1]-lo[1]+.02),.02];center[2]=lo[2]-.01-.01
 return dict(center=center.tolist(),size=size,speed_m_s=.005,max_down_m=.025,initial_gap_m=.01,source='Composed collision mesh vertex bounds, not cooked PhysX shape; no IK guarantee',material=dict(static_friction=1.,dynamic_friction=.8,restitution=0.,friction_combine_mode='max',restitution_combine_mode='max'))

def check_geometry(geometry,plan):
 if plan.get('support_mode')=='partial_distal':return check_partial_geometry(geometry,plan)
 units(geometry)
 if geometry['errors']:raise ValueError('Incomplete geometry')
 lo=np.array(plan['center'])-np.array(plan['size'])/2;hi=np.array(plan['center'])+np.array(plan['size'])/2
 tips=[f for f in geometry['fingers'] if f['joint'] in ('gripper_r_joint2','gripper_r_joint4')]
 if not tips:raise ValueError('No distal colliders')
 gaps=[]
 for f in tips:
  if f['world_vertex_bounds'] is None:raise ValueError('Missing bounds')
  mn,mx=np.array(f['world_vertex_bounds']);gap=mn[2]-hi[2]
  gaps.append(float(gap))
  if gap<.005:raise ValueError('Table overlaps or too close to a distal collider')
  if np.any(mn[:2]<lo[:2]) or np.any(mx[:2]>hi[:2]):raise ValueError('Finger outside table XY footprint')
 if not .005<=min(gaps)<=.02:raise ValueError('No distal collider within planned descent')
 return dict(valid=True,distal_gaps_m=gaps,all_distals_within_descent=all(g<plan['max_down_m'] for g in gaps),method='source collision bounds, runtime contact still required')

def swept_aabb_evidence(bounds,plan):
 """Conservative broad phase, not physical collision detection. Do not mutate bounds."""
 lo,hi=np.array(bounds,dtype=float);swept=lo.copy();swept[2]-=plan['max_down_m']
 tl=np.array(plan['center'])-np.array(plan['size'])/2;th=np.array(plan['center'])+np.array(plan['size'])/2
 if not np.isfinite([lo,hi,swept,tl,th]).all():raise ValueError('Nonfinite interference geometry')
 return dict(initial_bounds=[lo.tolist(),hi.tolist()],swept_bounds=[swept.tolist(),hi.tolist()],table_bounds=[tl.tolist(),th.tolist()],initial_overlap=bool(np.all(hi>=tl) and np.all(lo<=th)),swept_overlap=bool(np.all(hi>=tl) and np.all(swept<=th)),method='Source mesh AABB with pure world-Z descent; not actual collision/manifold')


def check_partial_geometry(geometry,plan):
 """Explicit partial support; retain full footprint gate for all other plans."""
 units(geometry)
 if geometry['errors']:raise ValueError('Incomplete geometry')
 lo=np.asarray(plan['center'])-np.asarray(plan['size'])/2
 hi=np.asarray(plan['center'])+np.asarray(plan['size'])/2
 if not np.isfinite([lo,hi]).all() or np.any(hi<=lo):raise ValueError('Invalid table')
 tips=[f for f in geometry['fingers'] if f['joint'] in ('gripper_r_joint2','gripper_r_joint4')]
 if {f['joint'] for f in tips}!={'gripper_r_joint2','gripper_r_joint4'}:raise ValueError('Both distal geometries required')
 matches=[];gaps={}
 for f in tips:
  points=np.concatenate([np.asarray(m['world_points'],dtype=float) for m in f['meshes']])
  if points.ndim!=2 or points.shape[1]!=3 or not np.isfinite(points).all():raise ValueError('Invalid source vertices')
  gap=float(points[:,2].min()-hi[2]);gaps[f['joint']]=gap
  if gap<.005:raise ValueError('Table too close to distal source geometry')
  if f['joint']==plan['direct_target_joint']:
   inside=points[(points[:,0]>lo[0]+.001)&(points[:,0]<hi[0]-.001)&(points[:,1]>lo[1]+.001)&(points[:,1]<hi[1]-.001)]
   if not len(inside):raise ValueError('No target collision vertex safely inside table')
   v=inside[inside[:,2].argmin()];matches.append(v)
 if not matches:raise ValueError('No target tip')
 v=min(matches,key=lambda x:x[2]);gap=float(v[2]-hi[2]);point=[float(v[0]),float(v[1]),float(hi[2])]
 if not .005<=gap<=.02:raise ValueError('Target outside planned approach')
 if np.linalg.norm(np.array(point)-plan['expected_contact_point_m'])>.001:raise ValueError('Target geometry differs from frozen plan')
 return dict(valid=True,support_mode='partial_distal',direct_target_joint=plan['direct_target_joint'],expected_contact_point_m=point,table_normal_world=[0,0,1],target_initial_gap_m=gap,distal_plane_gaps_m=gaps,method='Source collision vertices, NOT cooked PhysX contact or IK proof',joint4_direct_contact_verified=False)
