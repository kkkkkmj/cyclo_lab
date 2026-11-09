"""CPU summary of existing ContactProbe fields; unknown/aborted runs stay unknown."""
import argparse
import json
import hashlib
from pathlib import Path
import numpy as np


def log_lines(folder):
    with (Path(folder)/'contact.jsonl').open() as stream:
        yield from stream


def process_status(folder):
    path=Path(folder).with_suffix('.supervisor.json')
    if not path.exists():return dict(verified=False,reason='supervisor_report_missing',process_exit_clean=None)
    r=json.loads(path.read_text())
    return dict(verified=True,**{k:r.get(k) for k in ('child_exit','effective_exit','process_exit_clean','process_errors','native_errors')})


def observation_summary(folder):
    folder=Path(folder);groups={};times=[];separations=[];forces=[];stops=[];samples=0;detail_samples=0
    for line in log_lines(folder):
        r=json.loads(line)
        if r['event'] in ('sample_error','automatic_stop'):stops.append(dict(event=r['event'],reason=r['reason']))
        if r['event']!='physics':continue
        samples+=1;c=r['context'];t=r['simulation_time_s'];phase=c['phase']
        detail_samples+=int(len(r.get('all_pair_contacts',[]))==4 and all(x.get('details') is not None for x in r['all_pair_contacts']))
        if r.get('contact_pairs'):times.append(dict(episode=c['episode_number'],time_s=t,phase=phase,pairs=r['contact_pairs']))
        for contact in r.get('all_pair_contacts',[]):
            details=contact.get('details') or []
            separations.extend(s for d in details for s in d['separation_m'])
            if contact.get('details') is not None:forces.append(sum(abs(f) for d in details for f in d['normal_force_n']))
        q=np.array(r['direct_q']['value']);v=np.array(r['direct_velocity']['value'])
        tips=np.array(r['symmetry']['tip_centers_wrist_m'])
        keys=[f"episode{c['episode_number']}/{phase}"]
        if phase=='closed_hold' and t>=3.2:keys.append(f"episode{c['episode_number']}/closed_hold_after_0p2s")
        net=max((float(np.linalg.norm(x['net']['value'])) for x in r['all_pair_contacts'] if x['net']['value'] is not None),default=0.)
        for key in keys:groups.setdefault(key,[]).append(dict(q=q,v=v,pair=bool(r.get('contact_pairs')),
            excess=max(r['limit_excess_rad']),gap=r['symmetry']['tip_projected_gap_m'],net=net,
            mirror=float(np.linalg.norm(tips[0]-tips[1]*[1,-1,1]))))
    phases={}
    for key,rows in groups.items():
        q=np.array([r['q'] for r in rows]);v=np.array([r['v'] for r in rows])
        phases[key]=dict(samples=len(rows),angle_difference_max_rad=[float(np.abs(q[:,i]-q[:,j]).max()) for i,j in ((0,2),(1,3))],
            velocity_difference_max_rad_s=[float(np.abs(v[:,i]-v[:,j]).max()) for i,j in ((0,2),(1,3))],
            joint_angle_span_rad=np.ptp(q,axis=0).tolist(),joint_max_abs_velocity_rad_s=np.abs(v).max(axis=0).tolist(),
            tip_mirror_error_max_m=max(r['mirror'] for r in rows),projected_gap_range_m=[min(r['gap'] for r in rows),max(r['gap'] for r in rows)],
            contact_samples=sum(r['pair'] for r in rows),max_net_contact_force_n=max(r['net'] for r in rows),max_limit_excess_rad=max(r['excess'] for r in rows))
    runtime_path=folder/'runtime_settings.jsonl'
    runtime=[json.loads(x) for x in runtime_path.read_text().splitlines()] if runtime_path.exists() else []
    return dict(outcome=json.loads((folder/'outcome.json').read_text()),process=process_status(folder),samples=samples,
        detailed_contact_samples=detail_samples,
        runtime_checkpoints=len(runtime),runtime_checkpoints_verified=bool(runtime) and all(x.get('verified') for x in runtime),
        contact_samples=len(times),first_contact=times[0] if times else None,last_contact=times[-1] if times else None,
        min_reported_contact_separation_m=min(separations) if separations else None,
        max_pair_normal_force_sum_n=max(forces) if forces else None,
        max_limit_excess_rad=max((r['max_limit_excess_rad'] for r in phases.values()),default=None),
        phases=phases,stops=stops,
        note='Contact report is not a failure. Separation is at reported PhysX contacts, not global surface distance. Settled hold spans/velocities are observations, not automatic oscillation diagnosis. No measured drive torque.')


