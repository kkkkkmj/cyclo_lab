"""At most 12 lines. No success based on lack of violation alone."""
import argparse,json
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
r=json.loads((a.output/'process_results.json').read_text());observations={};trajectories={}
for name,v in r.items():
 print(name,'child=',v['child_exit'],'effective=',v['effective_exit'],'reason=',(v['outcome'] or {}).get('reason'),'close=',(v['outcome'] or {}).get('app_close_completed'))
 if not name.endswith('_run'):continue
 q=a.output/name/'contact.jsonl';samples=0;contact=0;invalid=0;first=None;ex=np.zeros(4);first_bad=None
 poses={};samples_by_step={}
 if q.exists():
  for line in q.open():
   try:x=json.loads(line)
   except ValueError:invalid+=1;continue
   if x['event']=='contact_details':poses[x['physics_step_global']]=np.array(x['wrist_actual'])[:3,3]
   if x['event']!='physics':continue
   samples_by_step[x['physics_step_global']]=x
   samples+=1;valid=all(c['validation'] is not None for c in x['contacts']);invalid+=not valid
   point=valid and any(np.sum(c['counts'])>0 for c in x['contacts']);contact+=point
   if point and first is None:first=x['simulation_time_s']
   if x['limit_excess_rad'] is not None:
    ex=np.maximum(ex,x['limit_excess_rad'])
    if max(x['limit_excess_rad'])>1e-4 and first_bad is None:first_bad=x['simulation_time_s']
 print(' samples=',samples,'table_point_samples=',contact,'invalid=',invalid,'first_contact_s=',first,'first_excess_s=',first_bad,'max_excess_rad=',ex.tolist())
 observations[name]=(contact>0,invalid==0,float(max(ex[1],ex[3])))
 trajectories[name]={round(x['simulation_time_s'],8):poses[k] for k,x in samples_by_step.items() if k in poses}
 if first is not None:
  near=sorted((t,v) for t,v in trajectories[name].items() if first-.1<=t<=first)
  velocity=(near[-1][1]-near[0][1])/(near[-1][0]-near[0][0]) if len(near)>1 else None
  print(' contact_wrist=',trajectories[name].get(round(first,8)),'precontact_velocity_m_s=',velocity)
print('both_contact_valid=',len(observations)==2 and all(v[0] and v[1] for v in observations.values()))
print('Diagnostic robot+table test, not full official task validation. Zero force is not no contact. Match approach trajectories before causal comparison.')

if len(trajectories)==2:
 a,b=trajectories.values();times=sorted(a.keys()&b.keys());print('common_time_samples=',len(times),'max_wrist_difference_m=',max((float(np.linalg.norm(a[t]-b[t])) for t in times),default=None),'note=common timestamps only, no interpolation; stop-truncated histories')

if not observations.get('current_run',(False,False,0))[2]>.05:print('Current original excess not reproduced: no conclusion about official efficacy or general safety.')
