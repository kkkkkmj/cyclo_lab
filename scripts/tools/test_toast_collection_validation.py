"""Audit code tests with synthetic states; NOT a simulator test."""
import json
import tempfile
import unittest
from toast_provenance import verify_fingerprint
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import numpy as np
import torch
import validate_toast_collection as v
import generate_current_toast_scenarios as gen

class AuditTests(unittest.TestCase):
    def test_quaternion_sign_and_boundary(self):
        self.assertEqual(v.angle([1,0,0,0],[-1,0,0,0]),0)
        self.assertAlmostEqual(v.angle([1,0,0,0],[2**-.5,0,0,2**-.5]),90)

    def test_saved_static_and_vr_coverage(self):
        folder=v.DEFAULT.parent/'validation_precollection_20261109'
        rows=v.load(folder/'results.json');data=v.load(v.DEFAULT)
        self.assertEqual(len(rows),100)
        self.assertEqual({r['static'] for r in rows},{'STATIC_PASS'})
        self.assertEqual({r['stability'] for r in rows},{'NOT_RUN'})
        selected=v.load(folder/'vr_selection.json')
        self.assertEqual(len(selected),len({r['scenario_id'] for r in selected}))
        entries={e['id']:e for e in data['scenarios']}
        for group in data['generation']['groups']:
            self.assertEqual({entries[r['scenario_id']]['type_index'] for r in selected if r['group']==group},set(range(6)))
        for key in ('source_sha256','asset_sha256'):
            for path,digest in data['provenance'][key].items():verify_fingerprint(path, digest)
        self.assertEqual(v.sha(v.DEFAULT),v.load(folder/'audit.json')['manifest_sha256'])

    def test_merge_keeps_missing_runtime_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);static=path/'static';runtime=path/'runtime';out=path/'report'
            for p in (static,runtime,out):p.mkdir()
            data=v.load(v.DEFAULT);rows=[v.base_row(e) for e in data['scenarios'][:2]]
            for r in rows:r['reasons']=['PhysX_NOT_RUN']
            v.dump(static/'results.json',rows)
            digest=v.sha(v.DEFAULT)
            v.dump(static/'audit.json',dict(manifest_sha256=digest,asset_hashes={},source_hashes={}))
            v.dump(runtime/'run_config.json',dict(manifest_sha256=digest,source_asset_sha256={}))
            v.dump(runtime/(rows[0]['scenario_id']+'.json'),dict(stability='ERROR',reset='NOT_RUN',error='synthetic launch failure'))
            v.merge(NS(static_dir=static,runtime_dir=runtime,manifest=v.DEFAULT),out)
            result=v.load(out/'results.json')
            self.assertEqual(result[0]['stability'],'ERROR')
            self.assertEqual(result[1]['stability'],'NOT_RUN')
            self.assertEqual({r['full_task'] for r in result},{'NOT_VERIFIED'})
            self.assertEqual(len(v.load(out/'failures.json')),1)

    def env(self):
        class Scene(dict):
            env_origins=torch.zeros(1,3)
            def update(self,dt):pass
        scene=Scene();cfg=NS(scene=NS(),actions=NS(lift=NS(scale=.25,offset=-.25),
            left_arm=NS(controller=NS(use_relative_mode=True)),right_arm=NS(controller=NS(use_relative_mode=True))))
        for n in v.NAMES:
            pos=[.5,0,1.];rot=[1.,0,0,0]
            setattr(cfg.scene,n,NS(init_state=NS(pos=pos,rot=rot),spawn=NS(scale=(1,1,1))))
            data=NS(root_pos_w=torch.tensor([pos]),root_quat_w=torch.tensor([rot]),root_state_w=torch.tensor([[*pos,*rot,*([0.]*6)]]),
                    joint_pos=torch.zeros(1,2),default_joint_pos=torch.zeros(1,2))
            scene[n]=NS(data=data,get_world_poses=lambda d=data:(d.root_pos_w,d.root_quat_w))
        scene['robot']=NS(data=NS(joint_pos=torch.zeros(1,5)))
        class Color:
            def __init__(self,value):self.value=value
            def Get(self):return self.value
        colors=[(Color([.025]*3),Color([0]*3))]
        cycle=NS(STATE_NAMES=('phase','elapsed','command','previous_pressed','heating_time'),BREAD_STATE_NAMES=('heated_bread','heating_present'))
        for name in (*cycle.STATE_NAMES,*cycle.BREAD_STATE_NAMES):setattr(cycle,name,torch.zeros(1,4) if name in cycle.BREAD_STATE_NAMES else torch.zeros(1))
        env=NS(scene=scene,cfg=cfg,device='cpu',step_dt=.1,toast_cycle=cycle,
               lever_indicators=NS(_colors=colors,_states=[False]),action_manager=NS(total_action_dim=15),steps=0)
        def reset():
            for name in (*cycle.STATE_NAMES,*cycle.BREAD_STATE_NAMES):getattr(cycle,name).zero_()
            colors[0][0].value=[.025]*3;colors[0][1].value=[0]*3;env.lever_indicators._states=[False]
        def update(force=False):
            env.lever_indicators._states=[True];colors[0][0].value=[.01,.8,.025];colors[0][1].value=[.01,1.2,.025]
        def step(action):
            torch.testing.assert_close(action,torch.tensor([[*([0.]*12),1.,1.,1.]]))
            env.steps+=1;scene.update(.1)
            return None,None,torch.tensor([False]),torch.tensor([False]),{}
        env.reset=reset;env.step=step;env._update_lever_indicators=update
        return env

    def run_fake(self,env,tmp):
        vertices={n:np.array([[0,0,0],[.001,0,0],[0,.001,0],[0,0,.001]]) for n in ('bread','plate','bread_shelf','toaster')}
        with patch.object(gen,'current_contract',return_value=({},{})),patch.object(gen,'geometry',return_value=(vertices,{})):
            return v.runtime_audit(env,NS(scenario_id='fake',seconds=5.),Path(tmp))

    def test_stability_and_reset_challenge_and_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            env=self.env();r=self.run_fake(env,tmp)
            self.assertEqual(r['stability'],'PASS');self.assertEqual(r['reset'],'PASS')
            self.assertEqual(env.steps,100)
            self.assertEqual([x['sim_seconds'] for x in r['runs']],[5.,5.])
            self.assertFalse(any(r['challenged_reset']['cycle']['heated_bread'][0]))
            self.assertEqual(len(list(Path(tmp).glob('*.gz'))),2)

    def test_termination_is_failure_even_if_manager_resets(self):
        with tempfile.TemporaryDirectory() as tmp:
            env=self.env();step=env.step
            def terminated(a):
                x=list(step(a));x[2]=torch.tensor([True]);return tuple(x)
            env.step=terminated;r=self.run_fake(env,tmp)
            self.assertEqual(r['stability'],'FAIL')
            self.assertIn('unexpected_termination_or_timeout',r['runs'][0]['failures'])

    def test_nonfinite_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            env=self.env();env.scene['bread_0'].data.root_pos_w[0,0]=float('nan')
            with self.assertRaises(ValueError):self.run_fake(env,tmp)

    def test_bread_departure_and_last_velocity_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            env=self.env();step=env.step
            def drift(a):
                env.scene['bread_0'].data.root_pos_w[0,0]+=.001
                env.scene['bread_0'].data.root_state_w[0,7]=.2
                return step(a)
            env.step=drift;r=self.run_fake(env,tmp)
            self.assertEqual(r['stability'],'FAIL')
            self.assertIn('bread_0:groove_departure',r['runs'][0]['failures'])
            self.assertIn('bread_0:final_velocity',r['runs'][0]['failures'])
            self.assertEqual(r['reset'],'FAIL')

if __name__=='__main__':unittest.main()
