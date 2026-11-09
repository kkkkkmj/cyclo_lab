import copy
import math
from pathlib import Path
import tempfile
import unittest
from bridge import read_input
from server import Receiver
from preview import build_id, publish_preview
from control import BoundedTeleop, qmul, qinv, quat, rotvec, norm
from test_receiver import packet

POSES={'left':([.35,.36,1.32],[0,0,0,1]),'right':([.35,-.36,1.32],[0,0,0,1])}

def sample():
    p=packet()
    p.update(client_protocol=3,client_build=build_id(),head_quaternion_xyzw=[0,0,0,1],preview_ok=True,reference_generation=0,safety_epoch=0)
    for i,h in enumerate(p['controllers'].values()):
        h.update(source_id=str(i),position=[0,1,0],reason='ok')
        h['buttons']=[dict(value=0,pressed=False,touched=False) for _ in range(6)]
    return dict(live=True,packet=p,server_id='server')


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.c=BoundedTeleop(POSES,1)
        self.s=sample();self.c.update(self.s)
    def squeeze(self,side='left',value=1):
        self.s['packet']['controllers'][side]['buttons'][1]['value']=value
    def test_forward_right_up_and_no_cross_arm_motion(self):
        self.squeeze();self.c.update(self.s)
        self.s['packet']['controllers']['left']['position']=[.04,1.04,-.04]
        self.c.update(self.s)
        for got,want in zip(self.c.targets['left'][0],[.36,.35,1.33]): self.assertAlmostEqual(got,want)
        self.assertEqual(self.c.targets['right'],POSES['right'])
    def test_rotation_basis_scale_and_sign(self):
        self.squeeze();self.c.update(self.s)
        self.s['packet']['controllers']['left']['quaternion_xyzw']=quat([0,.2,0])
        self.c.update(self.s)
        self.assertAlmostEqual(rotvec(self.c.targets['left'][1])[2],.1)
        # q and -q describe the same rotation.
        self.s['packet']['controllers']['left']['quaternion_xyzw']=[-v for v in quat([0,.2,0])]
        self.c.update(self.s)
        self.assertAlmostEqual(rotvec(self.c.targets['left'][1])[2],.1)
    def test_release_holds_and_reclutch_has_no_jump(self):
        self.squeeze();self.c.update(self.s)
        self.s['packet']['controllers']['left']['position'][2]=-.08;self.c.update(self.s)
        held=copy.deepcopy(self.c.targets)
        self.squeeze(value=0);self.c.update(self.s)
        self.s['packet']['controllers']['left']['position'][2]=-1;self.c.update(self.s)
        self.assertEqual(self.c.targets,held)
        self.squeeze();self.c.update(self.s)
        self.assertEqual(self.c.targets,held)
    def test_loss_reconnect_requires_release(self):
        self.squeeze();self.c.update(self.s)
        self.s['live']=False;self.c.update(self.s)
        self.s['live']=True;self.s['packet']['controllers']['left']['position'][2]=-.1
        self.c.update(self.s);self.assertEqual(self.c.targets,POSES)
        self.squeeze(value=0);self.c.update(self.s);self.squeeze();self.c.update(self.s)
        self.assertEqual(self.c.targets,POSES)
    def test_new_session_source_reference_server_and_epoch_rearm(self):
        for field in ('session','source_id','reference_generation','server_id','safety_epoch'):
            c=BoundedTeleop(POSES,1);s=sample();c.update(s)
            s['packet']['controllers']['left']['buttons'][1]['value']=1;c.update(s)
            if field=='server_id':s[field]='other'
            elif field=='source_id':s['packet']['controllers']['left'][field]='other'
            else:s['packet'][field]='other'
            s['packet']['controllers']['left']['position'][2]=-.1;c.update(s)
            self.assertEqual(c.targets,POSES)
            self.assertIsNone(c.basis)
    def test_hand_profile_never_controls(self):
        self.squeeze();self.c.update(self.s)
        self.s['packet']['controllers']['left'].update(profiles=['meta-fixed-hand'],position=[0,1,-.1])
        self.c.update(self.s);self.assertEqual(self.c.targets,POSES)
    def test_jump_and_preview_loss(self):
        self.squeeze();self.c.update(self.s)
        self.s['packet']['controllers']['left']['position'][2]=-1
        self.c.update(self.s);self.assertEqual(self.c.targets,POSES)
        self.assertEqual(self.c.states['left']['reason'],'controller_jump_release')
        self.s['packet']['preview_ok']=False;self.c.update(self.s)
        self.assertTrue(all(not v['ready'] for v in self.c.states.values()))
    def test_workspace_rotation_and_per_step_action_bounds(self):
        self.squeeze();self.c.update(self.s)
        for i in range(1,20):
            self.s['packet']['controllers']['left']['position'][2]=-.05*i
            self.s['packet']['controllers']['left']['quaternion_xyzw']=quat([0,.1*i,0])
            self.c.update(self.s)
        self.assertAlmostEqual(self.c.targets['left'][0][0]-.35,.05)
        self.assertAlmostEqual(norm(rotvec(self.c.targets['left'][1])),math.radians(15))
        action=self.c.action(POSES,.04)
        self.assertEqual(len(action),15)
        self.assertAlmostEqual(norm(action[:3])*.3,.002)
        self.assertAlmostEqual(norm(action[3:6])*.3,.02)
        self.assertEqual(action[12:],[1,1,1])
    def test_optional_grippers_only_with_clutch(self):
        c=BoundedTeleop(POSES,.8,True);c.update(self.s)
        self.s['packet']['controllers']['left']['buttons'][0]['value']=1
        c.update(self.s);self.assertEqual(c.grippers['left'],1)
        self.squeeze();c.update(self.s);c.update(self.s)
        self.assertEqual(c.grippers['left'],-1)
        self.s['live']=False;c.update(self.s);self.assertEqual(c.grippers['left'],-1)
        self.assertEqual(c.action(POSES,.04)[14],.8)
    def test_head_yaw_calibration(self):
        c=BoundedTeleop(POSES,1)
        self.s['packet']['head_quaternion_xyzw']=quat([0,math.pi/2,0]);c.update(self.s)
        self.squeeze();c.update(self.s)
        self.s['packet']['controllers']['left']['position'][0]=-.04;c.update(self.s)
        self.assertAlmostEqual(c.targets['left'][0][0],.36)
    def test_rebase_preserves_target(self):
        self.squeeze();self.c.update(self.s)
        self.s['packet']['controllers']['left']['position'][2]=-.04;self.c.update(self.s)
        held=copy.deepcopy(self.c.targets)
        self.squeeze(value=0);self.s['packet']['controllers']['right']['buttons'][5]['value']=1
        self.c.update(self.s);self.assertEqual(self.c.targets,held)
    def test_loop_stall_requires_release(self):
        self.squeeze();self.c.update(self.s);self.c.update(self.s,loop_gap=True)
        self.c.update(self.s);self.assertFalse(self.c.states['left']['ready'])


