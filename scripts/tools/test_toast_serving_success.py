"""CPU tests of real serving predicates and per-slice cycle evidence; no PhysX."""
import ast
import math
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import numpy as np
import torch
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from pxr import Usd, UsdGeom
import test_toaster_led as cycle_tests
from test_toaster_led import CFG, ROOT, led, UP, DOWN


def extract(name, scope, file='bimanual_mdp.py'):
    node=next(n for n in ast.parse((CFG/file).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),file,'exec'),scope)
    return scope[name]


def vertices(name, scale=(1,1,1)):
    s=Usd.Stage.Open(str(ROOT/f'source/cyclo_lab/data/objects/robodojo_make_toast/{name}/object.usdz'))
    root_inverse=np.linalg.inv(np.asarray(UsdGeom.Xformable(s.GetDefaultPrim()).ComputeLocalToWorldTransform(0)))
    values=[]
    for p in s.Traverse():
        if p.IsA(UsdGeom.Mesh) and 'collision' not in str(p.GetPath()):
            m=UsdGeom.Mesh(p);t=np.asarray(m.ComputeLocalToWorldTransform(0))@root_inverse
            values.append((np.asarray(m.GetPointsAttr().Get())@t[:3,:3]+t[3,:3])*scale)
    return np.concatenate(values)


class HeatingEvidence(unittest.TestCase):
    setUp=cycle_tests.CycleTests.setUp
    press=cycle_tests.CycleTests.press

    def start(self, i):
        self.loaded={(f'bread_{i}',i%2)};self.press(.90);self.cycle.update(.04)

    def lower(self):
        self.q[0,1]=-.045;self.cycle.update(.60)
        self.assertEqual(self.cycle.phase.item(),2)
        self.assertEqual(self.cycle.heating_time.item(),0)

    def test_each_id_requires_full_heating(self):
        for i in range(4):
            with self.subTest(i=i):
                self.setUp();self.start(i);self.lower()
                self.cycle.update(3.96)
                self.assertFalse(self.cycle.heated_bread.any())
                self.cycle.update(.04)
                self.assertEqual(self.cycle.heated_bread.tolist(),[[j==i for j in range(4)]])
                self.assertFalse(led.indicator_on(self.cycle.phase).item())
                self.cycle.reset(torch.tensor([0]))
                self.assertFalse(self.cycle.heated_bread.any())
                self.assertFalse(self.cycle.heating_present.any())
                self.assertEqual(self.cycle.heating_time.item(),0)

    def test_removed_before_heating_never_cooked(self):
        self.start(0);self.loaded.clear();self.lower();self.cycle.update(4.)
        self.assertEqual(self.cycle.phase.item(),3)
        self.assertFalse(self.cycle.heated_bread.any())

    def test_removal_reinsertion_and_late_arrival_not_cooked(self):
        self.start(0);self.lower();self.cycle.update(1.)
        self.loaded={("bread_1",1)};self.cycle.update(1.)
        self.loaded.add(("bread_0",0));self.cycle.update(2.)
        self.assertFalse(self.cycle.heated_bread.any())

    def test_state_roundtrip_and_legacy_fail_closed(self):
        self.start(2);self.lower();self.cycle.update(2.)
        saved=self.cycle.state()
        self.cycle.reset(torch.tensor([0]))
        self.cycle.restore(saved,torch.tensor([0]));self.cycle.update(2.)
        self.assertTrue(self.cycle.heated_bread[0,2])
        cooked=self.cycle.state();self.cycle.reset(torch.tensor([0]))
        self.cycle.restore(cooked,torch.tensor([0]))
        self.assertTrue(self.cycle.heated_bread[0,2])
        legacy={k:v for k,v in saved.items() if k in self.cycle.STATE_NAMES}
        self.cycle.restore(legacy,torch.tensor([0]));self.cycle.update(2.)
        self.assertFalse(self.cycle.heated_bread.any())

    def test_partial_reset_keeps_other_environment_evidence(self):
        env=self.cycle.env;env.num_envs=2
        c=type(self.cycle)(env);c.heated_bread[:,2]=True;c.heating_present[:,2]=True
        c.reset(torch.tensor([1]))
        self.assertEqual(c.heated_bread[:,2].tolist(),[True,False])
        self.assertEqual(c.heating_present[:,2].tolist(),[True,False])


class ServingSuccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        points=vertices('bread');cls.points=points[ConvexHull(points).vertices]
        cls.center=(points.min(0)+points.max(0))/2
        # Execute actual geometry-center helper with actual pinned hull vertices.
        center_scope={'lru_cache':lambda **kw:lambda f:f,'bread_support_vertices':lambda:cls.points}
        cls.center_fn=staticmethod(extract('bread_geometry_center',center_scope,'bread_geometry.py'))
        assets={}
        for node in ast.parse((CFG/'assets.py').read_text()).body:
            if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name):
                if node.targets[0].id in ('SERVING_BREAD_CENTER_RADIUS','BIMANUAL_STANDBY_WRIST'):
                    assets[node.targets[0].id]=ast.literal_eval(node.value)
        cls.radius=assets['SERVING_BREAD_CENTER_RADIUS']
        def rot(q):return Rotation.from_quat(q.numpy()[:,[1,2,3,0]])
        def subtract(p,q,b,r):
            inv=rot(q).inv()
            return torch.tensor(inv.apply((b-p).numpy())),torch.tensor((inv*rot(r)).as_quat()[:,[3,0,1,2]])
        cls.rot=staticmethod(rot)
        scope=dict(torch=torch,**assets,
            bread_support_vertices=lambda:cls.points,bread_geometry_center=cls.center_fn,
            math_utils=NS(subtract_frame_transforms=subtract,matrix_from_quat=lambda q:torch.tensor(rot(q).as_matrix())),
            mdp=NS(object_position=lambda e,n:e.scene[n].data.root_pos_w-e.scene.env_origins,
                   lever_pressed=lambda e:torch.tensor([e.lever_pressed])))
        for name in ('lift_position','gripper_positions','bread_on_plate','task_done'):
            extract(name,scope)
        cls.check=staticmethod(scope['bread_on_plate']);cls.done=staticmethod(scope['task_done'])
        cls.standby=assets['BIMANUAL_STANDBY_WRIST']

    def setUp(self):
        class Scene(dict):pass
        scene=Scene();scene.env_origins=torch.tensor([[2.,3.,0.]],dtype=torch.float64)
        def body(pos):return NS(data=NS(root_pos_w=torch.tensor([pos],dtype=torch.float64)+scene.env_origins,
            root_quat_w=torch.tensor([[1.,0,0,0]],dtype=torch.float64),root_lin_vel_w=torch.zeros((1,3),dtype=torch.float64)))
        scene['plate']=body([.43,.035,1.004222776]);scene['plate'].data.default_root_state=torch.tensor([[.43,.035,1.004222776]],dtype=torch.float64)
        for i in range(4):
            scene[f'bread_{i}']=body([3.,4.,2.]);scene[f'bread_{i}'].data.root_lin_vel_w[:]=9 # unrelated slices impose no stability/location requirement
        standby=torch.tensor([[self.standby,(self.standby[0],-self.standby[1],self.standby[2])]],dtype=torch.float64)+scene.env_origins[:,None]
        scene['robot']=NS(body_names=['arm_l_link7','arm_r_link7'],joint_names=['gripper_l_joint1','gripper_r_joint1','lift_joint'],
            data=NS(body_link_pos_w=standby,joint_pos=torch.zeros((1,3))))
        self.env=NS(scene=scene,cfg=NS(serve_to_plate=True),device='cpu',num_envs=1,lever_pressed=False,
            toast_cycle=NS(phase=torch.tensor([4.]),heated_bread=torch.zeros((1,4),dtype=torch.bool)))

    def place(self,i,xy=(0.,0.),height=.010,yaw=0.):
        plate=self.env.scene['plate'].data;bread=self.env.scene[f'bread_{i}'].data
        r=self.rot(plate.root_quat_w)
        local_rot=Rotation.from_euler('z',yaw)
        local=np.array([*xy,height])-local_rot.apply(self.center)
        bread.root_pos_w=plate.root_pos_w+torch.tensor(r.apply(local))
        bread.root_quat_w=torch.tensor((r*local_rot).as_quat()[:,[3,0,1,2]])
        bread.root_lin_vel_w.zero_()

    def test_measured_center_and_radius_budget(self):
        np.testing.assert_allclose(self.center_fn(),self.center,atol=1e-10)
        self.assertGreater(abs(self.center[2]),.005)
        plate=vertices('plate',(1.5,1.5,.22));h=ConvexHull(plate[:,:2])
        inscribed=(-h.equations[:,2]).min();sphere=np.linalg.norm(self.points-self.center,axis=1).max()
        self.assertLess(self.radius+sphere,inscribed-.0005)
        print(f'GEOMETRY center={self.center.tolist()} bread_radius={sphere:.10f} plate_radius={inscribed:.10f} success_radius={self.radius}')

    def test_each_cooked_bread_succeeds_others_unrestricted(self):
        for i in range(4):
            with self.subTest(i=i):
                self.setUp();self.place(i);self.env.toast_cycle.heated_bread[0,i]=True
                self.assertTrue(self.done(self.env).item())

    def test_raw_or_different_id_rejected(self):
        self.place(3)
        self.assertFalse(self.done(self.env).item())
        self.env.toast_cycle.heated_bread[0,0]=True
        self.assertFalse(self.done(self.env).item())
        self.env.toast_cycle.heated_bread[0,3]=True
        self.assertTrue(self.done(self.env).item())
        self.env.toast_cycle.heated_bread.zero_()
        self.assertFalse(self.done(self.env).item())

    def test_center_radius_current_plate_pose(self):
        for yaw in (0.,1.2):
            self.setUp()
            self.env.scene['plate'].data.root_quat_w=torch.tensor([[math.cos(yaw/2),0,0,math.sin(yaw/2)]],dtype=torch.float64)
            self.env.scene['plate'].data.root_pos_w+=torch.tensor([[.01,-.01,0.]])
            for distance,expected in ((.019999,True),(.020001,False)):
                self.place(1,(distance,0.),yaw=.8)
                self.assertEqual(self.check(self.env,'bread_1').item(),expected)
        self.setUp();self.place(0,(self.radius,0.))
        # Test exact mathematical strict boundary without world-coordinate cancellation.
        self.env.scene['plate'].data.root_pos_w.zero_()
        self.env.scene['bread_0'].data.root_pos_w=torch.tensor([[self.radius-self.center[0],-self.center[1],.010-self.center[2]]])
        self.assertFalse(self.check(self.env,'bread_0').item())

    def test_height_tilt_speed_unchanged(self):
        self.place(0,height=.10);self.assertFalse(self.check(self.env,'bread_0').item())
        self.place(0,height=-.01);self.assertFalse(self.check(self.env,'bread_0').item())
        # Existing height tolerance also admits low hovering; do not silently add contact constraints.
        self.place(0,height=.025);self.assertTrue(self.check(self.env,'bread_0').item())
        self.env.scene['bread_0'].data.root_lin_vel_w[0,0]=.15
        self.assertFalse(self.check(self.env,'bread_0').item())
        self.place(0);self.env.scene['bread_0'].data.root_quat_w=torch.tensor([[math.sqrt(.5),math.sqrt(.5),0,0]],dtype=torch.float64)
        self.assertFalse(self.check(self.env,'bread_0').item())

    def test_nonbread_success_conditions_remain(self):
        self.place(0);self.env.toast_cycle.heated_bread[0,0]=True
        self.assertTrue(self.done(self.env).item())
        changes=[lambda e:setattr(e,'lever_pressed',True),lambda e:e.toast_cycle.phase.fill_(3),
                 lambda e:e.scene['robot'].data.joint_pos.__setitem__((0,0),.15),
                 lambda e:e.scene['robot'].data.joint_pos.__setitem__((0,2),.02),
                 lambda e:e.scene['robot'].data.body_link_pos_w.__setitem__((0,0,0),9),
                 lambda e:e.scene['plate'].data.root_pos_w.__setitem__((0,0),2.418),
                 lambda e:e.scene['plate'].data.root_pos_w.__setitem__((0,1),3.10),
                 lambda e:e.scene['plate'].data.root_quat_w.__setitem__((0,slice(None)),torch.tensor([math.sqrt(.5),math.sqrt(.5),0,0]))]
        for change in changes:
            self.setUp();self.place(0);self.env.toast_cycle.heated_bread[0,0]=True;change(self.env)
            self.assertFalse(self.done(self.env).item())

if __name__=='__main__':unittest.main()
