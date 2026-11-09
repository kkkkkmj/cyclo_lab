"""Generate a separate fixed Plate / Toaster / Bread Rack corpus without simulation."""
import argparse
from collections import Counter
import copy
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import shutil

import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

import generate_base_toast_scenarios as fixed
from toast_scenario_geometry import footprint, hull, polygon_distance, rotate

shared = fixed.shared
ROOT = shared.ROOT
DEFAULT_OUTPUT = ROOT / 'scenario_delivery_base_ptb'
ORDER = ('plate', 'toaster', 'bread_shelf')
PREFIX = 'toast_base_ptb_20261109_'
VERSION = 'base_ptb_20261109_100'
SEED = 2026110901
ASSIGNMENT_SEED = 2026110902
GROUPS = shared.GROUPS
EXISTING = ('scenario_delivery', 'scenario_delivery_base')


def reference_poses(environment):
    # Reuse the six-order generator's zero-jitter PTB anchors, not sampled layouts.
    return shared.build_poses(environment, ORDER, {n: [0., 0., 0.] for n in ORDER})


def sampling_base(environment):
    reference = reference_poses(environment)
    base = dict(environment)
    base['baseline'] = {n: reference[n] for n in ORDER}
    base['baseline_bread'] = {f'bread_{i}': reference[f'bread_{i}'] for i in range(4)}
    return base


def make_poses(environment, jitter):
    return fixed.make_poses(sampling_base(environment), jitter)


def support_polygon(evidence):
    return unary_union([Polygon(p) for p in evidence['table_support']['convex_surface_polygons_xy']])


def check_layout(poses, vertices, evidence):
    """Same authored-bound criteria as the fixed-base set, with the requested PTB order."""
    polys = {n: shared.expand(footprint(vertices[n], poses[n], poses[n]['scale']), .001) for n in ORDER}
    breads = [footprint(vertices['bread'], poses[f'bread_{i}']) for i in range(4)]
    polys['bread_shelf'] = hull(polys['bread_shelf'] + [p for poly in breads for p in poly])
    support = support_polygon(evidence)
    reasons = [n + '_outside_tabletop' for n, p in polys.items() if not support.covers(Polygon(p))]
    gaps = {a + '/' + b: polygon_distance(polys[a], polys[b]) for a, b in itertools.combinations(ORDER, 2)}
    if min(gaps.values()) <= 0:
        reasons.append('object_overlap_or_contact')
    bread_gap = min(polygon_distance(a, b) for a, b in itertools.combinations(breads, 2))
    if bread_gap <= 0:
        reasons.append('bread_overlap_or_contact')
    if not all(poses[a]['position_m'][1] > poses[b]['position_m'][1] for a, b in zip(ORDER, ORDER[1:])):
        reasons.append('wrong_order')
    if poses['plate']['position_m'][0] <= .419:
        reasons.append('plate_success_x')
    return reasons, polys, dict(pair_gaps_m=gaps, minimum_bread_gap_m=bread_gap,
        tabletop_clearance_m={n: support.boundary.distance(Polygon(p)) for n, p in polys.items()},
        plate_success_x_margin_m=poses['plate']['position_m'][0] - .419,
        scope='Authored mesh/collider conservative XY bounds expanded 1 mm; no cooked PhysX or robot reachability validation')


def yaw_extrema(points, degrees=5.):
    """Exact XY extrema of vertices over continuous yaw, including interior extrema."""
    lo, hi = -math.radians(degrees), math.radians(degrees)
    bounds = []
    for u, v in ((points[:, 0], -points[:, 1]), (points[:, 1], points[:, 0])):
        values = [u * math.cos(t) + v * math.sin(t) for t in (lo, hi)]
        for k in range(-2, 3):
            t = np.arctan2(v, u) + k * math.pi
            mask = (t >= lo) & (t <= hi)
            values.append((u * np.cos(t) + v * np.sin(t))[mask])
        all_values = np.concatenate(values)
        bounds.append([float(all_values.min()), float(all_values.max())])
    return np.array(bounds).T