class BridgeTests(unittest.TestCase):
    def test_authored_hand_packet_is_sanitized(self):
        r=Receiver();p=packet();p['controllers']['left']['profiles']=['meta-fixed-hand']
        r.accept(p,now=10);h=r.snapshot(now=10.01)['packet']['controllers']['left']
        self.assertFalse(h['valid']);self.assertNotIn('position',h);self.assertEqual(h['buttons'],[])
    def test_atomic_bridge_timeout_and_loss_epoch(self):
        with tempfile.TemporaryDirectory() as directory:
            r=Receiver(directory);p=sample()['packet']
            publish_preview(directory,b'jpeg','run',1,{}, {},captured=10)
            p['preview_status']=dict(stage='draw_submitted',run_id='run',drawn_frame_id='1')
            r.accept(p,now=10)
            self.assertTrue(read_input(directory,now=10.1)['live'])
            self.assertFalse(read_input(directory,now=10.3)['live'])
            p['seq']=1;p['controllers']['left']['valid']=False;r.accept(p,now=10.1)
            p['seq']=2;p['controllers']['left']['valid']=True;r.accept(p,now=10.2)
            self.assertEqual(read_input(directory,now=10.21)['packet']['safety_epoch'],1)
            event=read_input(directory,now=10.21)['packet']['safety_event']
            self.assertEqual(event['seq'],1)
            self.assertIn('left',event['invalid_hands'])
            self.assertEqual(event['received_monotonic'],10.1)
            r.bridge_lock.close()

if __name__=='__main__':unittest.main()
