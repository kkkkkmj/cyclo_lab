import unittest,copy,ast
from pathlib import Path
from common import table_plan,check_geometry
class Tests(unittest.TestCase):
 def geometry(self):return dict(meters_per_unit=1.0,up_axis='Z',errors=[],fingers=[dict(joint='gripper_r_joint2',world_vertex_bounds=[[.4,-.1,1.2],[.43,-.08,1.23]]),dict(joint='gripper_r_joint4',world_vertex_bounds=[[.4,0,1.24],[.43,.02,1.27]])])
 def test_minimal_plane(self):
  g=self.geometry();p=table_plan(g);r=check_geometry(g,p);self.assertAlmostEqual(min(r['distal_gaps_m']),.01);self.assertFalse(r['all_distals_within_descent']);self.assertEqual(p['max_down_m'],.025)
 def test_recorded_overlap_preserved(self):
  from common import swept_aabb_evidence
  bounds=[[.4324318,-.46301075,1.39100922],[.50121548,-.36408151,1.47666566]]
  plan=dict(center=[.52483607,-.42090961,1.3658508],size=[.09144633,.1649623,.02],max_down_m=.025)
  before=copy.deepcopy(bounds);r=swept_aabb_evidence(bounds,plan)
  self.assertFalse(r['initial_overlap']);self.assertTrue(r['swept_overlap']);self.assertEqual(bounds,before)
 def test_invalid_geometry(self):
  for mutate in (lambda g:g['errors'].append('bad'),lambda g:g['fingers'][0].update(world_vertex_bounds=None),lambda g:g['fingers'].pop()):
   g=self.geometry();mutate(g)
   with self.assertRaises((ValueError,TypeError)):table_plan(g)
 def test_shared_xy_gate(self):
  g=self.geometry();p=table_plan(g);p['center'][0]+=1
  with self.assertRaises(ValueError):check_geometry(g,p)
 def test_no_writes_in_loop(self):
  t=ast.parse(Path(__file__).with_name('run.py').read_text())
  for loop in [x for x in ast.walk(t) if isinstance(x,ast.While)]:
   calls=[x.func.attr for x in ast.walk(loop) if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)]
   self.assertNotIn('write_joint_state_to_sim',calls);self.assertNotIn('write_root_pose_to_sim',calls)
 def test_stop_before_next_substep(self):
  import sys
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]));from contact_probe import stop_reason
  r=dict(dof_motions={'value':[1]*4},limit_excess_rad=[0,.051,0,0],links=[{'relative':{}}]*4,contacts=[{'validation':{}}]*4)
  self.assertEqual(stop_reason(r,.05,True),'joint_limit_excess')
if __name__=='__main__':unittest.main()
