import unittest
import numpy as np
from replay_validation import compare_states,resolve_episode_indices

class ValidationTests(unittest.TestCase):
    def states(self,a,b):
        return {'articulation':{'robot':{'q':np.asarray(a)}}},{'articulation':{'robot':{'q':np.asarray(b)[None]}}}
    def test_tolerance(self):
        for value,expected in [(0,True),(.009,True),(.01,True),(.010001,False)]:
            self.assertEqual(compare_states(*self.states([0],[value]),0)[0],expected)
    def test_nan_inf_both_sides(self):
        for value in (np.nan,np.inf,-np.inf):
            for a,b in (([value],[0]),([0],[value]),([value],[value])):
                self.assertFalse(compare_states(*self.states(a,b),0)[0])
    def test_shapes_same_count_and_keys(self):
        self.assertFalse(compare_states(*self.states([[1,2]],[1,2]),0)[0])
        a,b=self.states([1],[1]);b['articulation']['robot']['extra']=np.zeros((1,1))
        self.assertFalse(compare_states(a,b,0)[0])
        self.assertFalse(compare_states({}, {},0)[0])
    def test_whole_tensor_transfer_and_progress(self):
        class Tensor:
            calls=0
            def __init__(self,v):self.v=v
            def __getitem__(self,i):return Tensor(self.v[i])
            def detach(self):return self
            def cpu(self):Tensor.calls+=1;return self
            def numpy(self):return self.v
        a,b=self.states(np.zeros(10000),np.zeros(10000))
        a['articulation']['robot']['q']=Tensor(a['articulation']['robot']['q'])
        b['articulation']['robot']['q']=Tensor(b['articulation']['robot']['q'])
        logs=[];self.assertTrue(compare_states(a,b,0,logs.append)[0])
        self.assertEqual(Tensor.calls,2);self.assertEqual(len(logs),4)
    def test_bounded_detail(self):
        a,b=self.states(np.zeros(100000),np.ones(100000))
        ok,msg=compare_states(a,b,0);self.assertFalse(ok);self.assertLess(len(msg),1000)
    def test_exact_names_vs_list_order(self):
        names=['demo_0','demo_1','demo_10','demo_8']
        self.assertEqual(resolve_episode_indices(names,selected_names=['demo_8']),[3])
        self.assertEqual(resolve_episode_indices(names,[2]),[2])
        for indices,selected in [([-1],None),([8],None),(None,['missing']),([0],['demo_8'])]:
            with self.assertRaises(ValueError):resolve_episode_indices(names,indices,selected)


class SingleEnvironmentTests(unittest.TestCase):
    def test_explicit_env_axis_contract(self):
        a={'articulation':{'robot':{'q':np.zeros((1,25))}}}
        b={'articulation':{'robot':{'q':np.zeros((1,25))}}}
        self.assertTrue(compare_states(a,b,0,dataset_has_single_env_axis=True)[0])
        for shape in ((25,),(2,25),(1,1,25),(1,5,5)):
            a['articulation']['robot']['q']=np.zeros(shape)
            self.assertFalse(compare_states(a,b,0,dataset_has_single_env_axis=True)[0],shape)
        a['articulation']['robot']['q']=np.zeros((1,25))
        b['articulation']['robot']['q']=np.zeros((2,25))
        self.assertFalse(compare_states(a,b,0,dataset_has_single_env_axis=True)[0])
    def test_metrics_and_nonfinite(self):
        a={'rigid_object':{'bread':{'root_pose':np.zeros((1,7))}}}
        b={'rigid_object':{'bread':{'root_pose':np.zeros((1,7))}}}
        b['rigid_object']['bread']['root_pose'][0,3]=.02
        metrics={};self.assertFalse(compare_states(a,b,0,dataset_has_single_env_axis=True,metrics=metrics)[0])
        self.assertEqual(metrics['rigid_object/bread/root_pose']['max_abs'],.02)
        b['rigid_object']['bread']['root_pose'][0,3]=np.nan
        self.assertFalse(compare_states(a,b,0,dataset_has_single_env_axis=True)[0])


def actual_dataset_loader():
    # Import the vendored datasets package directly: actual loader/actual EpisodeData,
    # without importing the Isaac app or replacing either class with a fake.
    import importlib.util,sys
    from pathlib import Path
    folder=Path(__file__).resolve().parents[3]/'third_party/IsaacLab/source/isaaclab/isaaclab/utils/datasets'
    name='_replay_test_actual_datasets'
    if name not in sys.modules:
        spec=importlib.util.spec_from_file_location(name,folder/'__init__.py',submodule_search_locations=[str(folder)])
        module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return sys.modules[name].HDF5DatasetFileHandler


