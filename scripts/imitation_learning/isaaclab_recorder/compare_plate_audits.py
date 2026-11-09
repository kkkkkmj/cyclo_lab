"""Compare read-only record/replay evidence; does not replace full state validation."""
import argparse
import json
from pathlib import Path
import numpy as np


def differences(a,b,path=''):
    if isinstance(a,dict) and isinstance(b,dict):
        return [d for k in sorted(set(a)|set(b)) for d in
                (differences(a[k],b[k],path+'/'+k) if k in a and k in b else [dict(path=path+'/'+k,error='missing key')])]
    return [] if a==b else [dict(path=path,record=a,replay=b)]


def compare(record_file,replay_file,episode):
    def load(path):return [r for r in map(json.loads,Path(path).read_text().splitlines()) if r.get('episode')==episode]
    record,replay=load(record_file),load(replay_file)
    if not record or not replay:raise ValueError(f'Evidence missing for {episode}')
    report=dict(episode=episode,checkpoints={},note='Does not prove full physics replay; missing/unavailable runtime values remain unknown.')
    stages=[('after_reset_before_physics','after_reset_to_before_physics'),('after_first_physics_step','after_first_physics_step'),('after_first_control_step','after_first_control_step')]
    for a,b in stages:
        left=next((r for r in record if r.get('stage')==a),None)
        right=next((r for r in replay if r.get('stage')==b),None)
        if left is None or right is None:report['checkpoints'][a]={'status':'missing'};continue
        x=np.asarray(left['physx_com_velocity_world']);y=np.asarray(right['physx_com_velocity_world'])
        if x.shape!=(6,) or y.shape!=(6,) or not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError('Invalid velocity evidence')
        report['checkpoints'][a]=dict(record=x.tolist(),replay=y.tolist(),component_abs_error=abs(x-y).tolist(),max_abs=float(abs(x-y).max()))
    def properties(rows):
        r=next((r for r in rows if r['kind']=='runtime_physics'),None)
        return {k:v for k,v in r.items() if k not in ('wall_monotonic','kind','episode')} if r else None
    a,b=properties(record),properties(replay)
    report['property_differences']=differences(a,b) if a is not None and b is not None else 'missing snapshot'
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record_audit');parser.add_argument('replay_audit');parser.add_argument('--episode',default='demo_0')
    args=parser.parse_args();print(json.dumps(compare(args.record_audit,args.replay_audit,args.episode),indent=2))
