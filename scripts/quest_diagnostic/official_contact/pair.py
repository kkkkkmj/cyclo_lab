"""Sequential fresh-output supervisor; no running process termination."""
import argparse,json,subprocess,sys
from bounded_child import run_child
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from auto_contact_checked import effective_code,process_error
from common import verify_checkout,sha
p=argparse.ArgumentParser();p.add_argument('--current-plan-only',action='store_true');p.add_argument('--current-right-j3-speed-2p2',action='store_true');p.add_argument('--official-root',type=Path,required=True);p.add_argument('--bridge-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--partial-tip-plan',type=Path);p.add_argument('--child-timeout',type=float,default=600);p.add_argument('--shutdown-timeout',type=float,default=120);p.add_argument('--termination-grace',type=float,default=15);a=p.parse_args()
if min(a.child_timeout,a.shutdown_timeout,a.termination_grace)<=0:p.error('Timeouts must be positive')
verify_checkout(a.official_root)
if a.output.exists():p.error('New output directory required')
gpu=subprocess.run(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],capture_output=True,text=True)
if gpu.returncode or gpu.stdout.strip():raise SystemExit('GPU idle/access check failed; nothing launched: '+gpu.stdout+gpu.stderr)
a.output.mkdir(parents=True);shared=a.output/'shared_geometry_plan.json';results={}
if a.partial_tip_plan:
 plan=json.loads(a.partial_tip_plan.read_text())
 if plan['table'].get('support_mode')!='partial_distal':p.error('Expected explicit partial support plan')
 shared.write_text(json.dumps(plan,indent=2))
repo=Path(__file__).resolve().parents[3]
# Preserve actual production source/options without changing them.
files=list((repo/'source/cyclo_lab/cyclo_lab/assets/robots').glob('FFW_BG2.py'))+list((repo/'source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2').glob('*.py'))+list((repo/'scripts/quest_diagnostic').glob('*gripper*.py'))+[repo/'scripts/quest_diagnostic/teleop_toast.py']
snap=a.output/'current_source_snapshot';snap.mkdir()
for f in files:
 d=snap/f.relative_to(repo);d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(f.read_bytes())
(a.output/'current_source_hashes.json').write_text(json.dumps({str(f):sha(f) for f in files},indent=2))
schedule=[('plan','current')] if a.current_plan_only else [('plan','current'),('plan','official'),('run','current'),('run','official')]
for mode,condition in schedule:
 name=condition+'_'+mode;d=a.output/name;cmd=['/isaac-sim/python.sh',str(Path(__file__).with_name('run.py')),'--condition',condition,'--mode',mode,'--official-root',str(a.official_root),'--bridge-dir',str(a.bridge_dir),'--output',str(d),'--shared',str(shared),'--headless']
 if a.current_right_j3_speed_2p2 and condition=='current':cmd+=['--current-right-j3-speed-2p2']
 errors=[];native=[]
 supervision=run_child(cmd,a.output/(name+'.log'),d,a.child_timeout,a.shutdown_timeout,a.termination_grace)
 rc=supervision['child_exit']
 for line in (a.output/(name+'.log')).open(errors='replace'):
  if process_error(line):errors.append(line.strip())
  if ('omni.physx' in line or 'physics.tensors' in line) and any(t in line.lower() for t in ('[error]','did not match','overflow')):native.append(line.strip())
 try:outcome=json.loads((d/'outcome.json').read_text())
 except Exception:outcome=None
 eff=effective_code(rc,outcome,native)
 if errors:eff=1
 if supervision['forced_cleanup']:eff=124
 results[name]=dict(supervision=supervision,command=cmd,child_exit=rc,effective_exit=eff,process_errors=errors,native_errors=native,outcome=outcome)
 (a.output/'process_results.json').write_text(json.dumps(results,indent=2));print(name,eff, None if outcome is None else outcome.get('reason'),flush=True)
 if mode=='plan' and eff!=0:break
 # Physical capture code2 is evidence, not a reason to skip the other condition.
 if mode=='run' and eff not in (0,2,3):break
sys.exit(0 if len(results)==len(schedule) and all(x['effective_exit']==0 for x in results.values()) else 1)
