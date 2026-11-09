"""CPU integration: pinned EpisodeData/HDF5 writer, fake physics, real MP4 codec."""
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import patch

import h5py
import imageio_ffmpeg
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/tools'))
from toast_recording_metadata import create_diagnostic, finalize_diagnostic, inspect_diagnostic, TASK
from diagnostic_recorder import DiagnosticRecorder
from episode_control import EpisodeLifecycle, capture_termination_results
from episode_video import EpisodeVideo, CAMERAS

# Load the actual pinned dataset package without importing the simulator.
package=ModuleType('pinned_datasets')
package.__path__=[str(ROOT/'third_party/IsaacLab/source/isaaclab/isaaclab/utils/datasets')]
sys.modules[package.__name__]=package
from pinned_datasets.episode_data import EpisodeData
from pinned_datasets.hdf5_dataset_file_handler import HDF5DatasetFileHandler


class FakeManager:
    def __init__(self, directory, terms):
        self.cfg=SimpleNamespace(export_in_record_pre_reset=False)
        self._dataset_file_handler=HDF5DatasetFileHandler()
        self._dataset_file_handler.create(str(directory/'dataset.hdf5'),TASK)
        self.terms=terms
        self.reset()

    def reset(self, ids=None):self.ep=EpisodeData()
    def get_episode(self, i):return self.ep
    def record_post_step(self):pass
    def record_pre_reset(self, ids, force_export_or_skip=True):
        self.ep.success=self.terms['success']
        self.export_episodes(ids)
    def export_episodes(self, ids=None):
        self.ep.pre_export()
        self._dataset_file_handler.write_episode(self.ep)
        self._dataset_file_handler.flush()
        self.reset()


def state(value):
    return dict(articulation={'robot':{'root_pose':torch.full((7,),float(value))}},
                rigid_object={'bread_0':{'root_pose':torch.full((7,),float(value))}},
                toast_cycle={'timer':torch.tensor([float(value)])})