def variation_envelope(environment, vertices, evidence):
    """Conservative guarantee for the entire proposal box, not just sampled corners."""
    reference = reference_poses(environment)
    envelopes = {}
    for name in ORDER:
        p = reference[name]
        points = np.array([rotate(p['quaternion_wxyz'], v * p['scale']) for v in vertices[name]])
        bounds = yaw_extrema(points) + np.array(p['position_m'][:2])
        bounds += np.array([[-.021, -.021], [.021, .021]])  # 20 mm translation + 1 mm bound expansion
        if name == 'bread_shelf':
            pivot = np.array(p['position_m'])
            for i in range(4):
                b = reference[f'bread_{i}']
                relative = np.array([rotate(b['quaternion_wxyz'], v) for v in vertices['bread']])
                relative += np.array(b['position_m']) - pivot
                bb = yaw_extrema(relative) + pivot[:2] + np.array([[-.02, -.02], [.02, .02]])
                bounds[0] = np.minimum(bounds[0], bb[0]); bounds[1] = np.maximum(bounds[1], bb[1])
        envelopes[name] = bounds.tolist()
    polygons = {n: box(*b[0], *b[1]) for n, b in envelopes.items()}
    support = support_polygon(evidence)
    contained = all(support.covers(p) for p in polygons.values())
    gaps = {a + '/' + b: polygons[a].distance(polygons[b]) for a, b in itertools.combinations(ORDER, 2)}
    margins = {a + '/' + b: reference[a]['position_m'][1] - reference[b]['position_m'][1] - .04
               for a, b in zip(ORDER, ORDER[1:])}
    failures, _, checks = check_layout(reference, vertices, evidence)
    report = dict(method='Continuous yaw extrema of every authored bound vertex, including interior stationary angles; '
                  'XY translation intervals; axis-aligned envelopes include the rack and all four breads. '
                  'Containment/separation of these envelopes is conservative for the entire proposal range.',
        envelope_xy_m=envelopes, all_envelopes_inside_table=contained,
        minimum_table_clearance_m={n: support.boundary.distance(p) for n, p in polygons.items()},
        pair_gap_lower_bounds_m=gaps, origin_order_margin_lower_bounds_m=margins,
        plate_success_x_margin_lower_bound_m=reference['plate']['position_m'][0] - .02 - .419,
        reference_static_failures=failures, reference_checks=checks,
        scope='Static authored geometry only; not PhysX stability, robot reachability, or manipulation clearance')
    if failures or not contained or min(gaps.values()) <= 0 or min(margins.values()) <= 0 or report['plate_success_x_margin_lower_bound_m'] <= 0:
        raise ValueError('Reference does not provide the requested full variation clearance: ' + json.dumps(report))
    return report


def distributions(entries):
    result = shared.summaries(entries)
    result['all'] = dict(count=len(entries), type_counts=dict(Counter('>'.join(e['order_positive_to_negative_y']) for e in entries)), metrics={})
    for group, data in result.items():
        selected = [e for e in entries if group == 'all' or e['scenario_group'] == group or e['operator'] == group]
        for name in entries[0]['metrics']:
            values = np.array([e['metrics'][name] for e in selected])
            data['metrics'][name] = dict(min=float(values.min()), max=float(values.max()), mean=float(values.mean()),
                std=float(values.std()), p25=float(np.quantile(values, .25)), median=float(np.median(values)),
                p75=float(np.quantile(values, .75)), negative_count=int((values < 0).sum()),
                zero_count=int((values == 0).sum()), positive_count=int((values > 0).sum()))
    return result


