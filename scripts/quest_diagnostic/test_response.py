import argparse,copy,math,unittest
from control import BoundedTeleop,norm,sub
from practice_options import add_arguments,options,configure
from tracking_monitor import TrackingMonitor
from test_control import sample,POSES

class ResponseTests(unittest.TestCase):
    def controller(self,extra=()):
        p=argparse.ArgumentParser();add_arguments(p)
        return configure(BoundedTeleop(POSES,1,True),options(p.parse_args(['--control-profile','practice',*extra])))
    def move(self,c):
        s=sample();c.update(s,measured=POSES)
        s['packet']['controllers']['left']['buttons'][1]['value']=1;c.update(s,measured=POSES)
        s['packet']['controllers']['left']['position'][2]=-.1;c.update(s,measured=POSES)
        return s
    def test_disable_flags_and_diagnostic_preservation(self):
        p=argparse.ArgumentParser();add_arguments(p)
        c=self.controller(['--no-home-limits','--no-speed-limits','--no-target-lead','--workspace','off'])
        self.assertIsNone(c.max_translation);self.assertIsNone(c.max_rotation);self.assertIsNone(c.linear_speed)
        s=self.move(c);self.assertAlmostEqual(c.action(POSES,.04)[0],.1/.3)
        for flag in ['--no-home-limits','--no-speed-limits','--no-target-lead']:
            with self.assertRaises(ValueError):options(p.parse_args([flag]))
        default=options(p.parse_args([]));self.assertEqual(default['position_scale'],.25);self.assertEqual(default['max_translation'],.05)
    def test_release_cancels_pending_goal_and_reclutch_no_jump(self):
        c=self.controller(['--no-speed-limits']);s=self.move(c)
        self.assertGreater(c.action(POSES,.04)[0],0)
        h=s['packet']['controllers']['left'];h['buttons'][0]['value']=.75;c.update(s,measured=POSES)
        held=c.grippers['left'];h['buttons'][1]['value']=0;h['buttons'][0]['value']=0
        c.update(s,measured=POSES)
        self.assertEqual(c.action(POSES,.04)[:12],[0.]*12);self.assertEqual(c.grippers['left'],held)
        self.assertEqual(c.targets['left'],POSES['left'])
        h['position'][2]=-1;h['buttons'][1]['value']=1;h['buttons'][0]['value']=.25
        c.update(s,measured=POSES)
        self.assertEqual(c.targets['left'],POSES['left']);self.assertEqual(c.grippers['left'],.5)
        self.assertEqual(c.action(POSES,.04)[:12],[0.]*12)
    def test_stale_preview_and_loop_loss_cancel_pending(self):
        for loss in ['live','preview','loop']:
            c=self.controller();s=self.move(c)
            if loss=='live':s['live']=False
            if loss=='preview':s['packet']['preview_ok']=False
            c.update(s,loop_gap=loss=='loop',measured=POSES)
            self.assertEqual(c.action(POSES,.04)[:12],[0.]*12)
            s['live']=True;s['packet']['preview_ok']=True;c.update(s,measured=POSES)
            self.assertNotEqual(c.states['left']['reason'],'active')
    def test_raw_target_audit_is_pre_limit_and_cleared_on_loss(self):
        c=self.controller(['--no-home-limits','--no-speed-limits','--workspace','off','--max-target-lead','.04'])
        s=self.move(c)
        self.assertGreater(norm(sub(c.raw_targets['left'][0],POSES['left'][0])),.04)
        self.assertAlmostEqual(norm(sub(c.targets['left'][0],POSES['left'][0])),.04)
        s['packet']['safety_epoch']=1;s['packet']['preview_ok']=False
        c.update(s,measured=POSES)
        self.assertEqual(c.raw_targets,{})
        self.assertEqual(c.reference_changes,['safety_epoch'])
        self.assertEqual(c.action(POSES,.04)[:12],[0.]*12)

    def test_trigger_five_levels_are_continuous(self):
        c=self.controller();s=self.move(c)
        for v in [0,.25,.5,.75,1]:
            s['packet']['controllers']['left']['buttons'][0]['value']=v
            c.update(s,measured=POSES);a=c.action(POSES,.04)
            self.assertEqual(a[12],1-2*v);self.assertAlmostEqual((1-a[12])*.5*1.1,v*1.1)
    def test_tracking_transient_progress_stall_and_hard_gap(self):
        c=self.controller();self.move(c);monitor=TrackingMonitor(2)
        for i in range(5):self.assertIsNone(monitor.check(c,POSES,i*.3))
        self.assertEqual(monitor.check(c,POSES,2.1),('left','tracking_stall'))
        monitor=TrackingMonitor(2)
        for i in range(15):
            measured=copy.deepcopy(POSES);measured['left'][0][0]+=.003*i
            self.assertIsNone(monitor.check(c,measured,i*.3))
        c.targets['left'][0][0]+=1
        self.assertEqual(monitor.check(c,POSES,8),('left','tracking_discontinuity'))
    def test_moving_target_does_not_immediately_trigger_8cm_abort(self):
        c=self.controller();self.move(c);monitor=TrackingMonitor(.5)
        for i in range(10):
            c.targets['left'][0][0]+=.005
            self.assertIsNone(monitor.check(c,POSES,i*.1))

if __name__=='__main__':unittest.main()
