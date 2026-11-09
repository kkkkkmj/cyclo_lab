"""Generate 100 fixed-order layouts from one current environment baseline, without simulation."""
import argparse
from collections import Counter
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import shutil

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

import generate_current_toast_scenarios as shared
from toast_scenario_geometry import footprint, hull, polygon_distance, qmul, rotate
from build_toast_overview_cards import build as build_cards

ROOT = shared.ROOT
DEFAULT_OUTPUT = ROOT / 'scenario_delivery_base'
SEED = 20261109
ASSIGNMENT_SEED = 20261110
PREFIX = 'toast_base_20261109_'
ORDER = ('toaster', 'plate', 'bread_shelf')
GROUPS = shared.GROUPS


def reference_poses(base):
    return {n: dict(p, scale=base['scales'].get(n, [1., 1., 1.]))
            for n, p in {**base['baseline'], **base['baseline_bread']}.items()}


def make_poses(base, jitter):
    """Always transform the fixed baseline, never the previous sample."""
    poses = reference_poses(base)
    for name in ORDER:
        ref = base['baseline'][name]
        dx, dy, degrees = jitter[name]
        radians = math.radians(degrees)
        poses[name] = dict(position_m=[ref['position_m'][0]+dx, ref['position_m'][1]+dy, ref['position_m'][2]],
            quaternion_wxyz=shared.normalize(qmul([math.cos(radians/2), 0, 0, math.sin(radians/2)], ref['quaternion_wxyz'])),
            scale=base['scales'].get(name, [1., 1., 1.]))
    old = base['baseline']['bread_shelf']; new = poses['bread_shelf']
    q = shared.normalize(old['quaternion_wxyz'])
    delta = qmul(new['quaternion_wxyz'], [q[0], -q[1], -q[2], -q[3]])
    for i in range(4):
        ref = base['baseline_bread'][f'bread_{i}']
        offset = rotate(delta, np.array(ref['position_m'])-old['position_m'])
        poses[f'bread_{i}'] = dict(position_m=(np.array(new['position_m'])+offset).tolist(),
            quaternion_wxyz=shared.normalize(qmul(delta, ref['quaternion_wxyz'])), scale=[1.,1.,1.])
    return poses


def check_layout(poses, vertices, evidence):
    """Full conservative footprint containment and no overlap; no reachability claim.

    This set does not request the six-order corpus's extra 20 mm edge/60 mm approach buffers.
    Keep 1 mm mesh-bound expansion. Do not alter any task/physics tolerance.
    """
    polys = {n: shared.expand(footprint(vertices[n], poses[n], poses[n]['scale']), .001) for n in ORDER}
    breads = [footprint(vertices['bread'], poses[f'bread_{i}']) for i in range(4)]
    polys['bread_shelf'] = hull(polys['bread_shelf']+[p for poly in breads for p in poly])
    support = unary_union([Polygon(p) for p in evidence['table_support']['convex_surface_polygons_xy']])
    reasons = []
    for name, poly in polys.items():
        if not support.covers(Polygon(poly)):
            reasons.append(name+'_outside_tabletop')
    gaps = {a+'/'+b: polygon_distance(polys[a], polys[b]) for a,b in itertools.combinations(ORDER,2)}
    if min(gaps.values()) <= 0: reasons.append('object_overlap_or_contact')
    if min(polygon_distance(a,b) for a,b in itertools.combinations(breads,2)) <= 0: reasons.append('bread_overlap_or_contact')
    if not poses['toaster']['position_m'][1] > poses['plate']['position_m'][1] > poses['bread_shelf']['position_m'][1]:
        reasons.append('wrong_order')
    # Existing serving predicate uses strict environment-relative X > .419, unchanged.
    if poses['plate']['position_m'][0] <= .419: reasons.append('plate_success_x')
    return reasons, polys, dict(pair_gaps_m=gaps,
        tabletop_clearance_m={n: support.boundary.distance(Polygon(p)) for n,p in polys.items()},
        plate_success_x_margin_m=poses['plate']['position_m'][0]-.419,
        scope='Authored mesh/collider conservative XY bounds expanded 1 mm; no cooked PhysX or robot reachability validation')


