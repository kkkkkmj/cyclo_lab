import unittest,tempfile,json,subprocess,sys
from pathlib import Path
import numpy as np,h5py
from analyze_contact_probe import verify
class PostmortemTests(unittest.TestCase):
 def test_strict_and_audit_are_separate(self):
  with tempfile.TemporaryDirectory() as tmp:
   d=Path(tmp);h=d/'data.hdf5';log=d/'teleop.log';status=d/'exit_status.txt';log.write_text('RECORD_SAVED demo_0 frames=2\n');status.write_text('DOCKER_EXEC_EXIT=0')
   with h5py.File(h,'w') as f:
    g=f.create_group('data/demo_0');g['actions']=np.zeros((2,15));g['obs/q']=np.zeros((2,25));g['states/q']=np.zeros((2,25))
   with self.assertRaises(RuntimeError):verify(h,log,status)
   r=verify(h,log,status,postmortem=True);self.assertTrue(r['verified']);self.assertFalse(r['app_finalization_confirmed'])
   with h5py.File(h,'a') as f:f['data/demo_0/states/q'][0,0]=np.nan
   self.assertFalse(verify(h,log,status,postmortem=True)['verified'])
 def test_contact_report_survives_missing_hdf5(self):
  with tempfile.TemporaryDirectory() as tmp:
   d=Path(tmp);(d/'teleop.log').write_text('no finalization');(d/'contact.jsonl').write_text(json.dumps({'event':'configuration','decimation':4,'frames':[]})+'\n'+json.dumps({'event':'preview','frame_id':1})+'\n')
   r=subprocess.run([sys.executable,str(Path(__file__).with_name('analyze_contact_probe.py')),'--run-dir',str(d),'--dataset',str(d/'missing.hdf5'),'--output',str(d/'out'),'--postmortem-readonly'],capture_output=True)
   self.assertEqual(r.returncode,1);s=json.loads((d/'out/summary.json').read_text());self.assertFalse(s['storage_verified']);self.assertFalse(s['app_finalization_confirmed']);self.assertEqual(len(s['preview_links']),1)
if __name__=='__main__':unittest.main()
