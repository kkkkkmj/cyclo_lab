import copy,unittest
import numpy as np
from types import SimpleNamespace as NS
from test_teleop_gripper_options import config,per_joint
from teleop_slave_gains import configure,validate_options,readback,NAMES
class Tensor:
 def __init__(self,a):self.a=np.asarray(a)
 def __getitem__(self,k):return Tensor(self.a[k])
 def detach(self):return self
 def cpu(self):return self
 def tolist(self):return self.a.tolist()
def robot(enabled):
 names=list(reversed(NAMES));data={}
 for key in ('stiffness','dampings','max_forces','max_velocities'):data[key]=[]
 for n in names:
  master=n.endswith('joint1');candidate=enabled and not master
  for key,v in zip(data,[2 if candidate else 100,.5 if candidate else 4,30 if master else 20,6.5]):data[key].append(v)
 view=NS(get_dof_stiffnesses=lambda:Tensor([data['stiffness']]),get_dof_dampings=lambda:Tensor([data['dampings']]),get_dof_max_forces=lambda:Tensor([data['max_forces']]),get_dof_max_velocities=lambda:Tensor([data['max_velocities']]))
 return NS(joint_names=names,root_physx_view=view),data
class Tests(unittest.TestCase):
 def test_default(self):
  c=config();before=copy.deepcopy(c);groups=c.scene.robot.actuators;configure(c);self.assertEqual(c,before);self.assertIs(c.scene.robot.actuators,groups)
 def test_retired_soft_override_rejected(self):
  c=config();before=copy.deepcopy(c)
  with self.assertRaises(ValueError):configure(c,True)
  self.assertEqual(c,before)
  with self.assertRaises(ValueError):validate_options(True)
 def test_v2_defaults_and_strict_readback(self):
  c=config();a=c.scene.robot.actuators['gripper_slave']
  self.assertEqual((a.stiffness,a.damping),(100.,4.))
  values=per_joint(c)
  for name in NAMES:
   self.assertEqual((values[name]['stiffness'],values[name]['damping']),(100.,4.))
  r,d=robot(False)
  row=readback(r,'start',slave_gains=(100.,4.))
  readback(r,'reset',reference=row,slave_gains=(100.,4.))
  wrong,_=robot(True)
  with self.assertRaises(RuntimeError):readback(wrong,'start',slave_gains=(100.,4.))
  with self.assertRaises(RuntimeError):readback(wrong,'start',slave_gains=(2.,.5))
  a.stiffness=2.;a.damping=.5
  with self.assertRaises(ValueError):configure(c)
 def test_speed_candidates_preserve_all_gains(self):
  from teleop_gripper_options import configure_right_j1_speed,configure_right_j3_speed
  for option in (configure_right_j1_speed,configure_right_j3_speed):
   c=config();configure(c);option(c,True)
   values=per_joint(c)
   for name in NAMES:self.assertEqual((values[name]['stiffness'],values[name]['damping']),(100.,4.))
   validate_options(False,True,False);validate_options(False,False,True)
 def test_mapping_and_reset(self):
  r,d=robot(False);row=readback(r,'start');self.assertEqual(row['joint_names'],NAMES)
  self.assertEqual(row['velocity_limit_rad_s'],[6.5]*8)
  readback(r,'reset',reference=row)
  d['dampings'][0]=999
  with self.assertRaises(RuntimeError):readback(r,'reset',reference=row)
 def test_each_joint_readback_mismatch_rejected(self):
  for name in NAMES:
   for key in ('stiffness','dampings','max_velocities'):
    with self.subTest(name=name,key=key):
     r,d=robot(False);index=r.joint_names.index(name);d[key][index]=0.
     with self.assertRaises(RuntimeError):readback(r,'start')
 def test_hooks_before_make_and_after_resets(self):
  import ast
  from pathlib import Path
  tree=ast.parse(Path(__file__).with_name('teleop_toast.py').read_text())
  calls=[x for x in ast.walk(tree) if isinstance(x,ast.Call)]
  get=lambda name:[x for x in calls if ast.unparse(x.func)==name]
  self.assertLess(get('configure_slave_gains')[0].lineno,get('gym.make')[0].lineno)
  self.assertEqual(len(get('report_gripper_runtime')),3)
if __name__=='__main__':unittest.main()
