import copy,unittest
from types import SimpleNamespace as NS
from pathlib import Path
import torch
from control import BoundedTeleop
from test_control import POSES,sample
from check_gripper_contract import actual_method,ROOT
class Tests(unittest.TestCase):
 def setup_controller(self,binary=True):
  c=BoundedTeleop(POSES,0,True);c.practice=True;c.gripper_trigger_official_binary=binary;s=sample();c.update(s,measured=POSES)
  return c,s
 def update(self,c,s,sq,tr):
  for h in s['packet']['controllers'].values():h['buttons'][1]['value']=sq;h['buttons'][0]['value']=tr
  c.update(s,measured=POSES)
 def test_actual_processor(self):
  process=actual_method(ROOT/'source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/gripper_action.py','process_actions')
  c,s=self.setup_controller()
  for t in (0,.49,.5,1):
   self.update(c,s,1,t);a=c.action(POSES,.04);self.assertEqual(len(a),15)
   for index in (12,13):
    obj=NS(_raw_actions=torch.zeros(1,1),_processed_actions=torch.zeros(1,4),_open_command=torch.zeros(1,4),_close_command=torch.full((1,4),1.1))
    process(obj,torch.tensor([[a[index]]]))
    torch.testing.assert_close(obj._processed_actions,torch.full((1,4),0. if t<.5 else 1.),rtol=0,atol=2e-7)
 def test_release_reclutch_stale(self):
  c,s=self.setup_controller();self.update(c,s,1,1);closed=c.grippers.copy()
  self.update(c,s,0,0);self.assertEqual(c.grippers,closed)
  self.update(c,s,1,0);self.assertEqual(c.grippers,{'left':1.,'right':1.})
  s['live']=False;self.update(c,s,1,1);self.assertEqual(c.grippers,{'left':1.,'right':1.})
  s['live']=True;self.update(c,s,1,1);self.assertEqual(c.grippers,{'left':1.,'right':1.})
  self.update(c,s,0,1);self.update(c,s,1,1);self.assertEqual(c.grippers,closed)
 def test_default_analog(self):
  c,s=self.setup_controller(False)
  for t in (0,.49,.5,1):
   self.update(c,s,1,t);self.assertEqual(c.grippers,{'left':1-2*t,'right':1-2*t})
 def test_arm_unchanged(self):
  a,s=self.setup_controller();b,t=self.setup_controller(False)
  for tr in (0,.49,.5,1):
   self.update(a,s,1,tr);self.update(b,t,1,tr)
   self.assertEqual(a.action(POSES,.04)[:12],b.action(POSES,.04)[:12])
if __name__=='__main__':unittest.main()
