"""Generate a new immutable 100-layout delivery for the current v2 task (CPU USD).

No scene/robot/task settings are changed. Old manifests and assignments are read-only.
"""
import argparse
import ast
from collections import Counter
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
from types import SimpleNamespace as NS
import numpy as np
from scipy.spatial import ConvexHull
from pxr import Usd, UsdGeom
from toast_scenario_geometry import hull, footprint, polygon_distance, supported, qmul, rotate, model_filter

ROOT=Path(__file__).resolve().parents[2]
CFG=ROOT/'source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2'
VERSION='v20261108_current_100'
DEFAULT_OUTPUT=ROOT/'scenario_delivery'
OBJECTS=('toaster','plate','bread_shelf')
GROUPS=('operator_A_1','operator_A_2','operator_B_1','operator_B_2')
ORDERS=list(itertools.permutations(OBJECTS))
# 24 per group plus one extra each; parent/operator splits differ by <=1 per type.
QUOTAS=np.array([[5,4,4,4],[4,4,5,4],[4,5,4,4],[4,4,4,5],[4,4,4,4],[4,4,4,4]])
SEED=20261108


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,data):Path(path).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def normalize(q):return (np.asarray(q)/np.linalg.norm(q)).tolist()
def scalar_assignments(path,names):
    scope={}
    for node in ast.parse(Path(path).read_text()).body:
        if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in names:
            exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),scope)
    return {n:scope[n] for n in names}


