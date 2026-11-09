"""CPU checks for the fixed-base corpus; no PhysX, GUI, VR or reachability claim."""
import csv
from collections import Counter
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
from shapely.geometry import MultiPoint, Polygon
import torch

import generate_base_toast_scenarios as gen
import build_toast_overview_cards as cards
from test_toast_scenario_runtime import m as loader, fixture
from view_make_toast_scenario import build_parser, resolve_selection
from toast_recording_metadata import create_diagnostic, scenario_for_replay, TASK
from test_toast_serving_success import ServingSuccess

ROOT=gen.ROOT
DELIVERY=gen.DEFAULT_OUTPUT


def path_points(path):
    values=np.array([float(v) for v in re.findall(r'-?\d+(?:\.\d+)?',path)]).reshape(-1,2)
    # Display projects environment XY as SVG (-Y, -X), in millimetres.
    return -values[:,[1,0]]/1000


class BaseDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=loader.load_manifest(DELIVERY/'manifest.json');cls.entries=cls.data['scenarios']
        cls.base,_=gen.shared.current_contract();cls.vertices,_=gen.shared.geometry(cls.base)
        cls.evidence=json.loads((DELIVERY/'inputs/geometry_evidence.json').read_text())

    def test_ids_counts_and_saved_deltas(self):
        ids={e['id'] for e in self.entries}
        self.assertEqual(ids,{gen.PREFIX+f'{i:03d}' for i in range(100)})
        self.assertFalse(ids & {e['id'] for e in self.base['scenarios']})
        self.assertEqual(len({gen.shared.signature(e['poses']) for e in self.entries}),100)
        self.assertEqual(Counter(e['operator'] for e in self.entries),{'operator_A':50,'operator_B':50})
        self.assertEqual(self.data['generation']['reference_poses'],gen.reference_poses(self.base))
        for g in gen.GROUPS:
            entries=[e for e in self.entries if e['scenario_group']==g]
            self.assertEqual(sorted(e['group_index'] for e in entries),list(range(1,26)))
            self.assertEqual(sorted(e['operator_index'] for e in entries),list(range(26,51) if g.endswith('_2') else range(1,26)))
        for e in self.entries:
            self.assertEqual(e['order_positive_to_negative_y'],list(gen.ORDER))
            for n,(dx,dy,yaw) in e['jitter'].items():
                self.assertLessEqual(abs(dx),.02);self.assertLessEqual(abs(dy),.02);self.assertLessEqual(abs(yaw),5)
                ref=self.data['baseline'][n];p=e['poses'][n]
                np.testing.assert_allclose(np.array(p['position_m'])-ref['position_m'],[dx,dy,0],atol=1e-15)
                q=Rotation.from_quat(np.array(p['quaternion_wxyz'])[[1,2,3,0]])
                r=Rotation.from_quat(np.array(ref['quaternion_wxyz'])[[1,2,3,0]])
                np.testing.assert_allclose((q*r.inv()).as_rotvec(),[0,0,np.deg2rad(yaw)],atol=1e-14)
                self.assertEqual(p['scale'],self.data['scales'].get(n,[1.,1.,1.]))
            self.assertEqual(e['poses'],gen.make_poses(self.base,e['jitter']))

    def test_actual_asset_geometry(self):
        for e in self.entries:
            reasons,_,checks=gen.check_layout(e['poses'],self.vertices,self.evidence)
            self.assertFalse(reasons,(e['id'],reasons))
            self.assertEqual(checks,e['checks'])
        self.assertEqual(self.data['static_validation']['attempts'],100+self.data['static_validation']['rejected'])

    def test_selection_loader_recording_and_manifest_isolation(self):
        with (DELIVERY/'assignments.csv').open() as stream: rows=list(csv.DictReader(stream))
        byid={e['id']:e for e in self.entries}
        for row in rows:
            e=byid[row['scenario_id']]
            for field in ('operator','scenario_group','operator_index','group_index'):
                self.assertEqual(str(e[field]),row[field])
            for mode in (['--scenario_group',e['scenario_group'],'--group_index',str(e['group_index'])],
                         ['--operator',e['operator'],'--scenario_index',str(e['operator_index'])]):
                args=build_parser().parse_args(['--scenario_manifest',str(DELIVERY/'manifest.json'),*mode])
                self.assertEqual(resolve_selection(args),e['id'])
                self.assertEqual((args.operator,args.scenario_index),(e['operator'],e['operator_index']))
            cfg=fixture(self.data);cfg.scenario_manifest=str(DELIVERY/'manifest.json')
            loader.apply_scenario(cfg,e['id']) # actual loader validates every relative bread pose
            for name,pose in e['poses'].items():
                self.assertEqual(tuple(pose['position_m']),getattr(cfg.scene,name).init_state.pos)
            with self.assertRaises(ValueError):loader.get_scenario(e['id'])
        for group in gen.GROUPS:
            e=next(e for e in self.entries if e['scenario_group']==group and e['group_index']==1)
            with tempfile.TemporaryDirectory() as tmp:
                directory,meta=create_diagnostic(Path(tmp)/'record',DELIVERY/'manifest.json',e['operator'],e['id'],e['operator_index'])
                self.assertEqual(scenario_for_replay(directory,meta,TASK)[0],e['id'])
                self.assertEqual(meta['scenario_group'],group)
        source=(ROOT/'scripts/quest_diagnostic/teleop_toast.py').read_text()
        self.assertIn('selected_id=resolve_selection(known)',source)
        self.assertIn('Path(known.scenario_manifest).resolve()==DEFAULT_MANIFEST.resolve()',source)
        self.assertIn('cfg.scenario_id=selected_id;cfg.scenario_manifest=args.scenario_manifest',source)

    def test_plate_success_position_is_satisfiable(self):
        # Actual success predicate, CPU scene I/O: a constructed terminal state, not a solved trajectory.
        ServingSuccess.setUpClass();case=ServingSuccess()
        for e in self.entries:
            case.setUp();plate=case.env.scene['plate'].data;p=e['poses']['plate']
            plate.root_pos_w=torch.tensor([p['position_m']],dtype=torch.float64)+case.env.scene.env_origins
            plate.root_quat_w=torch.tensor([p['quaternion_wxyz']],dtype=torch.float64)
            plate.default_root_state=torch.tensor([p['position_m']],dtype=torch.float64)
            case.place(0);case.env.toast_cycle.heated_bread[0,0]=True
            self.assertTrue(case.done(case.env).item(),e['id'])

    def test_pose_csv_and_assignment_report(self):
        with (DELIVERY/'poses.csv').open() as stream: rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),700)
        lookup={(e['id'],n):p for e in self.entries for n,p in e['poses'].items()}
        self.assertEqual(len({(r['scenario_id'],r['object']) for r in rows}),700)
        for row in rows:
            p=lookup[row['scenario_id'],row['object']]
            self.assertEqual([float(row[k]) for k in ('x','y','z','qw','qx','qy','qz','sx','sy','sz')],
                             [*p['position_m'],*p['quaternion_wxyz'],*p['scale']])
        with tempfile.TemporaryDirectory() as tmp:
            gen.shared.write_assignments(Path(tmp),self.entries)
            self.assertEqual((Path(tmp)/'ASSIGNMENTS.md').read_bytes(),(DELIVERY/'ASSIGNMENTS.md').read_bytes())

    def test_card_payload_and_direct_current_mesh_projection(self):
        html=(DELIVERY/'overview_cards.html').read_text()
        payload=json.loads(re.search(r'<script id="scenario-data"[^>]*>(.*?)</script>',html,re.S).group(1))
        meta=json.loads(re.search(r'<script id="geometry-meta"[^>]*>(.*?)</script>',html,re.S).group(1))
        self.assertEqual(meta['manifest_sha256'],gen.shared.sha(DELIVERY/'manifest.json'))
        self.assertEqual(len(payload),100)
        objects=ROOT/'source/cyclo_lab/data/objects'
        paths={n:objects/'robodojo_make_toast'/n/'object.usdz' for n in ('bread','plate','toaster')}
        paths['bread_shelf']=objects/'bread_slot/rack.usda'
        parts={n:cards.mesh_parts(p) for n,p in paths.items()}
        lookup={e['id']:e for e in self.entries}
        for card in payload:
            e=lookup[card['id']]
            self.assertEqual(card['poses'],e['poses'])
            for key,field in [('group','scenario_group'),('index','group_index'),('operator','operator'),('operator_index','operator_index'),('order','order_positive_to_negative_y')]:
                self.assertEqual(card[key],e[field])
            for name,p in e['poses'].items():
                asset='bread' if name.startswith('bread_') and name!='bread_shelf' else name
                vertices=np.concatenate([v for v,faces in parts[asset]])
                rotation=Rotation.from_quat(np.array(p['quaternion_wxyz'])[[1,2,3,0]])
                world=rotation.apply(vertices*np.array(p['scale']))+p['position_m']
                expected=MultiPoint(world[:,:2]).convex_hull
                drawn=MultiPoint(path_points(card['shapes'][name])).convex_hull
                # Rendering only: 1 micrometre simplification plus 2D half-step rounding.
                # This is not a physical collision or success tolerance.
                render_error_m=1e-6+np.sqrt(2)*.5e-6+1e-12
                self.assertLessEqual(expected.hausdorff_distance(drawn),render_error_m,(e['id'],name))
            top=cards.project(parts['bread_shelf'],e['poses']['bread_shelf'],top=True)
            drawn_top=MultiPoint(path_points(card['rack_top'])).convex_hull
            self.assertLessEqual(top.convex_hull.hausdorff_distance(drawn_top),2e-6+np.sqrt(2)*.5e-6+1e-12)
        for path,digest in self.data['provenance']['source_sha256'].items():self.assertEqual(gen.shared.sha(ROOT/path),digest,path)
        for path,digest in meta['asset_sha256'].items():self.assertEqual(gen.shared.sha(ROOT/path),digest,path)


if __name__=='__main__':unittest.main()
