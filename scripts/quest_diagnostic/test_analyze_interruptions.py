import json
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np
from analyze_interruptions import analyze, align, joint_summary, load_episodes, read_log


def decision(tick, before='RUNNING', after='RUNNING'):
    h=dict(valid=True,input_reason='ok',control_reason='active',squeeze=1.,raw_squeeze={'value':1.},
           tracking_error_m=.12,position=[tick,0,0])
    return dict(event='decision',tick_monotonic=tick,phase_before=before,action=[0.]*15,
        teleop=dict(episode_state=after,recording=after=='RUNNING',hands={'left':h,'right':h},preview={}),
        input_snapshot={'packet':{'seq':int(tick)}},measured_before_step={'right':[[tick,0,0],[0,0,0,1]]},step_ms=80)


class InterruptionAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.log=self.root/'decisions.jsonl~';self.dataset=self.root/'dataset.hdf5'
        self.events=[dict(event='begin',run_id='r',scenario_id='s',seed=1),
            decision(10,'WAITING'),decision(11,after='WAITING'),decision(20,'WAITING'),decision(21)]
        self.write_log()
        self.write_hdf(False)
    def tearDown(self):self.temp.cleanup()
    def write_log(self):self.log.write_text(''.join(json.dumps(x)+'\n' for x in self.events))
    def write_hdf(self,two):
        with h5py.File(self.dataset,'w') as f:
            for ep,ticks in enumerate(([10,11],[20,21]) if two else ([10,11],)):
                e=f.create_group('data/demo_'+str(ep));e.attrs['toast_episode_metadata']=json.dumps(dict(episode_number=ep+1,scenario_id='s',seed=1))
                e.create_dataset('actions',data=np.zeros((2,15)))
                e.create_dataset('timing/wall_monotonic',data=np.array(ticks)[:,None])
                e.create_dataset('states/articulation/robot/joint_position',data=np.full((2,3),ep+1.))
                e.create_dataset('states/articulation/robot/joint_velocity',data=np.full((2,3),ep+2.))
    def test_unsaved_second_episode_remains_unknown_and_sources_unchanged(self):
        s=analyze(self.log,self.dataset,self.root/'out')
        self.assertEqual(s['verified_hdf_frames'],2)
        self.assertEqual(len(s['unmatched_action_decisions']),2)
        unknown=[x for x in s['large_tracking_errors'] if x['log_episode']==2]
        self.assertTrue(unknown)
        self.assertTrue(all(x['joints']['joint_min'] is None and x['joints']['status']=='확인 불가' for x in unknown))
        self.assertTrue(s['provenance']['unchanged'])
        report = (self.root/'out'/'candidates.md').read_text()
        self.assertIn('HDF joints', report)
        self.assertNotRegex(report, r'[\uac00-\ud7a3]')
    def test_multiple_episodes_keep_local_frame_ids_and_separate_ranges(self):
        self.write_hdf(True);s=analyze(self.log,self.dataset,self.root/'out')
        self.assertEqual(s['verified_hdf_frames'],4)
        self.assertEqual(len(s['log_episodes']),2)
        for x in s['large_tracking_errors']:
            self.assertEqual(x['joints']['joint_min'],[float(x['log_episode'])]*3)
            self.assertTrue(all(r['episode']=='demo_'+str(x['log_episode']-1) for r in x['joints']['references']))
    def test_empty_joint_range_returns_unknown_not_zero(self):
        x=joint_summary([],{},{});self.assertEqual(x['status'],'확인 불가');self.assertIsNone(x['joint_min'])
    def test_empty_dataset_no_gripper_samples_does_not_crash(self):
        with h5py.File(self.dataset,'w') as f:f.create_group('data')
        s=analyze(self.log,self.dataset,self.root/'out');self.assertEqual(s['verified_hdf_frames'],0)
    def test_truncated_last_line_is_reported(self):
        with self.log.open('ab') as f:f.write(b'{"event":')
        _,_,s=read_log(self.log);self.assertEqual(s['invalid_lines'][0]['line'],6);self.assertFalse(s['final_newline'])
    def test_duplicate_log_timestamp_never_selects_arbitrary_row(self):
        self.events.append(decision(10));self.write_log()
        ev,d,_=read_log(self.log);links,reports=align(d,load_episodes(self.dataset),{'r':self.events[0]})
        self.assertEqual(len(links),1);self.assertEqual(reports['demo_0']['issues'][0]['reason'],'duplicate_log_tick')
    def test_action_mismatch_and_nonfinite_joint_are_not_matched_as_normal(self):
        with h5py.File(self.dataset,'r+') as f:
            f['data/demo_0/actions'][0,0]=1
            f['data/demo_0/states/articulation/robot/joint_position'][1,0]=float('nan')
        s=analyze(self.log,self.dataset,self.root/'out')
        self.assertEqual(s['hdf_episodes']['demo_0']['issues'][0]['reason'],'action_mismatch')
        first=s['large_tracking_errors'][0]['joints'];self.assertIsNone(first['joint_min'])
        self.assertIn('nonfinite_joint_state',first['missing_reasons'])
    def test_partial_match_keeps_coverage_and_only_reduces_real_rows(self):
        self.events[2]['action'][0]=2.;self.write_log()
        s=analyze(self.log,self.dataset,self.root/'out')
        j=s['large_tracking_errors'][0]['joints']
        self.assertEqual(j['status'],'부분 확인');self.assertEqual(j['matched_samples'],1)
        self.assertEqual(j['requested_samples'],2);self.assertEqual(j['joint_min'],[1.]*3)
    def test_empty_episode_and_wrong_timing_shape_are_reported(self):
        with h5py.File(self.dataset,'w') as f:
            e=f.create_group('data/demo_0');e.create_dataset('actions',data=np.empty((0,15)))
            e.create_dataset('timing/wall_monotonic',data=np.empty((0,1)))
            e=f.create_group('data/demo_1');e.create_dataset('actions',data=np.zeros((2,15)))
            e.create_dataset('timing/wall_monotonic',data=np.array([10,11]))
        s=analyze(self.log,self.dataset,self.root/'out');self.assertEqual(s['verified_hdf_frames'],0)
        self.assertTrue(s['hdf_episodes']['demo_1']['issues'])
    def test_near_timestamp_is_not_rounded_or_interpolated(self):
        self.events[1]['tick_monotonic']+=1e-7;self.write_log()
        s=analyze(self.log,self.dataset,self.root/'out')
        self.assertEqual(s['verified_hdf_frames'],1)
        self.assertEqual(s['hdf_episodes']['demo_0']['issues'][0]['reason'],'log_tick_missing')
    def test_episode_metadata_mismatch_is_not_attached(self):
        with h5py.File(self.dataset,'r+') as f:
            f['data/demo_0'].attrs['toast_episode_metadata']=json.dumps({'episode_number':9})
        s=analyze(self.log,self.dataset,self.root/'out')
        self.assertEqual(s['verified_hdf_frames'],0)
        self.assertEqual(s['hdf_episodes']['demo_0']['issues'][0]['reason'],'episode_number_mismatch')

    def test_output_is_never_overwritten(self):
        out=self.root/'out';out.mkdir();(out/'sentinel').write_text('keep')
        with self.assertRaises(FileExistsError):analyze(self.log,self.dataset,out)
        self.assertEqual((out/'sentinel').read_text(),'keep')

if __name__=='__main__':unittest.main()
