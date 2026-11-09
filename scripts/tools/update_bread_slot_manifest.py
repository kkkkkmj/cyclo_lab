"""Derive rack-specific bread poses without resampling IDs, operators or objects."""
import json
import hashlib
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def qmul(a,b):
    w,x,y,z=a;v,i,j,k=b
    return (w*v-x*i-y*j-z*k,w*i+x*v+y*k-z*j,w*j-x*k+y*v+z*i,w*k+x*j-y*i+z*v)

def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Historical input manifest')
    parser.add_argument('--output', type=Path, required=True, help='New output outside the active delivery')
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve().is_relative_to(ROOT/'scenario_delivery'):
        parser.error('Choose a new output outside scenario_delivery')
    source = args.source
    data = json.loads(source.read_text())
    data['rack_asset'] = 'source/cyclo_lab/data/objects/bread_slot/rack.usda'
    data['rack_pose_source'] = 'manifest.json (IDs, assignments and object transforms unchanged)'
    data['status'] = 'BREAD_SLOT_GEOMETRY_CHECKED_NOT_GPU_VERIFIED'
    data['evidence_note'] = 'Inherited generation/provenance describe the original rack. New rack physics and robot access remain unverified.'
    data['scales']['bread_shelf'] = [1.,1.,1.]
    def bread(shelf,i):
        q=shelf['quaternion_wxyz'];q=tuple(v/math.sqrt(sum(x*x for x in q)) for v in q)
        offset=((.09,.03,-.03,-.09)[i]-.005607555,.000249905,.0885 + .994051338865205 - 1.0382)
        moved=qmul(qmul(q,(0,*offset)),(q[0],-q[1],-q[2],-q[3]))[1:]
        return dict(position_m=[a+b for a,b in zip(shelf['position_m'],moved)],
                    quaternion_wxyz=list(qmul(q,(math.sqrt(.5),0,math.sqrt(.5),0))),scale=[1.,1.,1.])
    for i in range(4):data['baseline_bread'][f'bread_{i}']=bread(data['baseline']['bread_shelf'],i)
    for entry in data['scenarios']:
        entry['legacy_rack_evidence'] = {k:entry.pop(k) for k in
            ('footprints_xy','checks','pose_signature_sha256','status') if k in entry}
        entry['status'] = 'BREAD_SLOT_NOT_GPU_VERIFIED'
        entry['checks'] = {'runtime_layout_reset':'NOT_TESTED', 'task_success':'NOT_TESTED',
                           'access_swept_volume':'NOT_TESTED', 'reachability':'NOT_PROVEN'}
        entry['poses']['bread_shelf']['scale']=[1.,1.,1.]
        for i in range(4):entry['poses'][f'bread_{i}']=bread(entry['poses']['bread_shelf'],i)
        entry['pose_signature_sha256'] = hashlib.sha256(json.dumps(entry['poses'],sort_keys=True).encode()).hexdigest()
    args.output.write_text(json.dumps(data,indent=2)+'\n')

if __name__=='__main__':main()
