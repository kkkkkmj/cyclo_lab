"""CPU only: align physics evidence by control_index/substep, never preview frame id."""
import argparse,json
from pathlib import Path
import numpy as np
from replay_contact_audit import contact_metrics

def physics(path):
    with Path(path).open() as f:
        for line in f:
            r=json.loads(line)
            if r['event']=='physics':yield r

def compare(reference,actual):
    def timing(path):
        with Path(path).open() as f:
            for line in f:
                r=json.loads(line)
                if r['event']=='configuration':return r['physics_dt'],r['decimation']
        raise ValueError('Missing physics timing configuration')
    rd,rc=timing(reference);ad,ac=timing(actual)
    if abs(rd*rc-ad*ac)>1e-10 or ad>rd+1e-12 or abs(round(rd/ad)-rd/ad)>1e-9:raise ValueError('Comparison requires equal action period and equal/finer integer physics steps')
    ratio=round(rd/ad);actual_rows=iter(physics(actual))
    out=dict(pairs=0,alignment_errors=0,action_differences=0,first_q_difference_over_1e5=None,max_q_difference_rad=[0.]*4,max_parent_position_difference_m=0.,max_child_position_difference_m=[0.]*4,max_child_rotation_difference_rad=[0.]*4,reference_dt=rd,actual_dt=ad,extra_fine_samples=0)
    b=next(actual_rows,None)
    for a in physics(reference):
        desired=(a['context']['control_index'],a['substep']*ratio)
        key=lambda r:(r['context']['control_index'],r['substep'])
        while b is not None and key(b)<desired:
            out['extra_fine_samples']+=1;b=next(actual_rows,None)
        if b is None or key(b)!=desired:out['alignment_errors']+=1;continue
        out['pairs']+=1
        if not np.array_equal(np.array(a['context']['action'],np.float32),np.array(b['context']['action'],np.float32)):out['action_differences']+=1
        qa=a['direct_q']['value'];qb=b['direct_q']['value']
        if qa is None or qb is None:out['alignment_errors']+=1;continue
        delta=np.abs(np.array(qa)-qb);out['max_q_difference_rad']=np.maximum(out['max_q_difference_rad'],delta).tolist()
        if delta.max()>1e-5 and out['first_q_difference_over_1e5'] is None:out['first_q_difference_over_1e5']=dict(control_index=key(a)[0],substep=key(a)[1],delta=delta.tolist())
        pa=a['links'][0]['parent'];pb=b['links'][0]['parent']
        if pa is not None and pb is not None:out['max_parent_position_difference_m']=max(out['max_parent_position_difference_m'],float(np.linalg.norm(np.array(pa[:3])-pb[:3])))
        for i,(la,lb) in enumerate(zip(a['links'],b['links'])):
            ca=la.get('child');cb=lb.get('child')
            if ca is None or cb is None:continue
            out['max_child_position_difference_m'][i]=max(out['max_child_position_difference_m'][i],float(np.linalg.norm(np.array(ca[:3])-cb[:3])))
            qa=np.array(ca[3:]);qb=np.array(cb[3:]);angle=2*np.arccos(np.clip(abs(np.dot(qa,qb))/(np.linalg.norm(qa)*np.linalg.norm(qb)),0,1))
            out['max_child_rotation_difference_rad'][i]=max(out['max_child_rotation_difference_rad'][i],float(angle))
        b=next(actual_rows,None)
    if b is not None:out['alignment_errors']+=1+sum(1 for _ in actual_rows)
    return out

def validation_summary(directory):
    out=dict(first_tolerance_failure=None,first_numerical_difference_over_1e6=None,fields={},processed_action_max_abs=0.)
    p=Path(directory)/'state_metrics.jsonl'
    if not p.exists():return {'unavailable':'state_metrics missing'}
    for line in p.open():
        r=json.loads(line);i=r['action_index'];out['processed_action_max_abs']=max(out['processed_action_max_abs'],r['processed_action_max_abs'])
        for field,m in r['fields'].items():
            t=out['fields'].setdefault(field,dict(max_abs=None,first_tolerance_failure=None))
            if m['max_abs'] is not None:
                t['max_abs']=max(t['max_abs'] or 0,m['max_abs'])
                if m['max_abs']>1e-6 and out['first_numerical_difference_over_1e6'] is None:out['first_numerical_difference_over_1e6']=dict(action_index=i,field=field,max_abs=m['max_abs'])
            if not m['matched']:
                if t['first_tolerance_failure'] is None:t['first_tolerance_failure']=i
                if out['first_tolerance_failure'] is None:out['first_tolerance_failure']=dict(action_index=i,field=field)
    return out

def analyze(reference,baseline,candidate=None):
    b=Path(baseline);out=dict(reference=contact_metrics(reference),baseline=contact_metrics(b/'contact.jsonl'),reference_vs_baseline=compare(reference,b/'contact.jsonl'),baseline_states=validation_summary(b),warning='Full action physics replay, not state playback. Table force validity and process exit are independent. No candidate automatically accepted as a fix.')
    if candidate:
        c=Path(candidate);out.update(candidate=contact_metrics(c/'contact.jsonl'),baseline_vs_candidate=compare(b/'contact.jsonl',c/'contact.jsonl'),candidate_states=validation_summary(c))
        out['contact_preservation_not_proven']=True
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--reference-contact',required=True);p.add_argument('--baseline-dir',required=True);p.add_argument('--candidate-dir');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=analyze(a.reference_contact,a.baseline_dir,a.candidate_dir)
    with a.output.open('x') as f:json.dump(r,f,indent=2)
    print(json.dumps({k:v for k,v in r.items() if k not in ['baseline_states','candidate_states']},indent=2))