def comparison_data(folder):
    """Stream existing logs; retain small metrics, never rewrite input results."""
    folder=Path(folder);phases={};digest=hashlib.sha256();resets=[];errors=[]
    limits=[];settings=[];count=0;invalid_contacts=0;pair_samples=0
    for line in log_lines(folder):
        r=json.loads(line)
        if r['event']=='fresh_reset':resets.append({k:r[k] for k in ('episode','q','velocity')})
        if r['event'] in ('sample_error','automatic_stop'):errors.append(r)
        if r['event']!='physics':continue
        count+=1;c=r['context']
        # Arm IK corrections depend on measured response; they need not be bitwise
        # identical after changing gripper dynamics. Compare gripper input/targets.
        digest.update(json.dumps([c['episode_number'],c['control_index'],r['substep'],c['phase'],c['trigger'],c['action'][12:14]],separators=(',',':')).encode())
        q=np.asarray(r['direct_q']['value'],dtype=float);v=np.asarray(r['direct_velocity']['value'],dtype=float)
        target=np.asarray(r['target']['value'],dtype=float)
        if q.shape!=(4,) or v.shape!=(4,) or target.shape!=(4,) or not np.isfinite([q,v,target]).all():
            raise ValueError('Invalid joint sample')
        digest.update(json.dumps(target.tolist(),separators=(',',':')).encode())
        contacts=r.get('all_pair_contacts',[])
        invalid=not contacts or any(x.get('validation') is None or x.get('counts') is None for x in contacts)
        pairs=bool(r.get('contact_pairs')) or any(x.get('counts') is not None and np.any(np.asarray(x['counts'])>0) for x in contacts)
        invalid_contacts+=int(invalid);pair_samples+=int(pairs)
        excess=r.get('limit_excess_rad')
        if excess is None:raise ValueError('Missing limit readback')
        net=max((float(np.linalg.norm(x['net']['value'])) for x in contacts if x['net']['value'] is not None),default=0.)
        key=f"episode{c['episode_number']}/{c['phase']}"
        phases.setdefault(key,[]).append([q[0]-q[2],v[0]-v[2],max(excess),np.ptp(target),int(pairs),int(invalid),net])
        limits.append(r['velocity_limit']['value'])
        settings.append([r[k]['value'] for k in ('effort_limit','stiffness','damping','hard_limits')])
        if r.get('runtime_settings_error'):errors.append(r['runtime_settings_error'])
    out={}
    for phase,rows in phases.items():
        a=np.asarray(rows)
        out[phase]=dict(samples=len(rows),angle_max_abs_rad=float(np.max(np.abs(a[:,0]))),
            angle_rms_rad=float(np.sqrt(np.mean(a[:,0]**2))),velocity_max_abs_rad_s=float(np.max(np.abs(a[:,1]))),
            velocity_rms_rad_s=float(np.sqrt(np.mean(a[:,1]**2))),max_limit_excess_rad=float(a[:,2].max()),
            max_target_spread_rad=float(a[:,3].max()),contact_samples=int(a[:,4].sum()),invalid_contact_samples=int(a[:,5].sum()),
            max_net_contact_force_n=float(a[:,6].max()))
    return dict(phases=out,samples=count,command_sha256=digest.hexdigest(),resets=resets,errors=errors,
        reported_contact_samples=pair_samples,invalid_contact_samples=invalid_contacts,
        velocity_limits=limits,right_settings=settings,
        provenance=json.loads((folder/'provenance.json').read_text()),outcome=json.loads((folder/'outcome.json').read_text()))


