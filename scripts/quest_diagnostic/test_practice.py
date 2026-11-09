import argparse,copy,math,unittest
from types import SimpleNamespace
from control import BoundedTeleop,norm,sub
from practice_options import add_arguments,options,configure
from test_control import sample,POSES
from performance_probe import PerformanceProbe

class PracticeTests(unittest.TestCase):
    def make(self):
        parser=argparse.ArgumentParser();add_arguments(parser)
        return configure(BoundedTeleop(POSES,1,True),options(parser.parse_args(['--control-profile','practice'])))
    def test_defaults_bounds_and_clutch(self):
        c=self.make();s=sample();measured=copy.deepcopy(POSES);c.update(s,measured=measured)
        s['packet']['controllers']['right']['buttons'][1]['value']=1;c.update(s,measured=measured)
        # Move in small increments to avoid the unchanged controller jump guard.
        for i in range(1,31):
            s['packet']['controllers']['right']['position'][1]=1-i*.04
            c.update(s,measured=measured)
            self.assertLessEqual(norm(sub(c.targets['right'][0],measured['right'][0])),.04000001)
            measured=copy.deepcopy(c.targets)
        self.assertGreater(norm(sub(c.targets['right'][0],c.home['right'][0])),.05)
        self.assertGreaterEqual(c.targets['right'][0][2],1.02)
        self.assertLessEqual(norm(sub(c.targets['right'][0],c.home['right'][0])),.5500001)
        s['live']=False;c.update(s,measured=measured);s['live']=True;c.update(s,measured=measured)
        self.assertNotEqual(c.states['right']['reason'],'active')
    def test_reject_unbounded_nan_and_wrong_gain(self):
        p=argparse.ArgumentParser();add_arguments(p)
        for flag,value in [('--max-translation','9'),('--max-rotation-deg','181'),('--linear-speed','nan'),('--preview-hz','0')]:
            with self.assertRaises(ValueError):options(p.parse_args([flag,value]))
    def test_profiler_delegates_once_without_extra_calls(self):
        calls=[]
        def fn(*a,**k):calls.append((a,k));return 7
        env=SimpleNamespace(sim=SimpleNamespace(step=fn,render=fn),scene=SimpleNamespace(update=fn),
          observation_manager=SimpleNamespace(compute=fn),action_manager=SimpleNamespace(process_action=fn,apply_action=fn))
        probe=PerformanceProbe(env);probe.begin()
        self.assertEqual(env.sim.step(render=False),7);self.assertEqual(len(calls),1)
        self.assertEqual(probe.report()['calls']['physics_call'],1)
        probe.close();self.assertIs(env.sim.step,fn)

if __name__=='__main__':unittest.main()
