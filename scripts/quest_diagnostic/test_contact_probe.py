import unittest,tempfile,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from contact_probe import relative_angle,value,ContactProbe
from analyze_contact_probe import verify
import h5py

class Tests(unittest.TestCase):
    def test_frames_axes_sign(self):
        parent=Rotation.from_euler('xyz',[.4,-.8,1.2]);j0=Rotation.from_euler('xyz',[.2,2.3,-.7]);j1=Rotation.from_euler('xyz',[-.5,.3,2.7])
        def wq(r):q=r.as_quat();return [q[3],*q[:3]]
        for axis in 'XYZ':
            for angle in (-2.18,-1.845,-.001,0,.6,1.1):
                child=parent*j0*Rotation.from_rotvec(np.eye(3)['XYZ'.index(axis)]*angle)*j1.inv()
                out=relative_angle([0,0,0,*parent.as_quat()],[0,0,0,*child.as_quat()],wq(j0),wq(j1),axis)
                self.assertAlmostEqual(out['angle_rad'],angle,places=10);self.assertLess(out['off_axis_residual_rad'],1e-7)
    def test_missing(self):
        self.assertIsNone(value(lambda:np.array([np.nan]))['value'])
        self.assertIn('ZeroDivisionError',value(lambda:1/0)['reason'])
    def test_storage(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);h=d/'data.h5';log=d/'log';status=d/'status'
            log.write_text('RECORD_FINALIZED: {}');status.write_text('DOCKER_EXEC_EXIT=0')
            with h5py.File(h,'w') as f:f.create_group('data')
            self.assertFalse(verify(h,log,status)['verified'])
            with h5py.File(h,'a') as f:
                for name in ('demo_0','demo_1'):
                    g=f['data'].create_group(name);g['actions']=np.zeros((3,15));g['states/robot/q']=np.zeros((3,25));g['obs/q']=np.zeros((3,25))
            self.assertTrue(verify(h,log,status)['verified'])
            status.write_text('DOCKER_EXEC_EXIT=1')
            with self.assertRaises(RuntimeError):verify(h,log,status)
    def test_substep_guard_source(self):
        # Integration guards: diagnostics are scoped to explicit env.step, no diagnostic setters.
        source=Path(__file__).with_name('contact_probe.py').read_text()
        self.assertIn('int(env._sim_step_counter)!=self.last_counter',source)
        self.assertNotIn('.set_joint',source);self.assertNotIn('.step(',source)
if __name__=='__main__':unittest.main()
