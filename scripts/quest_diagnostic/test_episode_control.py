"""CPU lifecycle/export contract tests with a fake manager, not a simulator/HDF5."""
import json
from types import SimpleNamespace as NS
import unittest
from diagnostic_recorder import DiagnosticRecorder, trim_complete_steps
from episode_control import EpisodeLifecycle, ButtonEdges, can_start
from test_control import sample, POSES
from control import BoundedTeleop

class EpisodeTests(unittest.TestCase):
    def test_explicit_start_finish_rearm(self):
        life=EpisodeLifecycle();s=sample()
        self.assertEqual(life.state,'WAITING');self.assertFalse(life.start(False))
        self.assertTrue(life.start(can_start(s)));self.assertFalse(life.start(True))
        self.assertTrue(life.finish('timeout'));self.assertEqual(life.state,'WAITING')
        s['packet']['controllers']['left']['buttons'][1]['value']=1
        self.assertFalse(can_start(s))
        c=BoundedTeleop(POSES,1);c.update(s)
        self.assertTrue(all(not h['ready'] for h in c.states.values()))
        s['packet']['controllers']['left']['buttons'][1]['value']=0
        self.assertTrue(life.start(can_start(s)));self.assertEqual(life.number,2)
    def test_start_guards(self):
        for change in ('live','preview','valid','hand','mapping'):
            s=sample()
            if change=='live':s['live']=False
            elif change=='preview':s['packet']['preview_ok']=False
            elif change=='valid':s['packet']['controllers']['left']['valid']=False
            elif change=='hand':s['packet']['controllers']['left']['profiles']=['meta-fixed-hand']
            else:s['packet']['controllers']['left']['mapping']=''
            self.assertFalse(can_start(s),change)
    def test_button_edges_and_disconnect(self):
        s=sample();edges=ButtonEdges();self.assertEqual(edges.commands(s),[])
        s['packet']['controllers']['left']['buttons'][4]['pressed']=True
        self.assertEqual(edges.commands(s),['n']);self.assertEqual(edges.commands(s),[])
        s['live']=False;self.assertEqual(edges.commands(s),[])
        s['live']=True;self.assertEqual(edges.commands(s),[])
        s['packet']['controllers']['left']['buttons'][4]['pressed']=False
        edges.commands(s)
        s['packet']['controllers']['right']['buttons'][4]['pressed']=True
        self.assertEqual(edges.commands(s),['s'])

class Group(dict):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.attrs={}

class FakeManager:
    def __init__(self):
        self.cfg=NS(export_in_record_pre_reset=False)
        self.file=Group(data=Group());self.ep=NS(data={},success=False,seed=None)
        self._dataset_file_handler=NS(_hdf5_file_stream=self.file,demo_count=0,flush=lambda:None,close=lambda:None)
    def get_episode(self,i):return self.ep
    def reset(self,ids=None):self.ep=NS(data={},success=False,seed=None)
    def export_episodes(self,ids=None):
        handler=self._dataset_file_handler
        self.file['data'][f'demo_{handler.demo_count}']=Group(actions=list(self.ep.data['actions']))
        handler.demo_count+=1;self.reset()
    def record_pre_reset(self,ids,force_export_or_skip=None):
        self.export_episodes(ids)

class RecorderTests(unittest.TestCase):
    def setup_recorder(self):
        m=FakeManager();terms={'success':False,'time_out':False}
        env=NS(recorder_manager=m,termination_manager=NS(active_terms=list(terms),get_term=lambda k:[terms[k]]))
        meta=dict(operator='operator_B',scenario_id='batch02_toast_001',manifest_sha256='test',seed=7)
        return DiagnosticRecorder(env,meta),m,terms
    def test_manual_short_failed_episode_and_no_duplicate(self):
        r,m,terms=self.setup_recorder();r.start(1,{'bread_shelf':'measured'},7)
        m.ep.data.update(actions=[[0]*15],obs={'test':[0]},states={'test':[0]});r.finish('manual_stop');r.finish('exit')
        self.assertEqual(m._dataset_file_handler.demo_count,1)
        ep=m.file['data']['demo_0'];self.assertFalse(ep.attrs['success'])
        self.assertFalse(ep.attrs['task_success_observed']);self.assertEqual(ep.attrs['seed'],7)
        info=json.loads(ep.attrs['toast_episode_metadata'])
        self.assertEqual(info['end_reason'],'manual_stop');self.assertEqual(info['applied_reset_poses'],{'bread_shelf':'measured'})
    def test_terminal_export_preserves_observed_success_but_not_success_demo(self):
        r,m,terms=self.setup_recorder();r.start(1,{},7)
        m.ep.data.update(actions=[[0]*15]*2,obs={'test':[0,0]},states={'test':[0,0]});m.ep.success=True;terms['success']=True
        m.export_episodes([0]);r.finish('exit')
        ep=m.file['data']['demo_0'];self.assertFalse(ep.attrs['success']);self.assertTrue(ep.attrs['task_success_observed'])
        self.assertEqual(json.loads(ep.attrs['toast_episode_metadata'])['end_reason'],'environment_termination')
        self.assertFalse(r.active);self.assertEqual(r.saved,1)
    def test_interrupted_step_trim(self):
        data=dict(initial_state={'pose':[9]},actions=[1,2,3],obs={'camera':[1,2,3]},
                  states={'pose':[1,2]},timing={'time':[1,2,3]})
        self.assertEqual(trim_complete_steps(data),2)
        self.assertEqual(data['actions'],[1,2]);self.assertEqual(data['initial_state']['pose'],[9])
        self.assertEqual(trim_complete_steps({'actions':[1]}),0)
    def test_empty_or_inactive_reset_does_not_export(self):
        r,m,_=self.setup_recorder();m.export_episodes([0]);r.start(1,{},7);r.finish('exit')
        self.assertEqual(m._dataset_file_handler.demo_count,0)

if __name__=='__main__':unittest.main()
