"""Supervise full recorded-action baseline, then one isolated candidate only if reproduced.
No VR, no new target path, no truncation, no automatic fix acceptance.
"""
import argparse,json,subprocess,sys,hashlib
from pathlib import Path

def baseline_gate(s):
    if not s or not s.get('complete_actions'):return 'baseline_incomplete'
    if s.get('checked')!=s.get('expected') or s.get('mismatched')!=0:return 'original_states_not_reproduced'
    if s.get('invalid_samples') or s.get('modes')!=[[1,1,1,1]]:return 'measurement_or_motion_unverified'
    if max(s.get('max_excess_rad',[0]))<=.05:return 'large_limit_excess_not_reproduced'
    if max(s.get('max_link_angle_error_rad',[1]))>.001:return 'link_angle_disagrees'
    if s.get('valid_table_contact_samples',0)==0:return 'table_contact_not_confirmed'
    return None

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--reference-contact',required=True);p.add_argument('--bridge-dir',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--compare-position-iterations',type=int,choices=[64]);p.add_argument('--reuse-baseline',type=Path);p.add_argument('--compare-half-physics-dt',action='store_true');p.add_argument('--compare-slave-gains',action='store_true');p.add_argument('--free-gripper-checks',action='store_true');a=p.parse_args()
    if sum(bool(x) for x in (a.compare_position_iterations,a.compare_half_physics_dt,a.compare_slave_gains))>1:p.error('Choose one factor')
    if a.free_gripper_checks and not (a.compare_half_physics_dt or a.compare_slave_gains):p.error('free checks require one supported candidate')
    if a.output.exists():p.error('New output folder required')
    gpu=subprocess.run(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],capture_output=True,text=True)
    if gpu.returncode or gpu.stdout.strip():raise RuntimeError('GPU accessibility/idle check failed; no simulation started: '+gpu.stdout+gpu.stderr)
    a.output.mkdir(parents=True);results={}
    script=Path(__file__).with_name('replay_checked.py')
    def run(name,candidate=None,half=False,free=False,slave=False):
        d=a.output/name
        app_close_returned=False;process_errors=[];execution_errors=[];reference_difference=False
        cmd=[sys.executable,str(script),'--dataset_file',a.dataset,'--task','Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2','--num_envs','1','--select_episode_names','demo_0','--validate_states','--headless','--enable_cameras','--bridge-dir',a.bridge_dir,'--contact-probe-dir',str(d),'--audit-dir',str(a.output/(name+'_scene'))]
        if candidate:cmd+=['--contact-solver-position-iterations',str(candidate)]
        if slave:cmd+=['--contact-slave-gains','--contact-baseline-provenance',str(baseline_dir/'provenance.json')]
        if half:cmd+=['--contact-half-physics-dt']
        if free:cmd.remove('--validate_states');cmd+=['--contact-free-gripper-check']
        with (a.output/(name+'.log')).open('x') as f:
            child=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
            for line in child.stdout:
                f.write(line);f.flush();print(line,end='',flush=True)
                if 'APP_CLOSE END' in line:app_close_returned=True
                if any(t in line.lower() for t in ('segmentation fault','fatal python error','core dumped')):process_errors.append(line.strip())
                if 'REPLAY_EXIT status=failed error=' in line:
                    if 'Diagnostic action replay state validation failed' in line:reference_difference=True
                    else:execution_errors.append(line.strip())
            rc=child.wait()
        summary=json.loads((d/'physical_summary.json').read_text()) if (d/'physical_summary.json').exists() else None
        results[name]=dict(command=cmd,process_exit=rc,app_close_returned=app_close_returned,process_errors=process_errors,execution_errors=execution_errors,reference_state_difference=reference_difference,physical_summary=summary)
        (a.output/'process_results.json').write_text(json.dumps(results,indent=2))
        return summary
    baseline_dir=a.output/'baseline'
    if a.reuse_baseline:
        baseline_dir=a.reuse_baseline.resolve()
        provenance=json.loads((baseline_dir/'provenance.json').read_text())
        if provenance['physics_dt']!=.01 or provenance['decimation']!=4 or provenance['candidate_position_iterations'] is not None:raise ValueError('Reused baseline must be original .01/4, no candidate')
        if provenance['dataset_sha256']!=hashlib.sha256(Path(a.dataset).read_bytes()).hexdigest():raise ValueError('Reused baseline dataset hash mismatch')
        b=json.loads((baseline_dir/'physical_summary.json').read_text())
        old=json.loads((baseline_dir.parent/'process_results.json').read_text())['baseline']
        results['baseline']=dict(old,reused_from=str(baseline_dir))
    else:b=run('baseline')
    block=baseline_gate(b)
    if not block and a.compare_position_iterations:run('candidate_pos64',a.compare_position_iterations)
    if not block and a.compare_half_physics_dt:run('candidate_dt005',half=True)
    if not block and a.compare_slave_gains:run('candidate_slave2',slave=True)
    if not block and a.free_gripper_checks:
        run('free_baseline',free=True)
        if a.compare_slave_gains:run('free_slave2',slave=True,free=True)
        else:run('free_dt005',half=True,free=True)
    results['comparison_block_reason']=block
    try:
        from compare_contact_replay import analyze
        candidate_dir=a.output/'candidate_pos64' if 'candidate_pos64' in results else (a.output/'candidate_dt005' if 'candidate_dt005' in results else (a.output/'candidate_slave2' if 'candidate_slave2' in results else None))
        report=analyze(a.reference_contact,baseline_dir,candidate_dir)
        (a.output/'comparison.json').write_text(json.dumps(report,indent=2))
    except Exception as e:results['analysis_error']=repr(e)
    results['note']='Candidate is an isolated hypothesis test, not a validated fix. Physics evidence and process/shutdown failure are separate. Candidate mismatch with original states is expected and remains reported.'
    (a.output/'process_results.json').write_text(json.dumps(results,indent=2))
    print('CONTACT_REPRO_COMPARE '+json.dumps(dict(output=str(a.output),comparison_block_reason=block,process_exits={k:v['process_exit'] for k,v in results.items() if isinstance(v,dict) and 'process_exit' in v})),flush=True)
    return 1 if block or 'analysis_error' in results or any(v['process_exit']!=0 for v in results.values() if isinstance(v,dict) and 'process_exit' in v) else 0
if __name__=='__main__':sys.exit(main())
