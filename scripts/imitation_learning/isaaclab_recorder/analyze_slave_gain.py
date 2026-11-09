"""Read-only per-joint contact/free-motion comparison. No force calibration claim."""
import argparse,json
from pathlib import Path
import numpy as np
from compare_contact_replay import compare

def analyze(path):
 rows=[];dt=None;names=None
 for line in Path(path).open():
  r=json.loads(line)
  if r['event']=='configuration':dt=r['physics_dt'];names=[x['name'] for x in r['frames']]
  if r['event']=='physics':rows.append(r)
 if not rows:return {'unavailable':'No physics samples'}
 q=np.array([r['direct_q']['value'] for r in rows]);target=np.array([r['target']['value'] for r in rows]);v=np.array([r['direct_velocity']['value'] for r in rows]);lim=np.array([r['hard_limits']['value'] for r in rows])
 if not np.isfinite([q,target,v]).all():raise ValueError('Nonfinite joint data')
 lo=np.maximum(lim[:,:,0]-q,0);hi=np.maximum(q-lim[:,:,1],0);ex=np.maximum(lo,hi)
 t=np.array([r['episode_physics_step']*dt for r in rows]);counts=np.array([sum(np.sum(c.get('counts') or []) for c in r['contacts']) for r in rows]);valid=np.array([len(r['contacts'])==4 and all(c.get('validation') is not None for c in r['contacts']) for r in rows]);contact=(counts>0)&valid
 def first(mask):
  ix=np.flatnonzero(mask)
  if not len(ix):return None
  i=int(ix[0]);return dict(step=rows[i]['episode_physics_step'],sim_s=float(t[i]),wrist=rows[i]['links'][0]['parent'])
 joints={}
 release=np.flatnonzero(contact[:-1]&~contact[1:])+1
 for j,n in enumerate(names):
  joints[n]=dict(first_excess=first(ex[:,j]>1e-4),first_gt_005=first(ex[:,j]>.05),max_lower_rad=float(lo[:,j].max()),max_upper_rad=float(hi[:,j].max()),outside_sample_s=float(np.sum(ex[:,j]>1e-4)*dt),max_abs_target_error_rad=float(np.max(abs(q[:,j]-target[:,j]))),max_abs_velocity_rad_s=float(np.max(abs(v[:,j]))),max_link_angle_error_rad=max(abs(r['links'][j]['relative']['minus_direct_wrapped_rad']) for r in rows),releases=[])
  for i in release:
   # Only observed zero-count samples, at most .5s. Zero count is not calibrated absence.
   end=i
   while end<len(rows) and end<i+round(.5/dt) and not contact[end] and valid[end]:end+=1
   if end>i:joints[n]['releases'].append(dict(sim_s=float(t[i]),window_s=float((end-i)*dt),initial_error_rad=float(q[i,j]-target[i,j]),last_error_rad=float(q[end-1,j]-target[end-1,j])))
 phases={}
 for phase in sorted({r['context'].get('phase','unknown') for r in rows}):
  ix=[i for i,r in enumerate(rows) if r['context'].get('phase','unknown')==phase];a=q[ix];g=target[ix];vel=v[ix]
  phases[phase]=dict(samples=len(ix),last_q=a[-1].tolist(),last_target=g[-1].tolist(),max_target_error=np.max(abs(a-g),axis=0).tolist(),max_abs_velocity=np.max(abs(vel),axis=0).tolist(),max_pair_angle_difference=[float(np.max(abs(a[:,0]-a[:,2]))),float(np.max(abs(a[:,1]-a[:,3])))],max_pair_velocity_difference=[float(np.max(abs(vel[:,0]-vel[:,2]))),float(np.max(abs(vel[:,1]-vel[:,3])))])
 force_info={}
 for kind in ('net','table'):
  forces=[np.asarray(c[kind]['value'],dtype=float) for r in rows for c in r['contacts'] if c[kind]['value'] is not None]
  force_info[kind]=dict(max_norm_n=max((float(np.linalg.norm(f)) for f in forces),default=None),available=len(forces),meaning='last-physics-step normal resultant, N; not measured drive torque')
 return dict(force_info=force_info,samples=len(rows),first_table_point=first(contact),invalid_contacts=int(np.sum(~valid)),table_point_samples=int(np.sum(contact)),max_points=float(counts.max()),joints=joints,phases=phases,note='Table count>0 with zero filtered force does not imply equal load. Release windows mean observed zero table counts, not proven all-body separation. PD effort is not measured torque.')

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():p.error('New output required')
 results=json.loads((a.run/'process_results.json').read_text());out={}
 for name in ('baseline','candidate_slave2','free_baseline','free_slave2'):
  item=results.get(name)
  if item is None:out[name]={'unavailable':'not run'};continue
  folder=Path(item.get('reused_from',str(a.run/name)))
  if str(folder).startswith('/workspace/cyclo_lab/') and not folder.exists():folder=Path(__file__).resolve().parents[3]/folder.relative_to('/workspace/cyclo_lab')
  out[name]=dict(physics=analyze(folder/'contact.jsonl') if (folder/'contact.jsonl').exists() else None,process={k:item.get(k) for k in ('process_exit','execution_errors','reference_state_difference','process_errors','app_close_returned')})
 with a.output.open('x') as f:json.dump(out,f,indent=2)
 for k,r in out.items():
  phys=r.get('physics') or {};print(k,json.dumps(dict(process=r.get('process'),samples=phys.get('samples'),first_table_point=phys.get('first_table_point'),joints={n:{kk:vv for kk,vv in x.items() if kk!='releases'} for n,x in phys.get('joints',{}).items()},phases=phys.get('phases') if k.startswith('free') else None)))
if __name__=='__main__':main()
