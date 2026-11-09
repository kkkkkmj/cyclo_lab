import json,sys,tempfile,unittest
from pathlib import Path
from common import check_geometry,swept_aabb_evidence
from bounded_child import run_child
class Tests(unittest.TestCase):
 def fixture(self):
  plan=dict(center=[0,0,0],size=[.1,.1,.02],max_down_m=.025,support_mode='partial_distal',direct_target_joint='gripper_r_joint2',expected_contact_point_m=[0,0,.01])
  g=dict(meters_per_unit=1.,up_axis='Z',errors=[],fingers=[dict(joint='gripper_r_joint2',meshes=[dict(world_points=[[0,0,.02],[.08,0,.03]])]),dict(joint='gripper_r_joint4',meshes=[dict(world_points=[[0,.08,.08],[.08,.08,.09]])])]);return g,plan
 def test_partial(self):
  g,p=self.fixture();self.assertTrue(check_geometry(g,p)['valid'])
 def test_wrong_tip(self):
  g,p=self.fixture();p['expected_contact_point_m']=[.02,0,.01]
  with self.assertRaises(ValueError):check_geometry(g,p)
 def test_nan(self):
  g,p=self.fixture();g['fingers'][0]['meshes'][0]['world_points'][0][0]=float('nan')
  with self.assertRaises(ValueError):check_geometry(g,p)
 def test_other_guard(self):
  _,p=self.fixture();self.assertTrue(swept_aabb_evidence([[-.01,-.01,.02],[.01,.01,.03]],p)['swept_overlap'])
 def test_clean(self):
  with tempfile.TemporaryDirectory() as d:
   r=run_child([sys.executable,'-c','print("saved")'],Path(d)/'log',Path(d)/'out',2,1,.1)
   self.assertEqual(r['child_exit'],0);self.assertFalse(r['forced_cleanup'])
 def test_hung_child_only(self):
  import subprocess
  other=subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)'])
  try:
   with tempfile.TemporaryDirectory() as d:
    r=run_child([sys.executable,'-c','import signal,time;signal.signal(signal.SIGINT,signal.SIG_IGN);signal.signal(signal.SIGTERM,signal.SIG_IGN);print("evidence",flush=True);time.sleep(10)'],Path(d)/'log',Path(d)/'out',.3,1,.1)
    self.assertTrue(r['forced_cleanup']);self.assertNotEqual(r['child_exit'],0);self.assertIn('evidence',(Path(d)/'log').read_text());self.assertIsNone(other.poll())
  finally:other.terminate();other.wait()
 def test_shutdown_deadline(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'out';out.mkdir();(out/'outcome.json').write_text(json.dumps(dict(shutdown_phase='app_close_begin',app_close_completed=False)))
   r=run_child([sys.executable,'-c','import time;time.sleep(10)'],Path(d)/'log',out,3,.2,.1)
   self.assertEqual(r['timeout_reason'],'shutdown_timeout');self.assertFalse(json.loads((out/'outcome.json').read_text())['app_close_completed'])
if __name__=='__main__':unittest.main()
