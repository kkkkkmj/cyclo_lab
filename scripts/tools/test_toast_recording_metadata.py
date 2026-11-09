"""CPU contract tests only. No simulation, headset, or HDF5 write is performed."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import toast_recording_metadata as m
from view_make_toast_scenario import build_parser, resolve_selection


class RecordingContract(unittest.TestCase):
    def make(self, root):
        args=build_parser().parse_args(['--operator','operator_B','--scenario_index','1'])
        sid=resolve_selection(args)
        self.assertEqual(sid,'toast_v20261108_041')
        return m.create_diagnostic(root/'new',m.DEFAULT_MANIFEST,args.operator,sid,args.scenario_index,seed=7)

    def test_recording_arguments_and_start_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=SimpleNamespace(record_dir=Path(tmp)/'new',operator='operator_B',scenario_index=1,
                                 record_seconds=8,enable_grippers=False,preview_only=False)
            m.validate_recording_args(args)
            manual=copy.copy(args);manual.enable_grippers=True;manual.record_seconds=0
            m.validate_recording_args(manual)
            for key,value in [('operator',None),('scenario_index',None),('record_seconds',-1),
                              ('record_seconds',3601),('record_seconds',float('nan')),
                              ('preview_only',True),('record_dir',Path(tmp))]:
                bad=copy.copy(args);setattr(bad,key,value)
                with self.assertRaises(ValueError):m.validate_recording_args(bad)
        states={s:{'reason':'ready'} for s in ('left','right')}
        self.assertTrue(m.ready_to_record({'live':True,'packet':{'preview_ok':True}},states))
        for snapshot in ({'live':False,'packet':{'preview_ok':True}}, {'live':True,'packet':{'preview_ok':False}}, {}):
            self.assertFalse(m.ready_to_record(snapshot,states))
        states['left']['reason']='preview_not_live'
        self.assertFalse(m.ready_to_record({'live':True,'packet':{'preview_ok':True}},states))

    def test_b_first_snapshot_and_portable_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            out,meta=self.make(Path(tmp))
            self.assertEqual((out/'manifest.json').read_bytes(),m.DEFAULT_MANIFEST.read_bytes())
            self.assertFalse(meta['diagnostic_success'])
            other=Path(tmp)/'different name';out.rename(other)
            sid,path=m.scenario_for_replay(other,meta,m.TASK)
            self.assertEqual(sid,'toast_v20261108_041');self.assertEqual(Path(path),other/'manifest.json')
            self.assertEqual(meta['initial_static_rack_pose'],next(e for e in json.loads((other/'manifest.json').read_text())['scenarios'] if e['id']==sid)['poses']['bread_shelf'])

    def test_existing_output_and_bad_operator_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            out,meta=self.make(Path(tmp));before=(out/'manifest.json').read_bytes()
            with self.assertRaises(FileExistsError):self.make(Path(tmp))
            self.assertEqual((out/'manifest.json').read_bytes(),before)
            with self.assertRaises(ValueError):m.create_diagnostic(Path(tmp)/'bad',m.DEFAULT_MANIFEST,'operator_A','toast_v20261108_041',1)
            self.assertFalse((Path(tmp)/'bad').exists())

    def test_hash_task_id_rack_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            out,meta=self.make(Path(tmp))
            for key,value in [('task','wrong'),('scenario_id','missing'),('manifest_file','../manifest.json'),
                              ('operator','operator_A'),('initial_static_rack_pose',{}),('manifest_sha256','bad')]:
                bad=copy.deepcopy(meta);bad[key]=value
                with self.assertRaises(ValueError):m.scenario_for_replay(out,bad,m.TASK)
            (out/'manifest.json').write_bytes((out/'manifest.json').read_bytes()+b' ')
            with self.assertRaises(ValueError):m.scenario_for_replay(out,meta,m.TASK)

    def test_replay_cfg_and_timing_with_fake_hdf5_header(self):
        # Explicitly a mock header, not evidence of an HDF5 recording.
        with tempfile.TemporaryDirectory() as tmp:
            out,meta=self.make(Path(tmp));meta['timing']=dict(physics_dt=.01,decimation=4,render_interval=4,control_dt=.04)
            class Header:
                attrs={m.ATTRIBUTE:json.dumps(meta)}
                def __enter__(self):return self
                def __exit__(self,*args):pass
            cfg=SimpleNamespace(sim=SimpleNamespace(dt=.01,render_interval=4),decimation=4)
            with patch.dict('sys.modules',{'h5py':SimpleNamespace(File=lambda *args:Header())}):
                m.configure_replay(out/'dataset.hdf5',cfg,m.TASK)
                self.assertEqual(cfg.scenario_id,'toast_v20261108_041');self.assertEqual(cfg.seed,7)
                self.assertEqual(cfg.scenario_manifest,str(out/'manifest.json'))
                cfg.decimation=2
                with self.assertRaises(ValueError):m.configure_replay(out/'dataset.hdf5',cfg,m.TASK)

    def test_diagnostic_marker_without_metadata_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            class Header:
                attrs={}
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def __getitem__(self,key):return {'demo_0':SimpleNamespace(attrs={'diagnostic':True})}
            with patch.dict('sys.modules',{'h5py':SimpleNamespace(File=lambda *args:Header())}):
                with self.assertRaises(ValueError):m.configure_replay(Path(tmp)/'dataset.hdf5',SimpleNamespace(),m.TASK)


if __name__=='__main__':unittest.main()
