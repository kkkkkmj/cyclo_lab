import unittest
from types import SimpleNamespace
import numpy as np
from auto_contact_protocol import Protocol
from auto_contact_checked import effective_code
from contact_filter import validate_view,read_contact,exact_targets
from contact_probe import stop_reason
class View:
 sensor_count=1;filter_count=1;sensor_paths=['/hand'];filter_paths=[['/table/collider']];max_contact_data_count=128
 def check(self):return True
 def get_net_contact_forces(self,dt):return np.zeros((1,3))
 def get_contact_force_matrix(self,dt):return np.zeros((1,1,3))
 def get_contact_data(self,dt):return [None,None,None,None,np.zeros((1,1),dtype=int),np.zeros((1,1),dtype=int)]
class Tests(unittest.TestCase):
 def test_backend_paths_shapes_native(self):
  v=View();setup=dict(body='/hand',filters=['/table/collider'],reason=None);native=SimpleNamespace(reason=None,errors=[])
  self.assertEqual(read_contact(v,setup,.01,native)['counts'],[[0]])
  native.errors=['Filter pattern error'];self.assertIsNone(read_contact(v,setup,.01,native)['table']['value'])
  native.errors=[];v.filter_count=5
  with self.assertRaises(ValueError):validate_view(v,'/hand',['/table/collider'])
  v.filter_count=1;v.get_contact_force_matrix=lambda dt:np.zeros((1,5,3))
  self.assertIsNone(read_contact(v,setup,.01,native)['validation'])
 def test_exact_static_and_rigid_paths(self):
  from pxr import Usd,UsdGeom,UsdPhysics
  s=Usd.Stage.CreateInMemory();UsdGeom.Xform.Define(s,'/table')
  for name in ['mesh','decorative1','decorative2','decorative3','decorative4']:UsdGeom.Xform.Define(s,'/table/'+name)
  UsdPhysics.CollisionAPI.Apply(s.GetPrimAtPath('/table/mesh'))
  self.assertEqual(exact_targets(s,'/table')['targets'],['/table/mesh'])
  UsdPhysics.RigidBodyAPI.Apply(s.GetPrimAtPath('/table'))
  self.assertEqual(exact_targets(s,'/table')['targets'],['/table'])
 def test_protocol(self):
  p=Protocol();before=0
  for i in range(5000):
   contact=p.phase in ('approach','contact_hold') and p.down>=.02
   p.advance(.04,contact);self.assertLessEqual(abs(p.down-before),.01*.04+1e-12);before=p.down
   if p.phase=='done':break
  self.assertTrue(p.contact_observed);self.assertEqual(p.down,0);self.assertEqual(p.phase,'done')
  p=Protocol()
  with self.assertRaises(RuntimeError):p.advance(.04,True)
 def test_guard_and_supervisor(self):
  row=dict(dof_motions={'value':[1]*4},limit_excess_rad=[0,.06,0,0],links=[{'relative':{}}]*4,contacts=[{'validation':{}}]*4)
  self.assertEqual(stop_reason(row,.05,True),'joint_limit_excess')
  self.assertIsNone(stop_reason(row,None,False))
  row['dof_motions']['value']=[0]*4;self.assertEqual(stop_reason(row,.05,True),'dof_motion_not_confirmed_limited')
  self.assertEqual(effective_code(0,None,[]),1)
  self.assertEqual(effective_code(0,dict(status='limit_excess_captured',app_close_completed=True),[]),2)
  self.assertEqual(effective_code(0,dict(status='completed',app_close_completed=True,requested_exit_code=0),['native failure']),1)
  self.assertEqual(effective_code(0,dict(status='completed',app_close_completed=False,requested_exit_code=0),[]),1)
if __name__=='__main__':unittest.main()
