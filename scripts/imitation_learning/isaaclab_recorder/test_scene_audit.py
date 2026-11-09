"""CPU evidence handling tests; USD/PhysX GPU reads still require Isaac runtime."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from replay_scene_audit import TimelineProbe,emit
from compare_plate_audits import compare,differences

class AuditTests(unittest.TestCase):
    def test_null_is_not_replaced_by_zero(self):
        self.assertEqual(differences({'mass':None},{'mass':None}),[])
        self.assertTrue(differences({'mass':None},{'mass':0}))
        self.assertTrue(differences({'status':'unavailable'},{'status':'queried','value':0}))
    def test_probe_calls_original_once_and_restores(self):
        calls=[]
        sim=NS(**{k:(lambda *a,_name=k,**kw:calls.append(_name)) for k in ('step','forward','render')})
        originals=dict(vars(sim));probe=TimelineProbe(NS(sim=sim))
        sim.render();sim.render();sim.forward();sim.step(render=False)
        self.assertEqual(calls,['render','render','forward','step'])
        self.assertEqual(probe.counts,dict(step=1,forward=1,render=2))
        probe.close()
        for k,v in originals.items():self.assertIs(getattr(sim,k),v)
    def test_record_replay_checkpoint_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);record=root/'record';replay=root/'replay';record.mkdir();replay.mkdir()
            for directory,stage,velocity in [(record,'after_reset_before_physics',[0]*6),(replay,'after_reset_to_before_physics',[0]*6),
                (record,'after_first_control_step',[0]*6),(replay,'after_first_control_step',[0,0,0,.02,0,0])]:
                env=NS(_replay_audit_dir=str(directory),_replay_audit_episode='demo_0')
                emit(env,'plate_checkpoint',dict(stage=stage,physx_com_velocity_world=velocity))
            report=compare(record/'audit.jsonl',replay/'audit.jsonl','demo_0')
            self.assertEqual(report['checkpoints']['after_reset_before_physics']['max_abs'],0)
            self.assertEqual(report['checkpoints']['after_first_control_step']['max_abs'],.02)
            self.assertEqual(report['checkpoints']['after_first_physics_step']['status'],'missing')
            self.assertEqual(report['property_differences'],'missing snapshot')

if __name__=='__main__':unittest.main()
