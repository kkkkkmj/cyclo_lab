import unittest,copy,tempfile
from pathlib import Path
from types import SimpleNamespace as N
import numpy as np
from slave_gain_experiment import override,readback,SLAVES,MASTERS
class Cfg(N):
 def to_dict(self):
  def d(x):return {k:d(v) for k,v in vars(x).items()} if isinstance(x,N) else ({k:d(v) for k,v in x.items()} if isinstance(x,dict) else x)
  return d(self)
def cfg():
 return Cfg(sim=N(dt=.01,render_interval=4),decimation=4,scene=N(robot=N(spawn=N(articulation_props=N(solver_position_iteration_count=32,solver_velocity_iteration_count=1)),actuators={'gripper_slave':N(stiffness=100.,damping=4.,joint_names_expr=['gripper_l_joint[2-4]','gripper_r_joint[2-4]'],effort_limit_sim=20.),'arm':N(stiffness=600.)})))
class Tensor:
 def __init__(self,x):self.x=np.asarray([x])
 def detach(self):return self
 def cpu(self):return self
 def numpy(self):return self.x
class Tests(unittest.TestCase):
 def test_process_address_not_config(self):
  from slave_gain_experiment import canonical_repr
  self.assertEqual(canonical_repr('func=<function f at 0x123>, dt=0.01'),canonical_repr('func=<function f at 0x456>, dt=0.01'))
  self.assertNotEqual(canonical_repr('func=<function f at 0x123>'),canonical_repr('func=<function other at 0x123>'))
 def test_only_slave(self):
  c=cfg();override(c);self.assertEqual(c.scene.robot.actuators['gripper_slave'].stiffness,2.);self.assertEqual(c.scene.robot.actuators['arm'].stiffness,600.);self.assertEqual(c.sim.dt,.01)
 def test_reject_combined(self):
  for key in ('dt','solver'):
   c=cfg()
   if key=='dt':c.sim.dt=.005
   else:c.scene.robot.spawn.articulation_props.solver_position_iteration_count=64
   with self.assertRaises(ValueError):override(c)
 def test_runtime_mapping_reset_guard(self):
  names=['arm_joint']+list(reversed(SLAVES+MASTERS));k=[600 if n=='arm_joint' else 2 if n in SLAVES else 100 for n in names];d=[20 if n=='arm_joint' else .5 if n in SLAVES else 4 for n in names]
  v=N(get_dof_stiffnesses=lambda:Tensor(k),get_dof_dampings=lambda:Tensor(d),get_dof_limits=lambda:Tensor([[-1,1]]*len(names)),get_dof_max_forces=lambda:Tensor([20]*len(names)),get_dof_max_velocities=lambda:Tensor([6.5]*len(names)))
  e=N(scene={'robot':N(joint_names=names,root_physx_view=v)},cfg=N(_slave_gain_experiment=True))
  with tempfile.TemporaryDirectory() as p:
   f=Path(p)/'r';first=readback(e,f,'init');readback(e,f,'reset',first);k[0]=601
   with self.assertRaises(ValueError):readback(e,f,'reset',first)
if __name__=='__main__':unittest.main()
