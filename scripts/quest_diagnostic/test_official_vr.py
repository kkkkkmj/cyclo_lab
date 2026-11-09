import copy,unittest
from official_vr_control import OfficialController
from test_control import sample,POSES
class Tests(unittest.TestCase):
 def setUp(self):
  self.s=sample();self.c=OfficialController(POSES);self.c.update(self.s,measured=POSES)
 def update(self,squeeze=1,trigger=0):
  h=self.s['packet']['controllers']['right'];h['buttons'][1]['value']=squeeze;h['buttons'][0]['value']=trigger
  self.c.update(self.s,measured=POSES)
 def test_binary(self):
  for t,want in [(0,1),(.25,1),(.499,1),(.5,-1),(.75,-1),(1,-1)]:
   self.update(trigger=t);a=self.c.action(POSES,.05);self.assertEqual(len(a),7);self.assertEqual(a[-1],want)
 def test_reclutch_freezes_actual(self):
  self.update();self.s['packet']['controllers']['right']['position'][2]-=.04;self.update()
  self.assertNotEqual(self.c.action(POSES,.05)[:6],[0.]*6)
  self.update(0);self.assertEqual(self.c.action(POSES,.05)[:6],[0.]*6)
  self.s['packet']['controllers']['right']['position'][2]-=.5;self.update()
  self.assertEqual(self.c.action(POSES,.05)[:6],[0.]*6)
 def test_stale_release(self):
  self.update(trigger=1);self.s['live']=False;self.update();self.assertEqual(self.c.action(POSES,.05),[0.]*6+[-1.])
  self.s['live']=True;self.update();self.assertEqual(self.c.states['right']['reason'],'release_then_squeeze')
 def test_preview(self):
  self.update();self.s['packet']['preview_ok']=False;self.update();self.assertEqual(self.c.states['right']['reason'],'preview_not_live')
 def test_left_not_action(self):
  self.s['packet']['controllers']['left']['buttons'][1]['value']=1
  self.s['packet']['controllers']['left']['position'][0]+=.1
  self.c.update(self.s,measured=POSES);self.assertEqual(self.c.action(POSES,.05),[0.]*6+[1.])
if __name__=='__main__':unittest.main()
