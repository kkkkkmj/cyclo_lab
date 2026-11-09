"""Offline protocol tests; deliberately no GPU, network or Isaac imports."""
import copy
import unittest
from server import Receiver


def packet(seq=0, session='test'):
    hand = dict(valid=True, position=[1, 2, 3], quaternion_xyzw=[0, 0, 0, 1],
                profiles=['meta-quest-touch-plus'], mapping='xr-standard', buttons=[dict(value=.5, pressed=True, touched=True)], axes=[0, 0])
    return dict(session=session, seq=seq, client_ms=123.0, visibility='visible',
                controllers=dict(left=hand, right=copy.deepcopy(hand)))


class ReceiverTests(unittest.TestCase):
    def test_valid_pose_and_buttons(self):
        r = Receiver(); r.accept(packet(), now=10)
        s = r.snapshot(now=10.1)
        self.assertTrue(s['live'])
        self.assertEqual(s['packet']['controllers']['left']['position'], [1, 2, 3])
        self.assertTrue(s['packet']['controllers']['right']['buttons'][0]['pressed'])

    def test_timeout_clears_pose_and_buttons(self):
        r = Receiver(); r.accept(packet(), now=10)
        s = r.snapshot(now=10.251)
        self.assertFalse(s['live'])
        for h in s['packet']['controllers'].values():
            self.assertFalse(h['valid']); self.assertEqual(h['buttons'], [])
            self.assertNotIn('position', h)

    def test_hidden_and_ended(self):
        for visibility in ('hidden', 'visible-blurred', 'ended'):
            r = Receiver(); p = packet(); p['visibility'] = visibility
            r.accept(p, now=10)
            self.assertFalse(r.snapshot(now=10.01)['packet']['controllers']['left']['valid'])

    def test_missing_tracking(self):
        r = Receiver(); p = packet(); p['controllers']['left'] = dict(valid=False)
        r.accept(p, now=10)
        self.assertFalse(r.snapshot(now=10.01)['packet']['controllers']['left']['valid'])

    def test_reordered_packet(self):
        r = Receiver(); r.accept(packet(5), now=10)
        for seq in (5, 4):
            with self.assertRaises(ValueError): r.accept(packet(seq), now=10.01)
        self.assertEqual(r.snapshot(now=10.1)['received_packets'], 1)

    def test_reconnection_and_session_collision(self):
        r = Receiver(); r.accept(packet(20), now=10)
        with self.assertRaises(ValueError): r.accept(packet(session='new'), now=10.1)
        r.accept(packet(session='new'), now=11.1)
        self.assertEqual(r.snapshot(now=11.11)['packet']['seq'], 0)

    def test_malformed_inputs(self):
        for key, value in [('position', [float('nan'), 0, 0]), ('quaternion_xyzw', [0, 0, 0, 0]),
                           ('mapping', ''), ('buttons', [dict(value=2, pressed=True, touched=False)]),
                           ('axes', [float('inf')])]:
            p = packet(); p['controllers']['left'][key] = value
            with self.assertRaises(ValueError): Receiver().accept(p, now=10)

    def test_snapshot_does_not_mutate_received_packet(self):
        r = Receiver(); p = packet(); r.accept(p, now=10)
        p['controllers']['left']['position'][0] = 99
        self.assertEqual(r.snapshot(now=10.1)['packet']['controllers']['left']['position'][0], 1)
        r.snapshot(now=11)
        self.assertTrue(r.packet['controllers']['left']['valid'])


if __name__ == '__main__':
    unittest.main()