def allocate(entries, seed):
    """Balance variations by quota-preserving swaps; never modify sampled poses."""
    rng=random.Random(seed)
    names=list(entries[0]['metrics'])
    raw=np.array([[e['metrics'][n] for n in names] for e in entries])
    z=(raw-raw.mean(0))/np.maximum(raw.std(0),1e-9)
    tails=np.concatenate([(raw>np.quantile(raw,q,axis=0)).astype(float) for q in (.25,.5,.75)],axis=1)
    features=np.concatenate([z,.35*z*z,1.5*tails],axis=1);features-=features.mean(0)
    ids=list(range(100));rng.shuffle(ids);labels=np.empty(100,dtype=int)
    for g in range(4):labels[ids[g*25:(g+1)*25]]=g
    sums=np.array([features[labels==g].sum(0) for g in range(4)])
    score=float((sums*sums).sum());initial=best=score;bestlabels=labels.copy()
    for step in range(50000):
        a,b=rng.sample(range(100),2);ga,gb=labels[a],labels[b]
        if ga==gb:continue
        delta=features[b]-features[a]
        change=2*float(((sums[ga]-sums[gb])*delta).sum()+(delta*delta).sum())
        temp=max(.01,2*(1-step/50000))
        if change<0 or rng.random()<math.exp(-min(change/temp,700)):
            sums[ga]+=delta;sums[gb]-=delta;labels[a],labels[b]=gb,ga;score+=change
            if score<best:best=score;bestlabels=labels.copy()
    for g,group in enumerate(GROUPS):
        indices=[i for i in range(100) if bestlabels[i]==g];rng.shuffle(indices)
        for index,i in enumerate(indices,1):
            entries[i].update(operator=group.rsplit('_',1)[0],scenario_group=group,group_index=index,
                              operator_index=index+(25 if group.endswith('_2') else 0))
    return dict(assignment_seed=seed,iterations=50000,initial_score=initial,final_score=best,
        method='Seeded 25-per-group allocation; within-set label swaps balance standardized signed deltas, second moments (0.35) and quartile occupancy (1.5)',
        feature_names=names,difficulty_equivalence='NOT_PROVEN')


