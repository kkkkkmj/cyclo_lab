"""CPU USD and real ToastCycle tests; no PhysX or renderer is started."""
import math
import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS
import unittest
import torch
from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdShade

ROOT=Path(__file__).resolve().parents[2]
CFG=ROOT/'source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m

led=load('led_test_module',CFG/'lever_indicator.py')
SOURCE=ROOT/'source/cyclo_lab/data/objects/robodojo_make_toast/toaster/object.usdz'
asset=Usd.Stage.Open(str(SOURCE))
joint=UsdPhysics.PrismaticJoint(asset.GetPrimAtPath('/root/joints/joint_1'))
UP,DOWN=joint.GetLowerLimitAttr().Get(),joint.GetUpperLimitAttr().Get()

class IndicatorTests(unittest.TestCase):
    def test_actual_phase_only(self):
        self.assertEqual(led.indicator_on(torch.tensor([0.,1.,2.,3.,4.])).tolist(),
                         [False,True,True,False,False])

    def test_common_environment_hook_uses_cycle_phase(self):
        tree=ast.parse((CFG/'bimanual_env.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_update_lever_indicators')
        scope={'torch':torch}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'bimanual_env.py','exec'),scope)
        seen=[]
        env=NS(lever_indicators=NS(update=lambda phase,force:seen.append((phase.clone(),force))),
               toast_cycle=NS(phase=torch.tensor([0.,1.,2.,3.,4.])),num_envs=5,device='cpu')
        scope['_update_lever_indicators'](env,force=True)
        self.assertEqual(led.indicator_on(seen[-1][0]).tolist(),[False,True,True,False,False])
        self.assertTrue(seen[-1][1])
        env.toast_cycle=None
        scope['_update_lever_indicators'](env)
        self.assertFalse(led.indicator_on(seen[-1][0]).any().item())

    def test_usd_independence_reset_idempotence_and_transform(self):
        stage=Usd.Stage.CreateInMemory()
        paths=['/World/envs/env_0/Toaster','/World/envs/env_1/Toaster']
        UsdGeom.Xform.Define(stage,paths[0]).GetPrim().GetReferences().AddReference(str(SOURCE))
        # Isaac Lab clones can inherit env_0: color opinions must remain private.
        stage.DefinePrim('/World/envs/env_1','Xform').GetInherits().AddInherit('/World/envs/env_0')
        indicators=led.LeverIndicators(stage,paths)
        count=len(list(stage.Traverse()))
        indicators.update(torch.tensor([1.,0.]))
        def color(i):
            return tuple(UsdShade.Shader(stage.GetPrimAtPath(paths[i]+'/base/LeverPressLED/Material/Shader')).GetInput('diffuseColor').Get())
        self.assertAlmostEqual(color(0)[1],.8);self.assertAlmostEqual(color(1)[1],.025)
        indicators.update(torch.tensor([0.,1.]),force=True)
        self.assertAlmostEqual(color(0)[1],.025);self.assertAlmostEqual(color(1)[1],.8)
        led.LeverIndicators(stage,paths).update(torch.zeros(2),force=True)
        self.assertEqual(count,len(list(stage.Traverse())))
        for path in paths:
            for p in Usd.PrimRange(stage.GetPrimAtPath(path+'/base/LeverPressLED')):
                self.assertFalse(p.HasAPI(UsdPhysics.CollisionAPI))
                self.assertFalse(p.HasAPI(UsdPhysics.RigidBodyAPI))
                self.assertFalse(p.HasAPI(UsdPhysics.MassAPI))
                self.assertFalse(p.IsA(UsdPhysics.Joint))
            lens=UsdGeom.Cylinder(stage.GetPrimAtPath(path+'/base/LeverPressLED/Lens'))
            self.assertAlmostEqual(lens.GetRadiusAttr().Get(),.004)
        root=UsdGeom.Xformable(stage.GetPrimAtPath(paths[1]))
        root.MakeMatrixXform().Set(Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0,0,1),37))*Gf.Matrix4d().SetTranslate(Gf.Vec3d(1,2,3)))
        base=UsdGeom.Xformable(stage.GetPrimAtPath(paths[1]+'/base'))
        lens=UsdGeom.Xformable(stage.GetPrimAtPath(paths[1]+'/base/LeverPressLED/Lens'))
        expected=base.ComputeLocalToWorldTransform(0).Transform(Gf.Vec3d(*led.LED_POSITION))
        actual=lens.ComputeLocalToWorldTransform(0).ExtractTranslation()
        self.assertLess((actual-expected).GetLength(),1e-8)