class ActualLoaderTests(unittest.TestCase):
    def test_actual_hdf5_loader_get_next_state(self):
        import tempfile,json
        import h5py,torch
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fixture.hdf5'
            with h5py.File(path,'w') as f:
                data=f.create_group('data');data.attrs['env_args']=json.dumps({'env_name':'cpu_fixture'})
                episode=data.create_group('demo_8')
                for key,width in [('joint_position',25),('root_pose',7),('root_velocity',6)]:
                    episode.create_dataset('states/articulation/robot/'+key,data=np.zeros((3,width),dtype=np.float32))
            handler=actual_dataset_loader()();handler.open(str(path))
            try:
                episode=handler.load_episode('demo_8','cpu')
                saved=episode.get_next_state()
                runtime={'articulation':{'robot':{k:torch.zeros((1,w)) for k,w in [('joint_position',25),('root_pose',7),('root_velocity',6)]}}}
                self.assertEqual(tuple(saved['articulation']['robot']['joint_position'].shape),(1,25))
                self.assertFalse(compare_states(saved,runtime,0)[0]) # reproduces previous bug
                self.assertTrue(compare_states(saved,runtime,0,dataset_has_single_env_axis=True)[0])
                runtime['articulation']['robot']['root_pose'][0,2]=.02
                metrics={};self.assertFalse(compare_states(saved,runtime,0,dataset_has_single_env_axis=True,metrics=metrics)[0])
                self.assertAlmostEqual(metrics['articulation/robot/root_pose']['max_abs'],.02,places=7)
            finally:handler.close()


class SupervisorTests(unittest.TestCase):
    def test_real_child_exit(self):
        import sys
        from replay_checked import run_command
        self.assertEqual(run_command([sys.executable,'-c','import os; os._exit(7)']),7)


class VerdictTests(unittest.TestCase):
    def test_failure_and_missing_verdict_survive_child_exit_zero(self):
        import sys
        from replay_checked import run_command
        self.assertEqual(run_command([sys.executable,'-c','import os; os._exit(0)'],True),2)
        prefix='import os,json; from pathlib import Path; p=Path(os.environ["CYCLO_REPLAY_RESULT"]); '
        def command(status,mismatches):
            return [sys.executable,'-c',prefix+f'p.write_text(json.dumps(dict(schema=1,run_id=os.environ["CYCLO_REPLAY_RUN_ID"],status="{status}",checked=95,expected=95,mismatched={mismatches}))); os._exit(0)']
        self.assertEqual(run_command(command('failed',95),True),1)
        self.assertEqual(run_command(command('completed',95),True),1)
        self.assertEqual(run_command(command('validated',0),True),0)
    def test_stale_run_id_and_incomplete_counts(self):
        from replay_outcome import effective_exit_code
        result=dict(schema=1,run_id='old',status='completed',checked=95,expected=95,mismatched=0)
        self.assertEqual(effective_exit_code(0,result,'new',True),2)
        result.update(run_id='new',checked=94)
        self.assertEqual(effective_exit_code(0,result,'new',True),1)


class PlateAuditTests(unittest.TestCase):
    def test_hook_does_not_add_steps_and_restores_on_error(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from replay_plate_audit import step_with_first_physics_checkpoint
        calls=[];sim=SimpleNamespace(step=lambda **kw:calls.append(kw))
        original=sim.step
        env=SimpleNamespace(sim=sim)
        def step(action):
            for _ in range(4):sim.step(render=False)
            return action
        env.step=step
        with patch('replay_plate_audit.plate_checkpoint') as audit:
            self.assertEqual(step_with_first_physics_checkpoint(env,123),123)
            self.assertEqual(len(calls),4);audit.assert_called_once_with(env,'after_first_physics_step',raw_only=True)
        self.assertIs(sim.step,original)
        def broken(action):sim.step(render=False);raise RuntimeError('test')
        env.step=broken
        with patch('replay_plate_audit.plate_checkpoint'):
            with self.assertRaises(RuntimeError):step_with_first_physics_checkpoint(env,0)
        self.assertIs(sim.step,original)
    def test_actual_worker_verdict_survives_immediate_zero_exit(self):
        import sys
        from pathlib import Path
        from replay_checked import run_command
        folder=str(Path(__file__).resolve().parent)
        code=f"import sys,os; sys.path.insert(0,{folder!r}); from replay_outcome import record_outcome; record_outcome('failed',checked=95,mismatched=95,expected=95); os._exit(0)"
        self.assertEqual(run_command([sys.executable,'-c',code],True),1)

if __name__=='__main__':unittest.main()
