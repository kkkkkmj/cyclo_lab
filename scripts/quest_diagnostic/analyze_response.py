import argparse,json,sys,statistics,collections,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from control import norm,sub,rotvec,qmul,qinv
parser=argparse.ArgumentParser(description='RUNNING-only trace analysis; active ratios require actual active samples')
parser.add_argument('--log',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();p=args.log
values=collections.defaultdict(list);counts=collections.Counter();phases=collections.Counter();prev=None;sim=wall=0;last=None
for line in p.open():
 try:r=json.loads(line)
 except ValueError:continue
 if r.get('event')=='decision':
  t=r['teleop'];phases[t['episode_state']]+=1
  if t['episode_state']!='RUNNING':prev=None;continue
  counts['running_steps']+=1
  counts['recording_steps']+=int(t.get('recording',False))
  if prev is not None and r['phase_before']=='RUNNING' and 0<r['tick_monotonic']-prev<1:
   wall+=r['tick_monotonic']-prev;sim+=.04
  prev=r['tick_monotonic'];perf=r.get('performance',{})
  for k,v in perf.get('wall_call_ms',{}).items():values['running_'+k].append(v)
  for k in ['receive_to_process_ms','receive_to_first_apply_ms','receive_to_first_physics_ms']:
   if isinstance(perf.get(k),(float,int)):values[k].append(perf[k])
  values['running_step_ms'].append(r['step_ms'])
  for side,h in t['hands'].items():
   counts[side+':'+h['control_reason']]+=1
   if h['active']:
    counts[side+'_active_samples']+=1
    for key,hit in t.get('limits_hit',{}).get(side,{}).items():counts[side+'_hit_'+key]+=int(hit)
    e=h['tracking_error_m'];values[side+'_active_error_m'].append(e)
    if 'limits_hit' not in t:counts[side+'_legacy_linear_clipped_inferred']+=int(e>.1*.04+1e-7)
    q=r['targets'][side][1];mq=r['measured_before_step'][side][1];angle=norm(rotvec(qmul(q,qinv(mq))))
    values[side+'_active_rotation_error_rad'].append(angle);counts[side+'_legacy_angular_clipped_inferred']+=int('limits_hit' not in t and angle>.8*.04+1e-7)
    counts[side+'_at_lead_limit']+=int(e>=.0399)
    values[side+'_home_distance_m'].append(h['home_distance_m'])
  last=r
 elif r.get('event')=='preview' and r['timings']['episode_state']=='RUNNING':
  t=r['timings'];perf=t.get('performance',{})
  for k in ['camera_readback_ms']:
   if k in perf:values[k].append(perf[k])
  values['encode_ms'].append(t['encoding']['encode_ms']);values['preview_interval_ms'].append(t['frame_interval_ms'])
  pr=t['teleop'].get('preview') or {}
  for k in ['fetch_decode_ms','decode_ms','frame_age_ms']:
   if isinstance(pr.get(k),(int,float)):values['quest_'+k].append(pr[k])
def stats(v):
 v=sorted(x for x in v if x is not None);return dict(n=len(v),median=statistics.median(v),p95=v[min(len(v)-1,int(len(v)*.95))],max=max(v)) if v else None
out=dict(source=str(p),phases=phases,counts=counts,running_sim_s=sim,running_wall_s=wall,ratio=sim/wall if wall else None,metrics={k:stats(v) for k,v in values.items()})
out['active_limit_ratios']={side:{k:counts[k]/counts[side+'_active_samples'] for k in counts if k.startswith(side+'_hit_')} if counts[side+'_active_samples'] else None for side in ['left','right']}
args.output.parent.mkdir(parents=True,exist_ok=True)
with args.output.open('x') as file:json.dump(out,file,indent=2)
print(json.dumps(out,indent=2))
