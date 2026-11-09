import tempfile,json,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from toast_audit_lifecycle import *

class Lifecycle(unittest.TestCase):
    def test_nonzero_exit_preserves_physics_json_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);atomic_json(p/'s.json',dict(stability='FAIL',reset='PASS',runs=[{'detail':123}]))
            before=(p/'s.json').read_bytes();atomic_json(p/'s.lifecycle.json',dict(status='ERROR',cleanup_errors=['weakref']))
            r=process_record(p,'s',1)
            self.assertEqual((p/'s.json').read_bytes(),before)
            self.assertEqual(r['process_status'],'ERROR');self.assertEqual(r['result_json_status'],'VALID')
    def test_missing_and_corrupt_results_explicit_and_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);r=process_record(p,'s',0);self.assertEqual(r['result_json_status'],'MISSING')
            (p/'s.json').write_bytes(b'{broken');r=process_record(p,'s',1)
            self.assertEqual(r['result_json_status'],'CORRUPT');self.assertEqual((p/'s.json').read_bytes(),b'{broken')
    def test_logged_weakref_error_is_not_normal_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);atomic_json(p/'s.json',dict(stability='PASS',reset='PASS'));atomic_json(p/'s.lifecycle.json',dict(status='PASS'))
            (p/'s.log').write_text('ReferenceError: weakly-referenced object no longer exists')
            self.assertEqual(process_record(p,'s',0)['process_status'],'ERROR')
    def test_normal_exit_needs_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);atomic_json(p/'s.json',dict(stability='PASS',reset='PASS'));atomic_json(p/'s.lifecycle.json',dict(status='PASS'))
            self.assertEqual(process_record(p,'s',0)['process_status'],'PASS')
    def test_detach_before_env_close_and_idempotent_registry(self):
        calls=[];sensor=NS(_clear_callbacks=lambda:calls.append('unsubscribe'),_rep_registry={'rgb':[NS(detach=lambda p:calls.append('detach'))]},_render_product_paths=['rp'])
        def close():
            self.assertEqual(sensor._rep_registry,{});calls.append('env.close')
        env=NS(scene=NS(sensors={'camera':sensor}),close=close)
        self.assertEqual(close_safely(env,NS(close=lambda:calls.append('app.close'))),[])
        self.assertEqual(calls,['unsubscribe','detach','env.close','app.close'])
    def test_close_failure_still_closes_app(self):
        calls=[]
        def bad():raise ReferenceError('weakly-referenced object no longer exists')
        errors=close_safely(NS(scene=NS(sensors={}),close=bad),NS(close=lambda:calls.append('app')))
        self.assertEqual(errors[0]['stage'],'env.close');self.assertEqual(calls,['app'])
if __name__=='__main__':unittest.main()