def generate(output=DEFAULT_OUTPUT, seed=SEED, assignment_seed=ASSIGNMENT_SEED):
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError('Output must be a NEW empty directory')
    base,contract=shared.current_contract()
    assert base['baseline']['toaster']['position_m'][1]>base['baseline']['plate']['position_m'][1]>base['baseline']['bread_shelf']['position_m'][1]
    vertices,assets=shared.geometry(base)
    evidence_path=ROOT/'scenario_delivery/inputs/geometry_evidence.json'
    evidence=json.loads(evidence_path.read_text())
    reference=reference_poses(base)
    rng=random.Random(seed);entries=[];seen=set();rejections=Counter();attempts=0;rejected=0
    old_signatures={shared.signature(e['poses']) for e in base['scenarios']}
    while len(entries)<100:
        if attempts>=100000:raise RuntimeError('Unable to obtain valid layouts without changing criteria')
        jitter={n:[rng.uniform(-.02,.02),rng.uniform(-.02,.02),rng.uniform(-5,5)] for n in ORDER}
        poses=make_poses(base,jitter);attempts+=1
        failures,polys,checks=check_layout(poses,vertices,evidence)
        sig=shared.signature(poses)
        if sig in seen or sig in old_signatures:failures.append('duplicate_pose')
        if failures:rejected+=1;rejections.update(failures);continue
        seen.add(sig)
        entries.append(dict(id=PREFIX+f'{len(entries):03d}',type_index=0,order_positive_to_negative_y=list(ORDER),
            status='STATIC_CHECKED_NOT_GPU_VERIFIED',poses=poses,jitter=jitter,footprints_xy=polys,checks=checks,
            pose_signature_sha256=hashlib.sha256(sig.encode()).hexdigest(),
            metrics={n+'_'+k:v for n in ORDER for k,v in zip(('dx_m','dy_m','yaw_deg'),jitter[n])}))
    allocation=allocate(entries,assignment_seed)
    baseline_failures,_,_=check_layout(reference,vertices,evidence)
    config=dict(seed=seed,assignment_seed=assignment_seed,groups=GROUPS,object_order=ORDER,
        card_title='100 Toast Scenarios — Fixed Toaster / Plate / Bread Rack Order',
        reference_selection='Current environment default already has T>P>S; use it unchanged as the sole reference, not any existing scenario',
        reference_poses=reference,reference_yaw_degrees={'toaster':150.,'plate':0.,'bread_shelf':-90.},
        delta_x_m=[-.02,.02],delta_y_m=[-.02,.02],delta_yaw_degrees=[-5.,5.],
        sampling='Independent uniform proposals for all 9 deltas; reject invalid full configurations. Accepted distribution is conditional, not uniformly distributed after rejection.',
        frame='Environment-local XY; yaw about environment +Z, left-multiplied; quaternion wxyz; metres',
        fixed='Z, roll, pitch, scale and rack-relative bread poses; no cumulative perturbations',
        mesh_bound_expansion_m=.001,extra_table_edge_margin_m=0.,minimum_pair_gap_m=0.,gap_comparison='strictly greater than',
        baseline_static_failures=baseline_failures,allocation=allocation)
    static=dict(attempts=attempts,accepted=100,rejected=rejected,rejection_reasons=dict(rejections),
        min_object_gap_m=min(min(e['checks']['pair_gaps_m'].values()) for e in entries),
        min_tabletop_clearance_m=min(min(e['checks']['tabletop_clearance_m'].values()) for e in entries),
        min_plate_success_x_margin_m=min(e['checks']['plate_success_x_margin_m'] for e in entries),
        physx='NOT_RUN',gui='NOT_RUN',vr='NOT_RUN',reachability='NOT_PROVEN',rack_stability='UNRESOLVED')
    sources=[Path(__file__),ROOT/'scripts/tools/generate_current_toast_scenarios.py',ROOT/'scripts/tools/build_toast_overview_cards.py',ROOT/'scripts/tools/toast_overview_cards_template.html',ROOT/'scripts/tools/toast_scenario_geometry.py']
    sources += [ROOT/p for p in base['provenance']['source_sha256'] if (ROOT/p) not in sources]
    manifest=dict(schema_version=2,delivery_version='base_20261109_100',task=base['task'],status='STATIC_CHECKED_NOT_GPU_VERIFIED',
        assignments_file='assignments.csv',baseline=base['baseline'],baseline_bread=base['baseline_bread'],scales=base['scales'],units=base['units'],
        generation=config,environment_contract=contract,static_validation=static,
        provenance=dict(source_sha256={str(p.relative_to(ROOT)):shared.sha(p) for p in sources},asset_sha256=assets,
                        existing_manifest_sha256=shared.sha(ROOT/'scenario_delivery/manifest.json'),geometry_evidence_sha256=shared.sha(evidence_path)),
        extracted_table_support=evidence['table_support'],planning_table_envelope=base['planning_table_envelope'],scenarios=entries)
    output.mkdir(parents=True,exist_ok=True);(output/'inputs').mkdir()
    for name in ('geometry_evidence.json','table_frame.json'):
        shutil.copyfile(ROOT/'scenario_delivery/inputs'/name,output/'inputs'/name)
    for name,value in [('manifest.json',manifest),('generation_config.json',config),('distribution.json',shared.summaries(entries))]:shared.dump(output/name,value)
    rows=sorted(entries,key=lambda e:(e['operator'],e['operator_index']))
    with (output/'assignments.csv').open('w',newline='') as stream:
        fields=['operator','scenario_group','operator_index','group_index','scenario_id','order_positive_to_negative_y']
        w=csv.DictWriter(stream,fieldnames=fields);w.writeheader()
        for e in rows:w.writerow({k:'>'.join(ORDER) if k=='order_positive_to_negative_y' else e['id'] if k=='scenario_id' else e[k] for k in fields})
    with (output/'poses.csv').open('w',newline='') as stream:
        w=csv.writer(stream);w.writerow(['scenario_id','object','x','y','z','qw','qx','qy','qz','sx','sy','sz'])
        for e in entries:
            for n,p in e['poses'].items():w.writerow([e['id'],n,*p['position_m'],*p['quaternion_wxyz'],*p['scale']])
    shared.write_assignments(output,entries)
    build_cards(output,output/'inputs/table_frame.json')
    return static


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--seed',type=int,default=SEED)
    parser.add_argument('--assignment-seed',type=int,default=ASSIGNMENT_SEED)
    args=parser.parse_args()
    print(json.dumps(generate(args.output,args.seed,args.assignment_seed),indent=2))