def current_contract():
    """Read real config literals without importing/starting Isaac Sim."""
    names=['TABLE_HEIGHT','BREAD_OFFSETS','BREAD_ROTATION','SERVING_PLATE_SCALE','SERVING_PLATE_POSITION','SERVING_BREAD_CENTER_RADIUS']
    values=scalar_assignments(CFG/'assets.py',names)
    data=json.loads((ROOT/'scenario_delivery/manifest.json').read_text())
    cfg_tree=ast.parse((CFG/'bimanual_env_cfg.py').read_text())
    positions={}
    for node in ast.walk(cfg_tree):
        if isinstance(node,ast.Assign) and len(node.targets)==1:
            target=ast.unparse(node.targets[0])
            if target in ('shelf_position','shelf_rotation'):
                positions[target]=np.array(eval(compile(ast.Expression(node.value.args[0]),'<cfg>','eval'),values),dtype=np.float32).tolist()
            if target in ('self.scene.toaster.init_state.pos','self.scene.toaster.init_state.rot'):
                positions[target]=eval(compile(ast.Expression(node.value),'<cfg>','eval'),values)
    baseline=data['baseline']
    for actual,expected in [(positions['shelf_position'],baseline['bread_shelf']['position_m']),
        (positions['shelf_rotation'],baseline['bread_shelf']['quaternion_wxyz']),
        (positions['self.scene.toaster.init_state.pos'],baseline['toaster']['position_m']),
        (positions['self.scene.toaster.init_state.rot'],baseline['toaster']['quaternion_wxyz']),
        (values['SERVING_PLATE_POSITION'],baseline['plate']['position_m'])]:
        np.testing.assert_allclose(actual,expected,atol=1e-7,rtol=0)
    shelf=baseline['bread_shelf']
    for i,offset in enumerate(values['BREAD_OFFSETS']):
        bread=data['baseline_bread'][f'bread_{i}']
        np.testing.assert_allclose(np.array(shelf['position_m'])+rotate(shelf['quaternion_wxyz'],offset),bread['position_m'],atol=1e-7,rtol=0)
        np.testing.assert_allclose(qmul(normalize(shelf['quaternion_wxyz']),values['BREAD_ROTATION']),bread['quaternion_wxyz'],atol=1e-7,rtol=0)
    robot_tree=ast.parse((ROOT/'source/cyclo_lab/cyclo_lab/assets/robots/FFW_BG2.py').read_text())
    robot=next(n.value for n in robot_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FFW_BG2_CFG' for t in n.targets))
    actuators=next(k.value for k in robot.keywords if k.arg=='actuators')
    groups=eval(compile(ast.Expression(actuators),'<actuators>','eval'),{'ImplicitActuatorCfg':lambda **kw:NS(**kw)})
    dummy=NS(scene=NS(robot=NS(actuators=groups)))
    for n in ast.walk(cfg_tree):
        if isinstance(n,ast.Assign) and len(n.targets)==1 and ast.unparse(n.targets[0]).startswith("self.scene.robot.actuators['gripper_"):
            exec(compile(ast.Module(body=[n],type_ignores=[]),'<task>','exec'),{'self':dummy})
    for name in ('gripper_master','gripper_slave'):
        assert (groups[name].stiffness,groups[name].damping)==(100.,4.)
    assert groups['gripper_master'].velocity_limit_sim==6.5
    cycle=(CFG/'toast_cycle.py').read_text();success=(CFG/'bimanual_mdp.py').read_text();led=(CFG/'lever_indicator.py').read_text()
    assert 'pressed = ratio >= .90' in cycle and 'HEATING_SECONDS = 4.0' in cycle and 'for i in range(4)' in cycle
    assert 'self.heated_bread[finished]' in cycle and 'self.heating_present[heating] &= present[heating]' in cycle
    assert '(phase == 1) | (phase == 2)' in led
    assert 'cycle.heated_bread[:, i] & bread_on_plate' in success and 'center_local' in success
    assert values['SERVING_BREAD_CENTER_RADIUS']==.020
    assert data['scales']['bread_shelf']==[1.,1.,1.]
    assert 'ASSET_DIR.parent / "bread_slot" / "rack.usda"' in (CFG/'assets.py').read_text()
    return data,dict(status='MATCHES_REQUESTED_CURRENT_SOURCE',start_press_ratio=.90,heating_seconds=4.,
        led_on_phases=[1,2],success='any same-ID fully heated bread on plate',success_center_radius_m=.020,
        master_gains=[100.,4.],slave_gains=[100.,4.],master_velocity_limit_rad_s=6.5,
        bread_offsets=values['BREAD_OFFSETS'],bread_rotation=values['BREAD_ROTATION'],
        baseline_source='manifest.json, checked against current Python literals',
        robot_distance_origin_m=[0.,0.,0.],runtime_verified=False)


def read_mesh(path):
    stage=Usd.Stage.Open(str(path));root=stage.GetDefaultPrim()
    inverse=np.linalg.inv(np.asarray(UsdGeom.Xformable(root).ComputeLocalToWorldTransform(0)))
    points=[]
    for p in Usd.PrimRange(root):
        if p.IsA(UsdGeom.Mesh):
            m=UsdGeom.Mesh(p);t=np.asarray(m.ComputeLocalToWorldTransform(0))@inverse
            points.append(np.asarray(m.GetPointsAttr().Get())@t[:3,:3]+t[3,:3])
    v=np.concatenate(points);return v[ConvexHull(v).vertices]


def geometry(base):
    assets=ROOT/'source/cyclo_lab/data/objects'
    paths={n:assets/'robodojo_make_toast'/n/'object.usdz' for n in ('toaster','plate','bread')}
    paths['bread_shelf']=assets/'bread_slot/rack.usda'
    points={n:read_mesh(p) for n,p in paths.items()}
    np.testing.assert_allclose(np.ptp(points['bread_shelf'],axis=0),[.23,.13,.045],atol=1e-7)
    # Include the current visual-only LED and authored carriage footprint in toaster bound.
    led=scalar_assignments(CFG/'lever_indicator.py',['LED_POSITION','LED_RADIUS','LED_DEPTH'])
    center=np.array(led['LED_POSITION']);half=np.array([led['LED_DEPTH']/2,led['LED_RADIUS'],led['LED_RADIUS']])
    extra=[center+np.array(sign)*half for sign in itertools.product((-1,1),repeat=3)]
    points['toaster']=np.concatenate([points['toaster'],extra])
    return points,{str(p.relative_to(ROOT)):sha(p) for p in paths.values()} | {
        'source/cyclo_lab/data/objects/bread_slot/bread_slot.usdz':sha(assets/'bread_slot/bread_slot.usdz')}


def expand(poly,r):return hull([(x+dx,y+dy) for x,y in poly for dx,dy in itertools.product((-r,r),repeat=2)])
def signature(poses):
    return json.dumps({n:[*[round(x,6) for x in p['position_m']],*[round(x,7) for x in normalize(p['quaternion_wxyz'])]] for n,p in sorted(poses.items())},sort_keys=True)


def build_poses(base,order,jitter):
    poses={};anchors={'toaster':.55,'plate':.49,'bread_shelf':.46}
    for rank,name in enumerate(order):
        ref=base['baseline'][name];dx,dy,deg=jitter[name];r=math.radians(deg)
        poses[name]=dict(position_m=[anchors[name]+dx,[.4,0.,-.4][rank]+dy,ref['position_m'][2]],
            quaternion_wxyz=normalize(qmul([math.cos(r/2),0,0,math.sin(r/2)],ref['quaternion_wxyz'])),
            scale=base['scales'].get(name,[1.,1.,1.]))
    old=base['baseline']['bread_shelf'];new=poses['bread_shelf']
    q=normalize(old['quaternion_wxyz']);delta=qmul(new['quaternion_wxyz'],[q[0],-q[1],-q[2],-q[3]])
    for i in range(4):
        b=base['baseline_bread'][f'bread_{i}']
        moved=rotate(delta,np.array(b['position_m'])-old['position_m'])
        poses[f'bread_{i}']=dict(position_m=(np.array(new['position_m'])+moved).tolist(),
            quaternion_wxyz=normalize(qmul(delta,b['quaternion_wxyz'])),scale=[1.,1.,1.])
    return poses


def validate_layout(poses,points,evidence,base):
    polygons={n:expand(footprint(points[n],poses[n],poses[n]['scale']),.001) for n in OBJECTS}
    bread_polys=[footprint(points['bread'],poses[f'bread_{i}']) for i in range(4)]
    polygons['bread_shelf']=hull(polygons['bread_shelf']+[p for poly in bread_polys for p in poly])
    failures=[]
    lo,hi=base['planning_table_envelope']
    if any(not(lo[0]+.02<=x<=hi[0]-.02 and lo[1]+.02<=y<=hi[1]-.02) for poly in polygons.values() for x,y in poly):
        failures.append('outside_planning_envelope')
    if not all(supported(expand(p,.02),evidence['table_support']['convex_surface_polygons_xy']) for p in polygons.values()):
        failures.append('outside_tabletop_20mm_margin')
    gaps={a+'/'+b:polygon_distance(polygons[a],polygons[b]) for a,b in itertools.combinations(OBJECTS,2)}
    if min(gaps.values())<.06:failures.append('object_or_approach_gap_below_60mm')
    if min(polygon_distance(a,b) for a,b in itertools.combinations(bread_polys,2))<=0:failures.append('bread_bread_overlap')
    if poses['plate']['position_m'][0]<=.419:failures.append('plate_success_x')
    model=model_filter(poses,evidence)
    if model['rejected']:failures.append('outside_robot_chain_distance_bound')
    return failures,polygons,dict(pair_gaps_m=gaps,table_margin_m=.02,model_prefilter=model,
        geometry_scope='1mm-expanded authored mesh/collider convex XY bounds; not cooked or swept contacts',
        runtime_reset='NOT_RUN',ik='NOT_RUN',robot_collision='NOT_RUN',task_success='NOT_RUN')


def features(entry,base):
    metrics={};j=entry['jitter']
    for n in OBJECTS:
        p=entry['poses'][n]['position_m'];d=np.array(p)-base['baseline'][n]['position_m']
        metrics[n+'_dx_m']=j[n][0];metrics[n+'_dy_m']=j[n][1];metrics[n+'_yaw_deg']=j[n][2]
        metrics[n+'_abs_yaw_deg']=abs(j[n][2]);metrics[n+'_jitter_xy_m']=math.hypot(*j[n][:2])
        metrics[n+'_baseline_displacement_m']=float(np.linalg.norm(d))
        metrics[n+'_robot_origin_distance_m']=float(np.linalg.norm(p))
        metrics[n+'_robot_origin_xy_distance_m']=math.hypot(*p[:2])
    distances=[min(a['distance_to_lift_segment_m'] for a in x['arms'].values()) for x in entry['checks']['model_prefilter']['probes']]
    metrics['max_probe_shoulder_distance_m']=max(distances)
    return metrics


def allocate(entries,seed):
    """Keep exact type quotas; minimize group feature means and tail imbalance."""
    rng=random.Random(seed);keys=list(entries[0]['metrics'])
    raw=np.array([[e['metrics'][k] for k in keys] for e in entries])
    standard=(raw-raw.mean(0))/np.maximum(raw.std(0),1e-9)
    tails=np.concatenate([(raw>np.quantile(raw,q,axis=0)).astype(float) for q in (.25,.5,.75)],axis=1)
    matrix=np.concatenate([standard,standard**2*.35,tails*1.5],axis=1)
    matrix-=matrix.mean(0)
    labels=np.zeros(100,dtype=int);indices=[]
    for typ in range(6):
        ids=[i for i,e in enumerate(entries) if e['type_index']==typ];indices.append(ids)
        rng.shuffle(ids);labels[ids]=np.repeat(np.arange(4),QUOTAS[typ])
    sums=np.array([matrix[labels==g].sum(0) for g in range(4)])
    score=float((sums*sums).sum());initial=score;best=score;bestlabels=labels.copy()
    for step in range(50000):
        a,b=rng.sample(indices[rng.randrange(6)],2);ga,gb=labels[a],labels[b]
        if ga==gb:continue
        delta=matrix[b]-matrix[a]
        change=2*float(((sums[ga]-sums[gb])*delta).sum()+(delta*delta).sum())
        temp=max(.01,2.*(1-step/50000))
        if change<0 or rng.random()<math.exp(-min(change/temp,700)):
            sums[ga]+=delta;sums[gb]-=delta;labels[a],labels[b]=gb,ga;score+=change
            if score<best:best=score;bestlabels=labels.copy()
    for g,group in enumerate(GROUPS):
        batches=[]
        for typ in range(6):
            ids=[i for i in indices[typ] if bestlabels[i]==g];rng.shuffle(ids);batches.append(ids)
        ordered=[]
        while any(batches):
            types=list(range(6));rng.shuffle(types)
            for typ in types:
                if batches[typ]:ordered.append(batches[typ].pop())
        assert len(ordered)==25
        for index,i in enumerate(ordered,1):
            entries[i].update(operator=group.rsplit('_',1)[0],scenario_group=group,group_index=index,
                              operator_index=index+(25 if group.endswith('_2') else 0))
    return dict(method='fixed per-type quotas + seeded within-type swaps of group labels',iterations=50000,
        assignment_seed=seed,objective='standardized signed offsets, magnitudes, distances, second moments and quartile occupancy',
        initial_score=initial,final_score=best,difficulty_equivalence='NOT_PROVEN',feature_names=keys)


def summaries(entries):
    summary={}
    for group in (*GROUPS,'operator_A','operator_B'):
        selected=[e for e in entries if e['scenario_group']==group or e['operator']==group]
        summary[group]=dict(count=len(selected),type_counts=dict(Counter('>'.join(e['order_positive_to_negative_y']) for e in selected)),metrics={})
        for name in entries[0]['metrics']:
            a=np.array([e['metrics'][name] for e in selected]);summary[group]['metrics'][name]=dict(
                min=float(a.min()),max=float(a.max()),mean=float(a.mean()),std=float(a.std()),
                p25=float(np.quantile(a,.25)),median=float(np.median(a)),p75=float(np.quantile(a,.75)))
    return summary


def write_assignments(path,entries):
    lines=['# Assignments for All 100 Scenarios','', '| operator | Group | Operator index | Group index | scenario ID | +Y → −Y order |',
           '|---|---|---:|---:|---|---|']
    for e in sorted(entries,key=lambda s:(s['scenario_group'],s['group_index'])):
        lines.append(f"| {e['operator']} | {e['scenario_group']} | {e['operator_index']} | {e['group_index']} | {e['id']} | {' > '.join(e['order_positive_to_negative_y'])} |")
    (path/'ASSIGNMENTS.md').write_text('\n'.join(lines)+'\n')


def generate(output,evidence_path,seed=SEED):
    output=Path(output)
    targets=['manifest.json','assignments.csv','generation_config.json','validation.json','distribution.json','poses.csv','ASSIGNMENTS.md']
    if any((output/f).exists() for f in targets):raise ValueError('Delivery exists; choose a NEW output directory')
    base,contract=current_contract();points,asset_hashes=geometry(base)
    evidence=json.loads(Path(evidence_path).read_text())
    robot=ROOT/'source/cyclo_lab/data/robots/FFW/FFW_BG2_without_mimic.usd'
    assert sha(robot)==evidence['robot_usd_sha256'] and evidence['robot_model']['fk_validated']
    history=json.loads((DEFAULT_OUTPUT/'inputs/generation_history.json').read_text())
    old_signatures=set(history['previous_pose_sha256'])
    rng=random.Random(seed);entries=[];rejections=Counter();seen=set();attempts=0
    # Latin hypercube candidates within each type; rejected candidates are replaced.
    for typ,order in enumerate(ORDERS):
        count=int(QUOTAS[typ].sum());accepted=0;pool=[]
        while accepted<count:
            if attempts>50000:raise RuntimeError('Cannot fill quotas without relaxing criteria')
            if not pool:
                columns=[]
                for dim in range(9):
                    col=[(i+rng.random())/count*2-1 for i in range(count)];rng.shuffle(col);columns.append(col)
                pool=list(zip(*columns))
            factors=pool.pop();jitter={}
            for i,n in enumerate(OBJECTS):jitter[n]=[factors[3*i]*(.01 if n=='plate' else .015),factors[3*i+1]*.015,factors[3*i+2]*5]
            poses=build_poses(base,order,jitter);attempts+=1
            failures,polys,checks=validate_layout(poses,points,evidence,base)
            sig=signature(poses)
            if sig in seen or hashlib.sha256(sig.encode()).hexdigest() in old_signatures:failures.append('duplicate_current_or_previous_pose')
            if failures:rejections.update(failures);continue
            seen.add(sig);entry=dict(id=f'toast_v20261108_{len(entries):03d}',type_index=typ,
                order_positive_to_negative_y=list(order),status='STATIC_CHECKED_NOT_GPU_VERIFIED',
                poses=poses,jitter=jitter,footprints_xy=polys,checks=checks,pose_signature_sha256=hashlib.sha256(sig.encode()).hexdigest())
            entry['metrics']=features(entry,base);entries.append(entry);accepted+=1
    allocation=allocate(entries,seed+1);distribution=summaries(entries)
    config=dict(seed=seed,assignment_seed=seed+1,sampling='per-type Latin hypercube, rejection sampling',
        object_orders=ORDERS,quotas_by_type_and_group=QUOTAS.tolist(),groups=GROUPS,
        x_anchors_m={'toaster':.55,'plate':.49,'bread_shelf':.46},y_anchors_m=[.4,0.,-.4],
        x_jitter_m={'toaster':.015,'plate':.010,'bread_shelf':.015},y_jitter_m=.015,yaw_jitter_degrees=5.,
        table_margin_m=.02,mesh_bound_margin_m=.001,minimum_collision_gap_m=.03,minimum_approach_gap_m=.06,
        range_adjustment='None: native rack passes existing ranges with full margins',allocation=allocation)
    sourcefiles=[CFG/n for n in ['assets.py','bread_geometry.py','bimanual_env_cfg.py','bimanual_env.py','bimanual_mdp.py','mdp.py','toast_cycle.py','lever_indicator.py','scene.py','scenarios.py']]
    sourcefiles += [Path(__file__),ROOT/'scripts/tools/toast_scenario_geometry.py',ROOT/'scripts/tools/view_make_toast_scenario.py',ROOT/'scripts/quest_diagnostic/teleop_toast.py',ROOT/'scripts/tools/toast_recording_metadata.py',ROOT/'source/cyclo_lab/cyclo_lab/assets/robots/FFW_BG2.py']
    manifest=dict(schema_version=2,delivery_version=VERSION,task=base['task'],status='STATIC_CHECKED_NOT_GPU_VERIFIED',
        assignments_file='assignments.csv',baseline=base['baseline'],baseline_bread=base['baseline_bread'],scales=base['scales'],
        units=base['units'],generation=config,environment_contract=contract,
        provenance=dict(source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sourcefiles},asset_sha256=asset_hashes,
            robot_usd_sha256=sha(robot),evidence_sha256=sha(evidence_path),
            **history['source_sha256'],
            remote_reference='https://github.com/kkkkkmj/cyclo_lab/tree/toast-scenarios-100/scenario_delivery',
            remote_identity_verified=False,remote_access='GitHub and raw fetch failed (cache miss); local snapshots used'),
        extracted_table_support=evidence['table_support'],planning_table_envelope=base['planning_table_envelope'],scenarios=entries)
    validation=dict(count=len(entries),unique_ids=len({e['id'] for e in entries}),unique_poses=len(seen),
        duplicate_previous_pose_count=len({hashlib.sha256(sig.encode()).hexdigest() for sig in seen}&old_signatures),attempts=attempts,rejections=dict(rejections),
        counts={g:distribution[g]['count'] for g in distribution},
        min_object_gap_m=min(min(e['checks']['pair_gaps_m'].values()) for e in entries),
        runtime_reset='NOT_RUN',physx='NOT_RUN',ik='NOT_RUN',manipulation='NOT_RUN',reachability='NOT_PROVEN')
    output.mkdir(parents=True,exist_ok=True)
    for name,value in [('manifest.json',manifest),('generation_config.json',config),('validation.json',validation),('distribution.json',distribution)]:dump(output/name,value)
    rows=sorted(entries,key=lambda s:(s['operator'],s['operator_index']))
    fields=['operator','scenario_group','operator_index','group_index','scenario_id','order_positive_to_negative_y']
    with (output/'assignments.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for e in rows:writer.writerow({k:('>'.join(e[k]) if k=='order_positive_to_negative_y' else e['id'] if k=='scenario_id' else e[k]) for k in fields})
    with (output/'poses.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['scenario_id','object','x','y','z','qw','qx','qy','qz','sx','sy','sz'])
        for e in entries:
            for n,p in e['poses'].items():writer.writerow([e['id'],n,*p['position_m'],*p['quaternion_wxyz'],*p['scale']])
    write_assignments(output,entries)
    return validation

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--seed',type=int,default=SEED)
    parser.add_argument('--evidence',type=Path,default=DEFAULT_OUTPUT/'inputs/geometry_evidence.json')
    args=parser.parse_args();print(json.dumps(generate(args.output,args.evidence,args.seed),indent=2))