class CycleTests(unittest.TestCase):
    def setUp(self):
        package=ModuleType('led_cycle_test');package.__path__=[str(CFG)];sys.modules[package.__name__]=package
        self.q=torch.tensor([[UP,0.]])
        self.loaded=set()
        mdp=ModuleType('led_cycle_test.mdp')
        mdp.lever_press_ratio=lambda env:led.press_fraction(self.q[:,0],UP,DOWN)
        sys.modules[mdp.__name__]=mdp
        bimanual=ModuleType('led_cycle_test.bimanual_mdp')
        bimanual.bread_in_slot=lambda env,bread,slot:torch.tensor([(bread,slot) in self.loaded])
        sys.modules[bimanual.__name__]=bimanual
        cycle=load('led_cycle_test.toast_cycle',CFG/'toast_cycle.py')
        self.targets=[]
        toaster=NS(joint_names=['joint_1','carriage_joint'],
            data=NS(joint_pos=self.q,joint_vel=torch.zeros((1,2)),joint_pos_limits=torch.tensor([[[UP,DOWN],[-.045,.015]]])),
            set_joint_position_target=lambda value,ids:self.targets.append((ids,value.clone())),
            write_joint_stiffness_to_sim=lambda *args:None)
        self.cycle=cycle.ToastCycle(NS(scene={'toaster':toaster},cfg=NS(toast_popup_extra_height=.015),num_envs=1,device='cpu'))
    def press(self,p):
        self.q[0,0]=UP+p*(DOWN-UP)
        # The inverse float32 conversion can land just below the requested 90%.
        # Use the first representable position ON the requested threshold side.
        if p == .90 and led.press_fraction(self.q[0,0],UP,DOWN) < .90:
            self.q[0,0]=torch.nextafter(self.q[0,0],torch.full_like(self.q[0,0],float('inf')))
    def test_cycle_conditions_and_four_second_clock(self):
        c=self.cycle;self.loaded={("bread_0",0)};self.press(.89);c.update(.04)
        self.assertEqual(c.phase.item(),0)
        self.press(.90);c.update(.04);self.assertEqual(c.phase.item(),1)
        self.assertTrue(led.indicator_on(c.phase).item())
        # Lever jitter (and no subsequent loading requirement) cannot unlatch the cycle.
        self.press(.2);self.loaded.clear()
        self.q[0,1]=-.045
        c.elapsed[:]=.55;c.update(.04);self.assertEqual(c.phase.item(),1)
        c.toaster.data.joint_vel[0,1]=.02;c.update(.04);self.assertEqual(c.phase.item(),1)
        c.toaster.data.joint_vel.zero_();c.update(.04)
        self.assertEqual(c.phase.item(),2);self.assertEqual(c.heating_time.item(),0)
        self.assertTrue(led.indicator_on(c.phase).item())
        c.update(3.96);self.assertEqual(c.phase.item(),2)
        c.update(.04);self.assertEqual(c.phase.item(),3)
        self.assertFalse(led.indicator_on(c.phase).item())
        lever_targets=[v for ids,v in self.targets if ids==[0]]
        self.assertAlmostEqual(lever_targets[-1].item(),UP)
        self.q[0,1]=.015;c.update(.90);self.assertEqual(c.phase.item(),3)
        c.update(.03);self.assertEqual(c.phase.item(),4)
        c.reset(torch.tensor([0]));self.assertEqual(c.phase.item(),0)
        self.assertFalse(led.indicator_on(c.phase).item())
        self.assertEqual(c.elapsed.item(),0)
        self.assertEqual(c.heating_time.item(),0)
        self.loaded={("bread_1",1)};self.press(0);c.update(.04)
        self.press(.90);c.update(.04)
        self.assertEqual(c.phase.item(),1)
        self.assertTrue(led.indicator_on(c.phase).item())
    def test_unloaded_press_requires_new_edge(self):
        c=self.cycle;self.press(1);c.update(.04);self.assertEqual(c.phase.item(),0)
        self.loaded={("bread_0",0)};c.update(.04);self.assertEqual(c.phase.item(),0)
        self.press(.89);c.update(.04);self.press(.90);c.update(.04)
        self.assertEqual(c.phase.item(),1)

    def test_each_target_and_slot_and_two_bread_start(self):
        cases=[{(bread,slot)} for bread in ('bread_0','bread_1','bread_2','bread_3') for slot in (0,1)]
        cases += [{('bread_0',0),('bread_1',1)}, {('bread_0',1),('bread_1',0)}, {('bread_2',0),('bread_3',1)}]
        for loaded in cases:
            with self.subTest(loaded=loaded):
                self.setUp();self.loaded=loaded;c=self.cycle
                self.press(.89);c.update(.04)
                self.assertEqual(c.phase.item(),0)
                self.assertFalse(led.indicator_on(c.phase).item())
                self.press(.90);c.update(.04)
                self.assertEqual(c.phase.item(),1)
                self.assertTrue(led.indicator_on(c.phase).item())

    def test_no_target_bread_no_light_at_or_above_threshold(self):
        for fraction in (.90,.95,1.):
            with self.subTest(fraction=fraction):
                self.setUp();self.press(fraction);self.cycle.update(.04)
                self.assertEqual(self.cycle.phase.item(),0)
                self.assertFalse(led.indicator_on(self.cycle.phase).item())

    def test_float32_positions_straddle_start_boundary(self):
        self.loaded={("bread_0",0)}
        self.press(.90)
        upper=self.q[0,0].clone()
        lower=torch.nextafter(upper,torch.full_like(upper,float('-inf')))
        self.assertLess(led.press_fraction(lower,UP,DOWN).item(),.90)
        self.assertGreaterEqual(led.press_fraction(upper,UP,DOWN).item(),.90)
        self.q[0,0]=lower;self.cycle.update(.04)
        self.assertEqual(self.cycle.phase.item(),0)
        self.q[0,0]=upper;self.cycle.update(.04)
        self.assertEqual(self.cycle.phase.item(),1)
        self.assertTrue(led.indicator_on(self.cycle.phase).item())

    def test_ninety_percent_boundary(self):
        self.loaded={("bread_3",1)}
        # Use double precision to verify the mathematical boundary independently
        # of quantization when writing a physical float32 joint position.
        self.q=self.q.double()
        self.cycle.toaster.data.joint_pos=self.q
        self.press(.899999);self.cycle.update(.04)
        self.assertEqual(self.cycle.phase.item(),0)
        self.assertFalse(led.indicator_on(self.cycle.phase).item())
        self.press(.90);self.cycle.update(.04)
        self.assertEqual(self.cycle.phase.item(),1)
        self.assertTrue(led.indicator_on(self.cycle.phase).item())

    def test_strict_four_second_boundary_and_overshoot(self):
        c=self.cycle;c.phase[:]=2;c.elapsed[:]=3.99999
        c.update(.000001)
        self.assertLess(c.elapsed.item(),4.0)
        self.assertEqual(c.phase.item(),2)
        self.assertTrue(led.indicator_on(c.phase).item())
        c.update(.00002)
        self.assertEqual(c.phase.item(),3)
        self.assertFalse(led.indicator_on(c.phase).item())
        c.reset(torch.tensor([0]))
        self.assertEqual(c.elapsed.item(),0)
        self.assertEqual(c.heating_time.item(),0)
        self.assertFalse(led.indicator_on(c.phase).item())

    def test_real_slot_geometry_all_slices_and_invalid_poses(self):
        # Execute the unchanged real geometry function and carriage-depth wrapper.
        # Only scene I/O and rigid-frame math are supplied by CPU test fixtures.
        from scipy.spatial.transform import Rotation
        def rotation(q):
            return Rotation.from_quat(q.numpy()[:,[1,2,3,0]])
        def subtract(p,q,b,r):
            inv=rotation(q).inv()
            return (torch.tensor(inv.apply((b-p).numpy())),
                    torch.tensor((inv*rotation(r)).as_quat()[:,[3,0,1,2]]))
        scope=dict(torch=torch,math=math,math_utils=NS(
            subtract_frame_transforms=subtract,
            matrix_from_quat=lambda q:torch.tensor(rotation(q).as_matrix())))
        for node in ast.parse((CFG/'assets.py').read_text()).body:
            if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name):
                name=node.targets[0].id
                if name in ('SLOT_X_BOUNDS','SLOT_Y_BOUNDS','SLOT_Z_BOUNDS'):
                    scope[name]=ast.literal_eval(node.value)
        def extract(filename,namespace):
            tree=ast.parse((CFG/filename).read_text())
            node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bread_in_slot')
            exec(compile(ast.Module(body=[node],type_ignores=[]),filename,'exec'),namespace)
            return namespace['bread_in_slot']
        geometric=extract('mdp.py',scope)
        seated=extract('bimanual_mdp.py',dict(mdp=NS(bread_in_slot=geometric)))
        sys.modules['led_cycle_test.bimanual_mdp'].bread_in_slot=seated
        env=self.cycle.env;env.toast_cycle=self.cycle
        env.scene['toaster'].data.root_pos_w=torch.zeros((1,3),dtype=torch.float64)
        env.scene['toaster'].data.root_quat_w=torch.tensor([[1.,0,0,0]],dtype=torch.float64)
        upright=torch.tensor([[math.sqrt(.5),math.sqrt(.5),0,0]],dtype=torch.float64)
        for i in range(4):
            env.scene[f'bread_{i}']=NS(data=NS(root_pos_w=torch.tensor([[2.,2.,2.]],dtype=torch.float64),root_quat_w=upright.clone()))
        for bread in ('bread_0','bread_1','bread_2','bread_3'):
            for slot,(y0,y1) in enumerate(scope['SLOT_Y_BOUNDS']):
                valid=torch.tensor([[0.,(y0+y1)/2,.06]],dtype=torch.float64)
                for label,position,quat,expected in [
                    ('valid',valid,upright,True),
                    ('outside_x',valid+torch.tensor([[.3,0,0]]),upright,False),
                    ('outside_y',valid+torch.tensor([[0,.3,0]]),upright,False),
                    ('outside_z',valid+torch.tensor([[0,0,.3]]),upright,False),
                    ('flat',valid,torch.tensor([[1.,0,0,0]],dtype=torch.float64),False)]:
                    with self.subTest(bread=bread,slot=slot,case=label):
                        self.cycle.reset(torch.tensor([0]));self.q[0,1]=0
                        item=env.scene[bread].data;item.root_pos_w=position;item.root_quat_w=quat
                        self.assertEqual(seated(env,bread,slot).item(),expected)
                        self.press(.90);self.cycle.update(.04)
                        self.assertEqual(self.cycle.phase.item(),1 if expected else 0)
                        self.assertEqual(led.indicator_on(self.cycle.phase).item(),expected)
                        item.root_pos_w=torch.tensor([[2.,2.,2.]],dtype=torch.float64)

if __name__=='__main__':unittest.main()