def source_paths():
    # Only generation/calibration dependencies. Do not bind this corpus to unrelated local teleop edits.
    paths = [Path(__file__), Path(fixed.__file__), Path(shared.__file__)]
    paths += [ROOT / 'scripts/tools' / n for n in ('toast_scenario_geometry.py', 'build_toast_overview_cards.py',
        'toast_overview_cards_template.html', 'check_bread_slot_geometry.py', 'render_base_scenario_pngs.py')]
    paths += [shared.CFG / n for n in ('assets.py', 'bimanual_env_cfg.py', 'bimanual_mdp.py', 'toast_cycle.py', 'lever_indicator.py')]
    paths += [ROOT / 'source/cyclo_lab/cyclo_lab/assets/robots/FFW_BG2.py',
        ROOT / 'source/cyclo_lab/cyclo_lab/manager_based/manipulation/pick_place/config/ffw_bg2/pick_place_env_cfg.py']
    return paths


def generate(output=DEFAULT_OUTPUT, seed=SEED, assignment_seed=ASSIGNMENT_SEED):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be a NEW empty directory')
    environment, contract = shared.current_contract()
    vertices, assets = shared.geometry(environment)
    evidence_path = ROOT / 'scenario_delivery/inputs/geometry_evidence.json'
    historical_evidence = json.loads(evidence_path.read_text())
    # Retain the necessary authored support evidence without old diagnostic dumps or robot measurements.
    evidence = dict(table_support={k: historical_evidence['table_support'][k] for k in
        ('kind', 'status', 'top_z_m', 'convex_surface_polygons_xy', 'mesh_paths')},
        provenance=dict(source_file=str(evidence_path.relative_to(ROOT)), source_sha256=shared.sha(evidence_path)))
    preflight = variation_envelope(environment, vertices, evidence)
    previous = {name: json.loads((ROOT / name / 'manifest.json').read_text()) for name in EXISTING}
    old_ids = {e['id'] for d in previous.values() for e in d['scenarios']}
    old_signatures = {shared.signature(e['poses']) for d in previous.values() for e in d['scenarios']}
    rng = random.Random(seed); entries = []; seen = set(); rejections = Counter(); attempts = rejected = 0
    while len(entries) < 100:
        if attempts >= 100000:
            raise RuntimeError('Unable to fill the corpus without changing criteria')
        jitter = {n: [rng.uniform(-.02, .02), rng.uniform(-.02, .02), rng.uniform(-5, 5)] for n in ORDER}
        poses = make_poses(environment, jitter); attempts += 1
        failures, polygons, checks = check_layout(poses, vertices, evidence)
        signature = shared.signature(poses)
        if signature in seen or signature in old_signatures:
            failures.append('duplicate_pose')
        if failures:
            rejected += 1; rejections.update(failures); continue
        seen.add(signature)
        sid = PREFIX + f'{len(entries):03d}'
        if sid in old_ids:
            raise ValueError('ID prefix collides with an existing corpus')
        entries.append(dict(id=sid, type_index=shared.ORDERS.index(ORDER), order_positive_to_negative_y=list(ORDER),
            status='STATIC_CHECKED_NOT_GPU_VERIFIED', poses=poses, jitter=jitter, footprints_xy=polygons, checks=checks,
            pose_signature_sha256=hashlib.sha256(signature.encode()).hexdigest(),
            metrics={n + '_' + k: v for n in ORDER for k, v in zip(('dx_m', 'dy_m', 'yaw_deg'), jitter[n])}))
    allocation = fixed.allocate(entries, assignment_seed)
    config = dict(seed=seed, assignment_seed=assignment_seed, id_prefix=PREFIX, groups=GROUPS, object_order=ORDER,
        card_title='100 Toast Scenarios — Fixed Plate / Toaster / Bread Rack Order',
        reference_selection='Reuse generate_current_toast_scenarios.build_poses with PTB order and zero jitter: '
            'object X anchors (plate .49, toaster .55, rack .46) and rank Y anchors (+.4, 0, -.4). '
            'Continuous full-range authored-geometry bounds pass before sampling; no environment default is changed.',
        reference_poses=reference_poses(environment), reference_yaw_degrees={'plate': 0., 'toaster': 150., 'bread_shelf': -90.},
        baseline_semantics='manifest.baseline/baseline_bread retain environment-default calibration for loader guards; '
            'generation.reference_poses is the single PTB sampling reference, not the environment default.',
        delta_x_m=[-.02, .02], delta_y_m=[-.02, .02], delta_yaw_degrees=[-5., 5.],
        sampling='Independent uniform proposals for all nine offsets from one fixed reference; reject invalid whole configurations. '
            'Report the finite accepted distribution explicitly; rejection can condition it.',
        frame='Environment-local XY; yaw about environment +Z, left-multiplied; quaternion wxyz; metres',
        fixed='Z, roll, pitch, scale and rack-relative bread poses; no cumulative perturbations',
        mesh_bound_expansion_m=.001, extra_table_edge_margin_m=0., minimum_pair_gap_m=0., gap_comparison='strictly greater than',
        reference_variation_envelope=preflight, allocation=allocation)
    static = dict(attempts=attempts, accepted=100, rejected=rejected, rejection_reasons=dict(rejections),
        rejection_reason_counts_can_overlap=True,
        min_object_gap_m=min(min(e['checks']['pair_gaps_m'].values()) for e in entries),
        min_tabletop_clearance_m=min(min(e['checks']['tabletop_clearance_m'].values()) for e in entries),
        min_plate_success_x_margin_m=min(e['checks']['plate_success_x_margin_m'] for e in entries),
        physx='NOT_RUN', gui='NOT_RUN', vr='NOT_RUN', runtime_reset='NOT_RUN', reachability='NOT_PROVEN', rack_stability='UNRESOLVED')
    manifest = dict(schema_version=2, delivery_version=VERSION, task=environment['task'], status='STATIC_CHECKED_NOT_GPU_VERIFIED',
        assignments_file='assignments.csv', baseline=copy.deepcopy(environment['baseline']),
        baseline_bread=copy.deepcopy(environment['baseline_bread']), scales=environment['scales'], units=environment['units'],
        generation=config, environment_contract=contract, static_validation=static,
        provenance=dict(source_sha256={str(p.relative_to(ROOT)): shared.sha(p) for p in source_paths()}, asset_sha256=assets,
            existing_manifest_sha256={n + '/manifest.json': shared.sha(ROOT / n / 'manifest.json') for n in EXISTING},
            geometry_evidence_source_sha256=shared.sha(evidence_path)),
        extracted_table_support=evidence['table_support'], planning_table_envelope=environment['planning_table_envelope'], scenarios=entries)
    output.mkdir(parents=True, exist_ok=True); (output / 'inputs').mkdir()
    shared.dump(output / 'inputs/geometry_evidence.json', evidence)
    shutil.copyfile(ROOT / 'scenario_delivery/inputs/table_frame.json', output / 'inputs/table_frame.json')
    for name, data in [('manifest.json', manifest), ('generation_config.json', config), ('distribution.json', distributions(entries))]:
        shared.dump(output / name, data)
    rows = sorted(entries, key=lambda e: (e['operator'], e['operator_index']))
    with (output / 'assignments.csv').open('w', newline='') as stream:
        fields = ['operator', 'scenario_group', 'operator_index', 'group_index', 'scenario_id', 'order_positive_to_negative_y']
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for e in rows:
            writer.writerow({k: '>'.join(ORDER) if k == fields[-1] else e['id'] if k == 'scenario_id' else e[k] for k in fields})
    with (output / 'poses.csv').open('w', newline='') as stream:
        writer = csv.writer(stream); writer.writerow(['scenario_id', 'object', 'x', 'y', 'z', 'qw', 'qx', 'qy', 'qz', 'sx', 'sy', 'sz'])
        for e in entries:
            for n, p in e['poses'].items():
                writer.writerow([e['id'], n, *p['position_m'], *p['quaternion_wxyz'], *p['scale']])
    shared.write_assignments(output, entries)
    fixed.build_cards(output, output / 'inputs/table_frame.json')
    return static


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--seed', type=int, default=SEED)
    parser.add_argument('--assignment-seed', type=int, default=ASSIGNMENT_SEED)
    args = parser.parse_args()
    print(json.dumps(generate(args.output, args.seed, args.assignment_seed), indent=2))
