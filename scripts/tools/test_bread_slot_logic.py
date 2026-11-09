"""CPU tests of actual predicate/reset function bodies, with fake scene I/O."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import numpy as np
import torch
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[2]
CFG=ROOT/'source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2'
OFFSETS=tuple((x-.005607555,.000249905,.0885+.994051338865205-1.0382) for x in (.09,.03,-.03,-.09))

def rot(q):
    q=np.asarray(q);return Rotation.from_quat(q[:,[1,2,3,0]])

def subtract(p,q,b,r):
    inverse=rot(q).inv();point=inverse.apply(np.asarray(b-p));quat=(inverse*rot(r)).as_quat()[:,[3,0,1,2]]
    return torch.tensor(point),torch.tensor(quat)

math_utils=NS(subtract_frame_transforms=subtract,matrix_from_quat=lambda q:torch.tensor(rot(q).as_matrix()))

def function(name):
    tree=ast.parse((CFG/'bimanual_mdp.py').read_text())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    node.body=[n for n in node.body if not isinstance(n,ast.ImportFrom)]
    scope=dict(torch=torch,math_utils=math_utils,BREAD_OFFSETS=OFFSETS,
               mdp=NS(object_position=lambda env,name:env.scene[name].data.root_state_w[:,:3]-env.scene.env_origins))
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(CFG/'bimanual_mdp.py'),'exec'),scope)
    return scope[name]

class Body:
    def __init__(self,pose):
        state=torch.tensor([[*pose['position_m'],*pose['quaternion_wxyz'],0,0,0,0,0,0]],dtype=torch.float64)
        self.data=NS(default_root_state=state,root_state_w=state.clone(),root_quat_w=state[:,3:7].clone(),default_joint_pos=torch.zeros((1,3)))
    def write_root_state_to_sim(self,state,ids):
        self.data.root_state_w=state.clone();self.data.root_quat_w=state[:,3:7].clone()
    def write_joint_state_to_sim(self,*args,**kwargs):pass
    def set_joint_position_target(self,*args,**kwargs):pass

class Scene(dict):pass

class BreadSlotLogic(unittest.TestCase):
    def test_all_scenarios_reset_and_spare_predicate(self):
        check=function('spare_bread_on_shelf');reset=function('reset_objects')
        data=json.loads((ROOT/'scenario_delivery/manifest_bread_slot.json').read_text())
        for entry in data['scenarios']:
            poses=entry['poses'];scene=Scene({n:Body(p) for n,p in poses.items() if n!='bread_shelf'})
            scene.env_origins=torch.tensor([[3.,6.,0.]],dtype=torch.float64)
            shelf=NS(init_state=NS(pos=poses['bread_shelf']['position_m'],rot=poses['bread_shelf']['quaternion_wxyz']))
            env=NS(scene=scene,cfg=NS(scene=NS(bread_shelf=shelf),serve_to_plate=True),device='cpu',num_envs=1)
            for _ in range(2):
                reset(env,None)
                self.assertTrue(check(env).item(),entry['id'])
                for n in ('bread_0','bread_1','bread_2','bread_3'):
                    torch.testing.assert_close(scene[n].data.root_state_w[:,:3]-scene.env_origins,scene[n].data.default_root_state[:,:3])
                scene['bread_2'].data.root_state_w[0,2]+=.02
                self.assertFalse(check(env).item())
            reset(env,None)
            shift=rot(torch.tensor([shelf.init_state.rot])).apply([[.012,0,0]])
            scene['bread_3'].data.root_state_w[:,:3]+=torch.tensor(shift)
            self.assertFalse(check(env).item())
            reset(env,None)
            scene['bread_3'].data.root_quat_w[:]=torch.tensor([[1.,0,0,0]])
            self.assertFalse(check(env).item())

if __name__=='__main__':unittest.main()