def compare(baseline,candidate):
    a=comparison_data(baseline);b=comparison_data(candidate);checks={}
    for key in ('task','scenario','seed','usd_sha256','dt','physics_dt','protocol','close_angle','actuators','command_source'):
        checks['same_'+key]=key in a['provenance'] and a['provenance'][key]==b['provenance'].get(key)
    checks['endpoint_1p0']=a['provenance']['close_angle']==b['provenance']['close_angle']==1.0
    checks['identical_gripper_commands_targets_and_samples']=a['samples']>0 and a['samples']==b['samples'] and a['command_sha256']==b['command_sha256']
    checks['same_production_code']=({k:v for k,v in a['provenance']['code_sha256'].items() if k.startswith('source/')} ==
                                    {k:v for k,v in b['provenance']['code_sha256'].items() if k.startswith('source/')})
    checks['same_zero_resets']=a['resets']==b['resets'] and len(a['resets'])==2 and all(
        max(map(abs,r['q']+r['velocity']))<=1e-5 for r in a['resets'])
    checks['candidate_requested']=b['provenance'].get('velocity_condition')=='right_j3_2p2'
    for name,data,want in [('baseline',a,[2.2,6.5,6.5,6.5]),('candidate',b,[2.2,6.5,2.2,6.5])]:
        checks[name+'_right_velocity_readbacks']=bool(data['velocity_limits']) and bool(np.allclose(data['velocity_limits'],want,atol=1e-6,rtol=0))
        checks[name+'_completed']=data['outcome'].get('status')=='completed' and data['outcome'].get('app_close_completed') is True and not data['outcome'].get('cleanup_errors')
        checks[name+'_valid_no_reported_contact']=data['invalid_contact_samples']==data['reported_contact_samples']==0 and not data['errors']
        checks[name+'_no_unattributed_force']=all(x['max_net_contact_force_n']<=1e-4 for x in data['phases'].values())
    checks['same_right_effort_gains_limits']=a['right_settings']==b['right_settings']
    runtime=Path(candidate)/'runtime_settings.jsonl'
    runtime_rows=[json.loads(x) for x in runtime.read_text().splitlines()] if runtime.exists() else []
    from free_gripper import VelocityCondition
    runtime_ok=len(runtime_rows)==5
    for r in runtime_rows:
        runtime_ok &= r.get('verified') is True and r.get('candidate') is True
        expected=json.loads(json.dumps(r['before']))
        runtime_ok &= bool(np.allclose(expected['velocity'][VelocityCondition.JOINT],6.5,atol=1e-6,rtol=0))
        expected['velocity'][VelocityCondition.JOINT]=[2.2]*len(expected['velocity'][VelocityCondition.JOINT])
        for key in expected:
            runtime_ok &= expected[key].keys()==r['actual'][key].keys() and all(
                np.allclose(v,r['actual'][key][n],atol=1e-6,rtol=0) for n,v in expected[key].items())
    checks['all_dof_runtime_single_change_verified']=bool(runtime_ok)
    rows={}
    for phase in sorted(a['phases'].keys()|b['phases'].keys()):
        left=a['phases'].get(phase);right=b['phases'].get(phase)
        rows[phase]=dict(baseline=left,candidate=right)
        if left and right:
            rows[phase]['candidate_minus_baseline']={k:right[k]-left[k] for k in ('angle_max_abs_rad','angle_rms_rad','velocity_max_abs_rad_s','velocity_rms_rad_s','max_limit_excess_rad','contact_samples')}
    processes=dict(baseline=process_status(baseline),candidate=process_status(candidate))
    return dict(baseline=str(baseline),candidate=str(candidate),comparison_valid=all(checks.values()),checks=checks,phases=rows,
        processes=processes,execution_clean=all(x.get('process_exit_clean') is True and x.get('effective_exit')==0 for x in processes.values()),
        outcomes=dict(baseline=a['outcome'],candidate=b['outcome']),
        note='comparison_valid concerns recorded physics/protocol; execution_clean separately checks supervisor process exit. j1 versus j3. Aborted/mismatched/contaminated runs are not valid free-motion comparisons. No measured drive torque: effort saturation cannot be concluded.')


