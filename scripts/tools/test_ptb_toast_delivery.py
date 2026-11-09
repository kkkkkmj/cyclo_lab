"""CPU contracts for PTB data, reset I/O, recording provenance and schematic images.

No PhysX, GUI, headset or robot trajectory is executed by these tests.
"""
import ast
from collections import Counter
import contextlib
import csv
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation
from shapely.geometry import MultiPoint, Polygon, box
import torch

import generate_ptb_toast_scenarios as gen
import build_toast_overview_cards as cards
import render_base_scenario_pngs as png
import test_base_toast_delivery as previous_tests
import test_toast_serving_success as serving
from test_toast_scenario_runtime import m as loader, fixture
from view_make_toast_scenario import build_parser, resolve_selection
from toast_recording_metadata import create_diagnostic, scenario_for_replay, applied_reset_poses, TASK

DELIVERY = gen.DEFAULT_OUTPUT
MANIFEST = DELIVERY / 'manifest.json'


class PTBDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = loader.load_manifest(MANIFEST)
        cls.entries = cls.data['scenarios']
        cls.environment, _ = gen.shared.current_contract()
        cls.vertices, _ = gen.shared.geometry(cls.environment)
        cls.evidence = json.loads((DELIVERY / 'inputs/geometry_evidence.json').read_text())

    def test_ids_quotas_reference_and_independent_offsets(self):
        ids = {e['id'] for e in self.entries}
        self.assertEqual(ids, {gen.PREFIX + f'{i:03d}' for i in range(100)})
        for name in gen.EXISTING:
            old = loader.load_manifest(gen.ROOT / name / 'manifest.json')
            self.assertFalse(ids & {e['id'] for e in old['scenarios']})
            self.assertFalse({gen.shared.signature(e['poses']) for e in self.entries} &
                             {gen.shared.signature(e['poses']) for e in old['scenarios']})
        self.assertEqual(len({gen.shared.signature(e['poses']) for e in self.entries}), 100)
        self.assertEqual(Counter(e['scenario_group'] for e in self.entries), {g: 25 for g in gen.GROUPS})
        self.assertEqual(Counter(e['operator'] for e in self.entries), {'operator_A': 50, 'operator_B': 50})
        # Loader calibration must remain the real environment default, not the new sampling reference.
        for key in ('baseline', 'baseline_bread', 'scales'):
            self.assertEqual(self.data[key], self.environment[key])
        reference = self.data['generation']['reference_poses']
        self.assertEqual(reference, gen.reference_poses(self.environment))
        self.assertEqual(json.loads((DELIVERY / 'generation_config.json').read_text()), self.data['generation'])
        for g in gen.GROUPS:
            entries = [e for e in self.entries if e['scenario_group'] == g]
            self.assertEqual(sorted(e['group_index'] for e in entries), list(range(1, 26)))
            self.assertEqual(sorted(e['operator_index'] for e in entries), list(range(26, 51) if g.endswith('_2') else range(1, 26)))
        for e in self.entries:
            self.assertEqual(e['poses'], gen.make_poses(self.environment, e['jitter']))
            self.assertEqual(e['order_positive_to_negative_y'], list(gen.ORDER))
            self.assertTrue(all(e['poses'][a]['position_m'][1] > e['poses'][b]['position_m'][1]
                                for a, b in zip(gen.ORDER, gen.ORDER[1:])))
            for n, (dx, dy, yaw) in e['jitter'].items():
                self.assertLessEqual(abs(dx), .02); self.assertLessEqual(abs(dy), .02); self.assertLessEqual(abs(yaw), 5)
                p, r = e['poses'][n], reference[n]
                np.testing.assert_allclose(np.array(p['position_m']) - r['position_m'], [dx, dy, 0], atol=1e-15)
                q = Rotation.from_quat(np.array(p['quaternion_wxyz'])[[1, 2, 3, 0]])
                rq = Rotation.from_quat(np.array(r['quaternion_wxyz'])[[1, 2, 3, 0]])
                np.testing.assert_allclose((q * rq.inv()).as_rotvec(), [0, 0, np.deg2rad(yaw)], atol=1e-14)
                self.assertEqual(p['scale'], r['scale'])

    def test_static_geometry_and_continuous_variation_envelope(self):
        report = gen.variation_envelope(self.environment, self.vertices, self.evidence)
        self.assertEqual(report, self.data['generation']['reference_variation_envelope'])
        support = gen.support_polygon(self.evidence)
        for bounds in report['envelope_xy_m'].values():
            self.assertTrue(support.covers(box(*bounds[0], *bounds[1])))
        # The maximum X is at the interior angle 0, not either interval endpoint.
        extent = gen.yaw_extrema(np.array([[1., 0., 0.]]))
        np.testing.assert_allclose(extent, [[np.cos(np.deg2rad(5)), -np.sin(np.deg2rad(5))],
                                          [1., np.sin(np.deg2rad(5))]], atol=1e-15)
        for e in self.entries:
            reasons, polygons, checks = gen.check_layout(e['poses'], self.vertices, self.evidence)
            self.assertFalse(reasons, (e['id'], reasons)); self.assertEqual(checks, e['checks'])
            for name, poly in polygons.items():
                bounds = report['envelope_xy_m'][name]
                self.assertTrue(box(*bounds[0], *bounds[1]).covers(Polygon(poly)), (e['id'], name))
        validation = self.data['static_validation']
        self.assertEqual(validation['attempts'], 100 + validation['rejected'])
        self.assertEqual((validation['attempts'], validation['rejected'], validation['rejection_reasons']), (100, 0, {}))
        distribution = json.loads((DELIVERY / 'distribution.json').read_text())
        self.assertEqual(distribution, gen.distributions(self.entries))
        # Explicitly check both signs rather than describing a finite sample as perfectly uniform.
        self.assertEqual(distribution['all']['metrics']['plate_dx_m']['negative_count'], 49)
        self.assertEqual(distribution['all']['metrics']['plate_dx_m']['positive_count'], 51)

    def test_selection_reset_and_rack_relative_bread_for_every_id(self):
        node = next(n for n in ast.parse((gen.shared.CFG / 'bimanual_mdp.py').read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name == 'reset_objects')
        scope = {'torch': torch}
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'bimanual_mdp.py', 'exec'), scope)

        class Scene(dict):
            env_origins = torch.tensor([[2., 3., 0.]])

        class Body:
            def __init__(self, state):
                default = torch.tensor([[*state.pos, *state.rot, 0., 0., 0., 0., 0., 0.]])
                self.data = NS(default_root_state=default, root_state_w=torch.full((1, 13), 999.),
                               default_joint_pos=torch.zeros(1, 2))
            def write_root_state_to_sim(self, state, env_ids): self.data.root_state_w = state.clone()
            def write_joint_state_to_sim(self, pos, vel, env_ids): self.joints = pos.clone()
            def set_joint_position_target(self, pos, env_ids): self.targets = pos.clone()

        for e in self.entries:
            for mode in (['--scenario_group', e['scenario_group'], '--group_index', str(e['group_index'])],
                         ['--operator', e['operator'], '--scenario_index', str(e['operator_index'])]):
                args = build_parser().parse_args(['--scenario_manifest', str(MANIFEST), *mode])
                self.assertEqual(resolve_selection(args), e['id'])
                self.assertEqual((args.operator, args.scenario_index), (e['operator'], e['operator_index']))
            cfg = fixture(self.environment); cfg.scenario_manifest = str(MANIFEST)
            loader.apply_scenario(cfg, e['id'])  # validates all four original rack-relative poses before mutation
            scene = Scene()
            for n, p in e['poses'].items():
                state = getattr(cfg.scene, n).init_state
                self.assertEqual(tuple(p['position_m']), state.pos)
                self.assertEqual(tuple(p['quaternion_wxyz']), state.rot)
                scene[n] = Body(state)
            rack = cfg.scene.bread_shelf.init_state
            scene['bread_shelf'].get_world_poses = lambda: (torch.tensor([rack.pos]) + scene.env_origins, torch.tensor([rack.rot]))
            env = NS(cfg=cfg, scene=scene, num_envs=1, device='cpu')
            scope['reset_objects'](env, None)  # real reset function, mocked simulator write API
            with contextlib.redirect_stdout(io.StringIO()):
                measured = applied_reset_poses(env, MANIFEST, e['id'])
            self.assertEqual(set(measured), set(e['poses']))
            self.assertTrue(torch.equal(scene['toaster'].joints, scene['toaster'].targets))
            for old in gen.EXISTING:
                with self.assertRaises(ValueError): loader.get_scenario(e['id'], gen.ROOT / old / 'manifest.json')
        self.assertEqual(loader.MANIFEST, gen.ROOT / 'scenario_delivery/manifest.json')
        with self.assertRaises(ValueError): loader.get_scenario('toast_base_20261109_025', MANIFEST)

    def test_recording_manifest_snapshot_and_replay(self):
        for group in gen.GROUPS:
            e = next(e for e in self.entries if e['scenario_group'] == group and e['group_index'] == 1)
            with tempfile.TemporaryDirectory() as tmp:
                directory, meta = create_diagnostic(Path(tmp) / 'record', MANIFEST, e['operator'], e['id'], e['operator_index'], seed=1)
                for key in ('scenario_group', 'group_index', 'operator_index'):
                    self.assertEqual(meta[key], e[key])
                self.assertEqual(meta['scenario_id'], e['id'])
                self.assertEqual(meta['manifest_source'], str(MANIFEST.resolve()))
                self.assertEqual(meta['manifest_sha256'], gen.shared.sha(MANIFEST))
                self.assertEqual((directory / 'manifest.json').read_bytes(), MANIFEST.read_bytes())
                sid, path = scenario_for_replay(directory, meta, TASK)
                self.assertEqual(sid, e['id'])
                cfg = fixture(self.environment); cfg.scenario_manifest = path
                loader.apply_scenario(cfg, sid)
                self.assertEqual(cfg.scene.plate.init_state.pos, tuple(e['poses']['plate']['position_m']))

    def test_existing_success_predicate_is_logically_satisfiable_at_every_plate(self):
        serving.ServingSuccess.setUpClass(); case = serving.ServingSuccess()
        for e in self.entries:
            for bread in range(4):
                case.setUp(); plate = case.env.scene['plate'].data; p = e['poses']['plate']
                plate.root_pos_w = torch.tensor([p['position_m']], dtype=torch.float64) + case.env.scene.env_origins
                plate.root_quat_w = torch.tensor([p['quaternion_wxyz']], dtype=torch.float64)
                plate.default_root_state = torch.tensor([p['position_m']], dtype=torch.float64)
                case.place(bread)
                self.assertFalse(case.done(case.env).item())
                case.env.toast_cycle.heated_bread[0, bread] = True
                self.assertTrue(case.done(case.env).item(), (e['id'], bread))

    def test_assignments_pose_csv_and_current_mesh_cards(self):
        with (DELIVERY / 'assignments.csv').open() as stream: assignments = list(csv.DictReader(stream))
        with (DELIVERY / 'poses.csv').open() as stream: rows = list(csv.DictReader(stream))
        byid = {e['id']: e for e in self.entries}
        self.assertEqual(len(assignments), 100)
        self.assertEqual({r['scenario_id'] for r in assignments}, set(byid))
        for r in assignments:
            e = byid[r['scenario_id']]
            for k in ('operator', 'scenario_group', 'operator_index', 'group_index'):
                self.assertEqual(str(e[k]), r[k])
            self.assertEqual(r['order_positive_to_negative_y'], '>'.join(gen.ORDER))
        self.assertEqual(len(rows), 700)
        self.assertEqual(len({(r['scenario_id'], r['object']) for r in rows}), 700)
        for r in rows:
            p = byid[r['scenario_id']]['poses'][r['object']]
            self.assertEqual([float(r[k]) for k in ('x','y','z','qw','qx','qy','qz','sx','sy','sz')],
                             [*p['position_m'], *p['quaternion_wxyz'], *p['scale']])
        html = (DELIVERY / 'overview_cards.html').read_text()
        payload = png.embedded(html, 'scenario-data'); meta = png.embedded(html, 'geometry-meta')
        self.assertEqual(len(payload), 100); self.assertEqual(meta['manifest_sha256'], gen.shared.sha(MANIFEST))
        self.assertEqual(meta['assignments_sha256'], gen.shared.sha(DELIVERY / 'assignments.csv'))
        objects = gen.ROOT / 'source/cyclo_lab/data/objects'
        paths = {n: objects / 'robodojo_make_toast' / n / 'object.usdz' for n in ('bread', 'plate', 'toaster')}
        paths['bread_shelf'] = objects / 'bread_slot/rack.usda'
        parts = {n: cards.mesh_parts(p) for n, p in paths.items()}
        vertices = {n: np.concatenate([v for v, faces in ps]) for n, ps in parts.items()}
        for card in payload:
            e = byid[card['id']]; self.assertEqual(card['poses'], e['poses'])
            for k, field in [('group','scenario_group'),('index','group_index'),('operator','operator'),('operator_index','operator_index'),('order','order_positive_to_negative_y')]:
                self.assertEqual(card[k], e[field])
            for n, p in e['poses'].items():
                name = 'bread' if n.startswith('bread_') and n != 'bread_shelf' else n
                r = Rotation.from_quat(np.array(p['quaternion_wxyz'])[[1, 2, 3, 0]])
                world = r.apply(vertices[name] * p['scale']) + p['position_m']
                expected = MultiPoint(world[:, :2]).convex_hull
                drawn = MultiPoint(previous_tests.path_points(card['shapes'][n])).convex_hull
                self.assertLessEqual(expected.hausdorff_distance(drawn), 1e-6 + np.sqrt(2) * .5e-6 + 1e-12)
            top = cards.project(parts['bread_shelf'], e['poses']['bread_shelf'], top=True)
            drawn = MultiPoint(previous_tests.path_points(card['rack_top'])).convex_hull
            self.assertLessEqual(top.convex_hull.hausdorff_distance(drawn), 2e-6 + np.sqrt(2) * .5e-6 + 1e-12)
        for kind in ('source_sha256', 'asset_sha256', 'existing_manifest_sha256'):
            for path, digest in self.data['provenance'][kind].items():
                self.assertEqual(gen.shared.sha(gen.ROOT / path), digest, path)

    def test_png_metadata_sizes_and_sheet_order(self):
        directory = DELIVERY / 'images'
        entries = sorted(self.entries, key=lambda e: (e['scenario_group'], e['group_index']))
        self.assertEqual({p.stem for p in (directory / 'individual').glob('*.png')}, {e['id'] for e in entries})
        viewbox = png.embedded((DELIVERY / 'overview_cards.html').read_text(), 'geometry-meta')['viewBox']
        for e in entries:
            with Image.open(directory / 'individual' / (e['id'] + '.png')) as im:
                self.assertEqual(im.size, (1600, 680))
                for k, expected in [('scenario_id', e['id']), ('scenario_group', e['scenario_group']),
                    ('group_index', str(e['group_index'])), ('manifest_sha256', gen.shared.sha(MANIFEST)), ('viewBox', viewbox)]:
                    self.assertEqual(im.info[k], expected)
                self.assertEqual(json.loads(im.info['poses']), e['poses']); im.verify()
        for group in (*gen.GROUPS, 'overview_100'):
            selected = [e['id'] for e in entries if group == 'overview_100' or e['scenario_group'] == group]
            with Image.open(directory / (group + '.png')) as im:
                self.assertEqual(im.size, (16000, 6920) if group == 'overview_100' else (8000, 3520))
                self.assertEqual(json.loads(im.info['scenario_ids']), selected)
                self.assertEqual(im.info['viewBox'], viewbox)
                self.assertEqual(im.info['manifest_sha256'], gen.shared.sha(MANIFEST)); im.verify()

    def test_reproduction_in_separate_empty_directory(self):
        with tempfile.TemporaryDirectory(prefix='toast-ptb-reproduce-') as tmp:
            rebuilt = Path(tmp) / 'delivery'
            with contextlib.redirect_stdout(io.StringIO()): gen.generate(rebuilt)
            files = sorted(p.relative_to(rebuilt) for p in rebuilt.rglob('*') if p.is_file())
            self.assertEqual(len(files), 9)
            for name in files:
                self.assertEqual((rebuilt / name).read_bytes(), (DELIVERY / name).read_bytes(), str(name))
            with self.assertRaises(ValueError): gen.generate(rebuilt)


if __name__ == '__main__':
    unittest.main()