class SessionTest(unittest.TestCase):
    def test_lifecycle_labels_alignment_and_decode(self):
        # Keep artifacts when requested; mkdtemp guarantees no existing recording is touched.
        directory=Path(tempfile.mkdtemp(prefix='quest-recording-cpu-',dir=os.environ.get('QUEST_TEST_ROOT','/tmp')))
        print('CPU_ARTIFACTS',directory)
        manifest=ROOT/'scenario_delivery_base/manifest.json'
        entries=json.loads(manifest.read_text())['scenarios']
        entry=next(e for e in entries if e['scenario_group']=='operator_B_1' and e['group_index']==1)
        out,meta=create_diagnostic(directory/'run',manifest,entry['operator'],entry['id'],entry['operator_index'],1)
        meta['timing']=dict(control_dt=.04,physics_dt=.01,decimation=4,render_interval=4)
        terms={'success':False,'time_out':False}
        manager=FakeManager(out,terms)
        env=SimpleNamespace(recorder_manager=manager,termination_manager=SimpleNamespace(
            active_terms=list(terms),get_term=lambda name:[terms[name]]))
        life=EpisodeLifecycle()
        configs={name:SimpleNamespace(func=lambda name=name:[terms[name]]) for name in terms}
        def compute():
            return any([cfg.func()[0] for cfg in configs.values()])
        env.termination_manager.compute=compute
        env.termination_manager.get_term_cfg=lambda name:configs[name]
        capture_termination_results(env.termination_manager,life)
        recorder=DiagnosticRecorder(env,meta,life)
        results=[]
        # Startup/WAITING reset must not write an episode.
        manager.record_pre_reset([0])
        for number,reason,success in [(1,'manual_stop',False),(2,'success',True),
                                      (3,'tracking_stall',False),(4,'KeyboardInterrupt',False),
                                      (5,'environment_termination',False)]:
            manager.record_pre_reset([0])
            manager.ep.add('initial_state',state(number))
            self.assertTrue(life.start(True))
            recorder.start(number,{},1)
            for i in range(3):
                manager.ep.add('actions',torch.full((15,),float(number)))
                manager.ep.add('processed_actions',torch.full((15,),float(number)))
                manager.ep.add('obs',{name:torch.full((244,244,3),i*60,dtype=torch.uint8) for name in CAMERAS})
                manager.ep.add('states',state(number))
                manager.ep.add('timing/wall_monotonic',torch.tensor([100.+i*.061],dtype=torch.float64))
                manager.ep.add('timing/simulation_time',torch.tensor([i*.04]))
                manager.record_post_step()
            terms['success']=success
            terms['time_out']=reason=='environment_termination'
            env.termination_manager.compute()
            if success or terms['time_out']:
                manager.record_pre_reset([0]) # automatic export before reset
            else:
                if reason=='KeyboardInterrupt':
                    manager.ep.add('actions',torch.zeros(15)) # incomplete step trimmed
                    manager.ep.add('timing/wall_monotonic',torch.tensor([101.]))
                recorder.finish(reason)
            automatic=success or terms['time_out']
            terms['success']=terms['time_out']=False
            life.finish('environment_termination' if automatic else reason,life.pending_result if automatic else None)
            results.append(life.result)
            self.assertFalse(recorder.active)
        # Start then stop without any step: distinct sidecar, no invalid MP4 or HDF group.
        manager.ep.add('initial_state',state(6))
        recorder.start(6,{},1);recorder.finish('manual_stop')
        self.assertFalse((out/'episode_000006/video.mp4').exists())
        recorder.close();finalize_diagnostic(out,meta)
        report=inspect_diagnostic(out/'dataset.hdf5')
        self.assertEqual(len(report['episodes']),5)
        with h5py.File(out/'dataset.hdf5','r') as f:
            for i,ep in enumerate(f['data'].values()):
                self.assertEqual(bool(ep.attrs['success']),i==1)
                self.assertEqual(len(ep['actions']),3)
                np.testing.assert_array_equal(ep['actions'][:],np.full((3,15),i+1))
                info=json.loads(ep.attrs['toast_episode_metadata'])
                self.assertEqual(info['end_reason'],['manual_stop','success','tracking_stall','KeyboardInterrupt','timeout'][i])
                self.assertEqual(info['scenario_group'],'operator_B_1')
                self.assertEqual(info['episode_result']['label'],results[i]['label'])
                self.assertEqual(info['episode_result']['success'],results[i]['success'])
                self.assertEqual(json.loads((out/ep.attrs['episode_id']/'episode.json').read_text()),info)
                self.assertTrue(info['code_version']['commit'])
                rows=[json.loads(line) for line in (out/ep.attrs['episode_id']/'frames.jsonl').read_text().splitlines()]
                self.assertAlmostEqual(rows[1]['observation_sample_interval_s'],.061)
                self.assertGreaterEqual(rows[1]['capture_interval_s'],0.)
                video=out/ep.attrs['video_file']
                reader=imageio_ffmpeg.read_frames(str(video),pix_fmt='rgb24')
                header=next(reader);decoded=list(reader)
                self.assertEqual(header['size'],(768,256));self.assertEqual(len(decoded),3)
        (directory/'inspection.json').write_text(json.dumps(report,indent=2)+'\n')
        loader=HDF5DatasetFileHandler();loader.open(str(out/'dataset.hdf5'))
        self.assertEqual(loader.load_episode('demo_1','cpu').get_next_action().shape,(15,))
        loader.close()
        with self.assertRaises(FileExistsError):create_diagnostic(out,manifest,entry['operator'],entry['id'],entry['operator_index'],1)

    def test_backpressure_and_encoder_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            # No worker consumption: bounded queue drops instead of blocking the producer.
            with patch.object(EpisodeVideo,'_encode',lambda self:None):
                video=EpisodeVideo(Path(tmp)/'full','full',.04,capacity=1)
                frames={k:np.zeros((244,244,3),dtype=np.uint8) for k in CAMERAS}
                for i in range(10):video.submit(frames,i,float(i),i*.04)
                report=video.close()
                self.assertEqual(report['queue_dropped'],9)
                self.assertEqual(report['dropped'],10)
            with patch('episode_video.imageio_ffmpeg.write_frames',side_effect=OSError('encoder failed')):
                video=EpisodeVideo(Path(tmp)/'error','error',.04)
                video.submit(frames,0,0.,0.)
                report=video.close()
                self.assertIn('encoder failed',report['error'])
                self.assertFalse(report['playable'])


if __name__=='__main__':unittest.main()