def summarize(folder):
    folder=Path(folder);groups={};errors=[];resets=[];contacts=[]
    for line in log_lines(folder):
        r=json.loads(line)
        if r['event']=='fresh_reset':resets.append(r)
        if r['event'] in ('sample_error','automatic_stop'):errors.append(r)
        if r['event']!='physics':continue
        if r.get('contact_pairs'):contacts.append(dict(step=r['physics_step_global'],pairs=r['contact_pairs']))
        key=f"episode{r['context']['episode_number']}/{r['context']['phase']}"
        groups.setdefault(key,[]).append(r)
    out={}
    for key,rows in groups.items():
        metrics={k:[r['symmetry'][k] for r in rows] for k in ('target_spread_rad','proximal_error_rad','distal_error_rad','proximal_velocity_error','distal_velocity_error','tip_projected_gap_m')}
        out[key]=dict(samples=len(rows),metrics={k:dict(min=float(min(v)),max=float(max(v)),rms=float(np.sqrt(np.mean(np.square(v))))) for k,v in metrics.items()},
            max_limit_excess_rad=max(max(r['limit_excess_rad']) for r in rows if r['limit_excess_rad'] is not None),
            actual_angle_range=[np.min([r['direct_q']['value'] for r in rows],axis=0).tolist(),np.max([r['direct_q']['value'] for r in rows],axis=0).tolist()],
            max_abs_velocity=np.max(np.abs([r['direct_velocity']['value'] for r in rows]),axis=0).tolist())
    outcome=json.loads((folder/'outcome.json').read_text())
    return dict(source=str(folder),resets=resets,groups=out,contact_events=contacts,errors=errors,outcome=outcome,
                physical_symmetry_acceptance='not automatic: compare matched endpoint, phase, reset and code hashes',
                no_contact_claim='no reported pairs only; not external calibration or guarantee of all-scene separation')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folders',type=Path,nargs='*')
    p.add_argument('--baseline',type=Path);p.add_argument('--candidate',type=Path);p.add_argument('--output',type=Path)
    p.add_argument('--observation',type=Path);p.add_argument('--brief',action='store_true')
    a=p.parse_args()
    if a.observation:
        if a.baseline or a.candidate or a.folders:p.error('Observation mode takes one folder')
        report=observation_summary(a.observation)
        if a.output:
            with a.output.open('x') as f:json.dump(report,f,indent=2)
        if a.brief:
            print(json.dumps({k:report[k] for k in ('samples','contact_samples','min_reported_contact_separation_m','max_pair_normal_force_sum_n','max_limit_excess_rad','runtime_checkpoints_verified')},ensure_ascii=False))
            print('status='+report['outcome']['status']+' reason='+report['outcome']['reason']+' process_clean='+str(report['process']['process_exit_clean']))
            for k,v in report['phases'].items():
                if 'closed_hold_after' in k or 'settle_open' in k:
                    print(k,json.dumps({n:v[n] for n in ('angle_difference_max_rad','joint_angle_span_rad','joint_max_abs_velocity_rad_s','contact_samples')}))
            print('Next: inspect hold/release and stop reasons; do not treat contact reports alone as a fault.')
        else:print(json.dumps(report,indent=2))
        raise SystemExit(0)
    if a.baseline or a.candidate or a.output:
        if not (a.baseline and a.candidate and a.output) or a.folders:p.error('Use --baseline --candidate --output together, without folders')
        if a.output.exists():p.error('Comparison output already exists; no overwrite')
        report=compare(a.baseline,a.candidate)
        with a.output.open('x') as f:json.dump(report,f,indent=2)
        print(json.dumps(dict(comparison_valid=report['comparison_valid'],execution_clean=report['execution_clean'],failed_checks=[k for k,v in report['checks'].items() if not v],output=str(a.output)) if a.brief else report,indent=2))
        raise SystemExit(0 if report['comparison_valid'] else 2)
    if not a.folders:p.error('Provide folders or comparison arguments')
    for folder in a.folders:
        report=summarize(folder)
        with (folder/'free_summary.json').open('x') as f:json.dump(report,f,indent=2)
        print(json.dumps(report,indent=2))
