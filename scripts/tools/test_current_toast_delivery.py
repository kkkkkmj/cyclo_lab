"""New delivery CPU contracts, actual USD geometry and mocked reset writes; no PhysX."""
import ast
import csv
import json
import tempfile
import unittest
from toast_provenance import verify_fingerprint
from collections import Counter
from types import SimpleNamespace as NS
from pathlib import Path
import numpy as np
import torch
from pxr import Usd, UsdGeom, UsdPhysics
from scipy.spatial import ConvexHull
import generate_current_toast_scenarios as gen
from test_toast_scenario_runtime import m as loader, fixture
from view_make_toast_scenario import build_parser, resolve_selection
from check_bread_slot_geometry import mesh_points, rotation, triangle_intersects_hull
from toast_recording_metadata import create_diagnostic, scenario_for_replay, TASK

ROOT=gen.ROOT
DELIVERY=gen.DEFAULT_OUTPUT
MANIFEST=DELIVERY/'manifest.json'

class Delivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=loader.load_manifest(MANIFEST)
        cls.entries=cls.data['scenarios']

    def test_unique_and_balanced(self):
        entries=self.entries
        self.assertEqual(len(entries),100)
        self.assertEqual(len({e['id'] for e in entries}),100)
        signatures={gen.signature(e['poses']) for e in entries}
        self.assertEqual(len(signatures),100)
        history=json.loads((DELIVERY/'inputs/generation_history.json').read_text())
        import hashlib
        self.assertFalse({hashlib.sha256(s.encode()).hexdigest() for s in signatures} & set(history['previous_pose_sha256']))
        self.assertEqual(Counter(e['scenario_group'] for e in entries),dict.fromkeys(gen.GROUPS,25))
        self.assertEqual(Counter(e['operator'] for e in entries),{'operator_A':50,'operator_B':50})
        totals=[]
        for typ in range(6):
            counts=[sum(e['type_index']==typ and e['scenario_group']==g for e in entries) for g in gen.GROUPS]
            self.assertLessEqual(abs(counts[0]-counts[1]),1)
            self.assertLessEqual(abs(counts[2]-counts[3]),1)
            self.assertLessEqual(abs(sum(counts[:2])-sum(counts[2:])),1)
            totals.append(sum(counts))
        self.assertLessEqual(max(totals)-min(totals),1)

    def test_all_group_parent_selection_and_recording(self):
        for e in self.entries:
            args=build_parser().parse_args(['--scenario_manifest',str(MANIFEST),'--scenario_group',e['scenario_group'],'--group_index',str(e['group_index'])])
            self.assertEqual(resolve_selection(args),e['id'])
            self.assertEqual(resolve_selection(args),e['id'])
            self.assertEqual((args.operator,args.scenario_index),(e['operator'],e['operator_index']))
            args=build_parser().parse_args(['--scenario_manifest',str(MANIFEST),'--operator',e['operator'],'--scenario_index',str(e['operator_index'])])
            self.assertEqual(resolve_selection(args),e['id'])
        for g in gen.GROUPS:
            e=next(e for e in self.entries if e['scenario_group']==g and e['group_index']==1)
            with tempfile.TemporaryDirectory() as tmp:
                out,meta=create_diagnostic(Path(tmp)/'record',MANIFEST,e['operator'],e['id'],e['operator_index'])
                self.assertEqual(meta['scenario_group'],g)
                self.assertEqual(meta['group_index'],1)
                self.assertEqual(scenario_for_replay(out,meta,TASK)[0],e['id'])

    def test_invalid_group_selection(self):
        cases=[['--scenario_group','operator_A_1'],['--group_index','1'],
               ['--scenario_group','operator_A_1','--group_index','0'],
               ['--scenario_group','operator_A_1','--group_index','26'],
               ['--scenario_group','operator_A_1','--group_index','1','--operator','operator_A','--scenario_index','1']]
        for tokens in cases:
            args=build_parser().parse_args(['--scenario_manifest',str(MANIFEST)]+tokens)
            with self.assertRaises(ValueError):resolve_selection(args)
        args=build_parser().parse_args(['--scenario_group','operator_A_1','--group_index','1'])
        self.assertEqual(resolve_selection(args), 'toast_v20261108_097')

    def test_all_loader_and_actual_reset_function_mock_writes(self):
        tree=ast.parse((gen.CFG/'bimanual_mdp.py').read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='reset_objects')
        ns={'torch':torch};exec(compile(ast.Module(body=[node],type_ignores=[]),'actual_reset','exec'),ns)
        class Asset:
            def __init__(self,pose):
                state=torch.tensor([[*pose['position_m'],*pose['quaternion_wxyz'],*([0]*6)]],dtype=torch.float64).repeat(2,1)
                self.data=NS(default_root_state=state,default_joint_pos=torch.zeros(2,2))
            def write_root_state_to_sim(self,state,ids):self.written=state
            def write_joint_state_to_sim(self,pos,vel,env_ids):self.joints=(pos,vel)
            def set_joint_position_target(self,pos,env_ids):self.target=pos
        class Scene(dict):pass
        for e in self.entries:
            cfg=fixture(self.data);cfg.scenario_manifest=str(MANIFEST)
            loader.apply_scenario(cfg,e['id'])
            scene=Scene({n:Asset(p) for n,p in e['poses'].items()})
            scene.env_origins=torch.tensor([[0.,0.,0.],[3.,-2.,0.]],dtype=torch.float64)
            env=NS(cfg=cfg,scene=scene,num_envs=2,device='cpu')
            for ids in (None,torch.tensor([1])):
                ns['reset_objects'](env,ids)
                use=torch.arange(2) if ids is None else ids
                for name,asset in scene.items():
                    state=getattr(cfg.scene,name).init_state
                    np.testing.assert_allclose(state.pos,e['poses'][name]['position_m'])
                    if name=='bread_shelf':continue # Static asset is spawned at cfg pose; no reset write.
                    expected=asset.data.default_root_state[use].clone();expected[:,:3]+=scene.env_origins[use]
                    torch.testing.assert_close(asset.written,expected)
                self.assertTrue(torch.all(scene['toaster'].joints[1]==0))
            # Success uses plate.default_root_state for scenario-relative plate placement.
            np.testing.assert_allclose(scene['plate'].data.default_root_state[0,:3],cfg.scene.plate.init_state.pos)

    def test_actual_geometry_all_layouts_and_rack_support(self):
        base,_=gen.current_contract();points,_=gen.geometry(base)
        evidence=json.loads((DELIVERY/'inputs/geometry_evidence.json').read_text())
        for e in self.entries:
            failures,_,_=gen.validate_layout(e['poses'],points,evidence,base)
            self.assertFalse(failures,(e['id'],failures))
        stage=Usd.Stage.Open(str(ROOT/'source/cyclo_lab/data/objects/bread_slot/rack.usda'))
        prim=next(p for p in stage.Traverse() if p.HasAPI(UsdPhysics.CollisionAPI))
        vertices=mesh_points(stage,prim)
        triangles=vertices[np.asarray(UsdGeom.Mesh(prim).GetFaceVertexIndicesAttr().Get()).reshape(-1,3)]
        bread=Usd.Stage.Open(str(ROOT/'source/cyclo_lab/data/objects/robodojo_make_toast/bread/object.usdz'))
        bp=mesh_points(bread,bread.GetPrimAtPath('/World/collision'))
        baseline=[]
        s=base['baseline']['bread_shelf'];rs=rotation(s['quaternion_wxyz'])
        for i in range(4):
            p=base['baseline_bread'][f'bread_{i}']
            local=bp@rotation(p['quaternion_wxyz']).T@rs+(np.array(p['position_m'])-s['position_m'])@rs
            baseline.append(local)
            equations=ConvexHull(local).equations
            lower_equations=ConvexHull(local-[0,0,.001]).equations
            self.assertFalse(any(triangle_intersects_hull(t,equations) for t in triangles))
            self.assertTrue(any(triangle_intersects_hull(t,lower_equations) for t in triangles))
        # Rigid transforms preserve the checked rack/bread intersections and support for all 100.
        for e in self.entries:
            s=e['poses']['bread_shelf'];rs=rotation(s['quaternion_wxyz'])
            for i in range(4):
                p=e['poses'][f'bread_{i}']
                local=bp@rotation(p['quaternion_wxyz']).T@rs+(np.array(p['position_m'])-s['position_m'])@rs
                np.testing.assert_allclose(local,baseline[i],atol=1e-7)

    def test_preserved_source_and_asset_fingerprints(self):
        provenance=self.data['provenance']
        for collection in ('source_sha256','asset_sha256'):
            for path,digest in provenance[collection].items():verify_fingerprint(path, digest)
        relocation=json.loads((ROOT/'docs/toast_quest/SCENARIO_RELOCATION.json').read_text())
        for name,digest in relocation['retained_files_sha256'].items():
            self.assertEqual(gen.sha(DELIVERY/name),digest,name)
        self.assertEqual(gen.sha(DELIVERY/'inputs/generation_history.json'),relocation['generation_history_sha256'])
        history=json.loads((DELIVERY/'inputs/generation_history.json').read_text())
        for key,digest in history['source_sha256'].items():
            self.assertEqual(digest,provenance[key])

if __name__=='__main__':unittest.main()
