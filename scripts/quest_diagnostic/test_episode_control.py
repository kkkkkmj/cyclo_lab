"""CPU lifecycle/export contract tests with a fake manager, not a simulator/HDF5."""
import json
import tempfile
from types import SimpleNamespace as NS
import unittest
from diagnostic_recorder import DiagnosticRecorder, trim_complete_steps
from episode_control import EpisodeLifecycle, ButtonEdges, can_start, episode_result, capture_termination_results
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

class ResultTests(unittest.TestCase):
    def test_pre_reset_capture_without_recording_and_approved_start(self):
        life=EpisodeLifecycle();life.start(True)
        terms={'success':True,'bread_dropping':False,'time_out':False}
        returned=object()
        configs={name:NS(func=lambda name=name:[terms[name]]) for name in terms}
        def compute():
            for cfg in configs.values():cfg.func()
            return returned
        manager=NS(active_terms=list(terms),compute=compute,get_term_cfg=lambda k:configs[k])
        capture_termination_results(manager,life)
        self.assertIs(manager.compute(),returned)
        # Simulate automatic reset clearing every term before env.step returns.
        terms.update(dict.fromkeys(terms,False))
        life.finish('environment_termination',life.pending_result)
        self.assertEqual(life.result['label'],'SUCCESS');self.assertEqual(life.state,'WAITING')
        self.assertFalse(life.start(False));self.assertEqual(life.result['label'],'SUCCESS')
        self.assertFalse(life.finish('manual_stop'));self.assertTrue(life.result['success'])
        self.assertTrue(life.start(True));self.assertIsNone(life.result);self.assertIsNone(life.pending_result)

    def test_pinned_compute_last_term_cache_does_not_hide_failure_or_reuse_success(self):
        import ast
        import torch
        from pathlib import Path
        from types import MethodType
        path=Path(__file__).resolve().parents[2]/'third_party/IsaacLab/source/isaaclab/isaaclab/managers/termination_manager.py'
        tree=ast.parse(path.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='TerminationManager')
        node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='compute')
        scope={'torch':torch};exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),scope)
        terms={'time_out':True,'bread_dropping':True,'success':True}
        configs={name:NS(func=lambda env,name=name:torch.tensor([terms[name]]),params={},time_out=name=='time_out') for name in terms}
        m=NS(_env=None,_term_cfgs=list(configs.values()),active_terms=list(terms),
             _truncated_buf=torch.zeros(1,dtype=torch.bool),_terminated_buf=torch.zeros(1,dtype=torch.bool),
             _term_dones=torch.zeros((1,3),dtype=torch.bool),get_term_cfg=lambda k:configs[k])
        m.compute=MethodType(scope['compute'],m)
        life=EpisodeLifecycle();life.start(True);capture_termination_results(m,life)
        self.assertTrue(m.compute().item());self.assertEqual(m._term_dones.tolist(),[[False,False,True]])
        self.assertEqual(life.pending_result['reason'],'bread_dropping')
        self.assertEqual(life.pending_result['termination_terms'],terms)
        terms.update(dict.fromkeys(terms,False));self.assertFalse(m.compute().item())
        self.assertIsNone(life.pending_result) # stale cached success must not end the next step

    def test_priority(self):
        for terms,reason,success in [({'success':True},'success',True),
            ({'success':True,'time_out':True},'success',True),
            ({'success':True,'bread_dropping':True},'bread_dropping',False),
            ({'success':True,'bread_dropping':True,'time_out':True},'bread_dropping',False),
            ({'time_out':True},'timeout',False)]:
            result=episode_result(terms=terms)
            self.assertEqual((result['reason'],result['success']),(reason,success))
        for reason,label in [('manual_stop','STOPPED'),('tracking_stall','TRACKING STALL')]:
            life=EpisodeLifecycle();life.start(True);life.finish(reason)
            self.assertEqual(life.result['label'],label)
            self.assertFalse(episode_result(reason,{'success':True})['success'])

class Group(dict):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.attrs={}

class FakeManager:
    def __init__(self):
        self.cfg=NS(export_in_record_pre_reset=False)
        self.file=Group(data=Group());self.ep=NS(data={},success=False,seed=None)
        self._dataset_file_handler=NS(_hdf5_file_stream=self.file,demo_count=0,flush=lambda:None,close=lambda:None)
    def record_post_step(self):pass
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
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        meta=dict(record_directory=tmp.name,timing={'control_dt':.04},operator='operator_B',scenario_id='batch02_toast_001',manifest_sha256='test',seed=7)
        return DiagnosticRecorder(env,meta),m,terms
    def test_manual_short_failed_episode_and_no_duplicate(self):
        r,m,terms=self.setup_recorder();r.start(1,{'bread_shelf':'measured'},7)
        m.ep.data.update(actions=[[0]*15],obs={'test':[0]},states={'test':[0]});r.finish('manual_stop');r.finish('exit')
        self.assertEqual(m._dataset_file_handler.demo_count,1)
        ep=m.file['data']['demo_0'];self.assertFalse(ep.attrs['success'])
        self.assertFalse(ep.attrs['task_success_observed']);self.assertEqual(ep.attrs['seed'],7)
        info=json.loads(ep.attrs['toast_episode_metadata'])
        self.assertEqual(info['end_reason'],'manual_stop');self.assertEqual(info['applied_reset_poses'],{'bread_shelf':'measured'})
    def test_terminal_export_preserves_actual_success(self):
        r,m,terms=self.setup_recorder();r.start(1,{},7)
        m.ep.data.update(actions=[[0]*15]*2,obs={'test':[0,0]},states={'test':[0,0]});m.ep.success=True;terms['success']=True
        m.export_episodes([0]);r.finish('exit')
        ep=m.file['data']['demo_0'];self.assertTrue(ep.attrs['success']);self.assertTrue(ep.attrs['task_success_observed'])
        self.assertEqual(json.loads(ep.attrs['toast_episode_metadata'])['end_reason'],'success')
        self.assertFalse(r.active);self.assertEqual(r.saved,1)
    def test_stop_and_failure_override_success_labels(self):
        for reason,extra,expected in [('manual_stop',{},False),('tracking_stall',{},False),
                                     (None,{'bread_dropping':True},False),
                                     (None,{'time_out':True},True)]:
            r,m,terms=self.setup_recorder();r.start(1,{},7)
            m.ep.data.update(actions=[[0]*15],obs={'test':[0]},states={'test':[0]})
            terms['success']=True;terms.update(extra);r.env.termination_manager.active_terms=list(terms)
            if reason:r.finish(reason)
            else:m.export_episodes([0])
            ep=m.file['data']['demo_0'];info=json.loads(ep.attrs['toast_episode_metadata'])
            self.assertEqual(bool(ep.attrs['success']),expected)
            self.assertEqual(info['episode_result']['success'],expected)
            self.assertEqual(info['task_success_observed'],expected)
            sidecar=json.loads((r.video.directory/'episode.json').read_text())
            self.assertEqual(sidecar,info)

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
