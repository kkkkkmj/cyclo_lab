import copy
import unittest
from control import BoundedTeleop
from episode_control import EpisodeLifecycle, can_start
from display_status import display_status, start_blockers
from test_control import sample, POSES

class StatusTests(unittest.TestCase):
    def test_start_explanation_matches_existing_predicate(self):
        base = sample()
        variants = [base]
        for side in ('left', 'right'):
            for field, value in [('valid', False), ('profiles', ['meta-fixed-hand']),
                                 ('mapping', 'none'), ('buttons', [])]:
                s = copy.deepcopy(base); s['packet']['controllers'][side][field] = value; variants.append(s)
            s = copy.deepcopy(base); s['packet']['controllers'][side]['buttons'][1]['value'] = .2; variants.append(s)
        s = copy.deepcopy(base); s['live'] = False; s['age_ms'] = 251; variants.append(s)
        s = copy.deepcopy(base); s['packet']['preview_ok'] = False; variants.append(s)
        for s in variants:
            before = copy.deepcopy(s)
            self.assertEqual(not start_blockers(s), can_start(s))
            self.assertEqual(before, s)
        self.assertIn('input_stale', start_blockers(variants[-2]))

    def test_both_hands_rearm_after_start_and_loss(self):
        s=sample(); life=EpisodeLifecycle(); c=BoundedTeleop(POSES,1)
        self.assertTrue(can_start(s)); life.start(can_start(s)); c.update(s)
        self.assertEqual([v['reason'] for v in c.states.values()],['ready','ready'])
        for h in s['packet']['controllers'].values(): h['buttons'][1].update(value=1,pressed=True)
        c.update(s); c.update(s)
        self.assertTrue(all(h['active'] for h in display_status(s,c,life)['hands'].values()))
        s['packet']['preview_ok']=False;c.update(s)
        s['packet']['preview_ok']=True;c.update(s)
        self.assertTrue(all(v['reason']=='release_then_squeeze' for v in c.states.values()))
        for h in s['packet']['controllers'].values(): h['buttons'][1].update(value=0,pressed=False)
        c.update(s)
        for h in s['packet']['controllers'].values(): h['buttons'][1].update(value=1,pressed=True)
        c.update(s);c.update(s)
        self.assertTrue(all(h['active'] for h in display_status(s,c,life)['hands'].values()))

    def test_status_survives_atomic_preview_publication(self):
        import tempfile
        from preview import publish_preview, read_preview
        s=sample(); c=BoundedTeleop(POSES,1); life=EpisodeLifecycle()
        status=display_status(s,c,life)
        with tempfile.TemporaryDirectory() as root:
            publish_preview(root,b'jpeg-test','run',1,{},dict(teleop=status),captured=10)
            data,meta=read_preview(root,now=10.2)
            self.assertEqual(data,b'jpeg-test')
            self.assertEqual(meta['timings']['teleop'],status)
            self.assertIsNone(read_preview(root,now=11.1)[0])

    def test_pressed_is_not_active_and_loss_reports_controller_verdict(self):
        s = sample(); c = BoundedTeleop(POSES, 1); life = EpisodeLifecycle()
        c.update(s); s['packet']['controllers']['left']['buttons'][1].update(value=1, pressed=True)
        def status(): return display_status(s,c,life)
        self.assertTrue(status()['hands']['left']['squeeze_pressed'])
        self.assertFalse(status()['hands']['left']['active'])
        life.start(True); c.update(s) # anchored, not yet active
        self.assertFalse(status()['hands']['left']['active'])
        c.update(s)
        self.assertTrue(status()['hands']['left']['active'])
        self.assertFalse(display_status(s,c,life,True)['hands']['left']['active'])
        s['live']=False; c.update(s)
        self.assertEqual(status()['hands']['left']['control_reason'], 'input_not_live')
        self.assertFalse(status()['hands']['left']['active'])

if __name__=='__main__': unittest.main()
