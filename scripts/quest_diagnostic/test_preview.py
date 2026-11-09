import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from preview import build_id, publish_preview, read_preview, stop_preview
from server import Receiver, Pairing, make_handler
from test_pairing import request
from test_control import sample


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def publish(self, captured=None):
        return publish_preview(self.root,b'jpeg bytes','run',7,{'head':{'shape':[244,244,3]}},{},captured)
    def test_generation_freshness_integrity_and_stop(self):
        self.publish(10)
        data,meta=read_preview(self.root,10.2)
        self.assertEqual(data,b'jpeg bytes');self.assertAlmostEqual(meta['age_ms'],200)
        self.assertEqual(read_preview(self.root,11)[1]['reason'],'frame_stale')
        (self.root/'preview.jpg').write_bytes(b'new generation racing reader')
        self.assertEqual(read_preview(self.root,10.2)[0],b'jpeg bytes')
        bundle=self.root/'preview.frame'
        bundle.write_bytes(bundle.read_bytes()+b'corrupt')
        self.assertEqual(read_preview(self.root,10.2)[1]['reason'],'publication_in_progress')
        stop_preview(self.root,'run')
        self.assertEqual(read_preview(self.root,10.2)[1]['reason'],'producer_stopped')
        self.assertTrue((self.root/'preview.jpg').exists())
    def test_commit_remains_consistent_during_legacy_pair_replacement(self):
        import preview
        self.publish(10)
        original=preview.atomic_write
        reads=[]
        def intercepted(path,data,**kwargs):
            original(path,data,**kwargs)
            payload,meta=read_preview(self.root,10.2)
            reads.append((payload,meta['frame_id'],meta['reason']))
        with patch('preview.atomic_write',side_effect=intercepted):
            publish_preview(self.root,b'next bytes','run',8,{}, {},10.1)
        self.assertTrue(all(x==(b'next bytes',8,'ok') for x in reads))

    def test_concurrent_commit_reader_never_observes_mixed_generation(self):
        from concurrent.futures import ThreadPoolExecutor
        self.publish(10)
        def writer():
            for i in range(100):publish_preview(self.root,str(i).encode(),'run',i+8,{}, {},10)
        with ThreadPoolExecutor(max_workers=1) as pool:
            job=pool.submit(writer)
            for _ in range(300):
                data,meta=read_preview(self.root,10.2)
                self.assertEqual(meta['reason'],'ok')
                self.assertIsNotNone(data)
            job.result()

    def test_missing_and_permission_failures_are_distinct(self):
        self.assertEqual(read_preview(None)[1]['reason'],'bridge_not_configured')
        self.assertEqual(read_preview(self.root)[1]['reason'],'file_missing')
        with patch('preview.Path.read_text',side_effect=PermissionError('denied')):
            self.assertEqual(read_preview(self.root)[1]['reason'],'permission_denied')
    def test_authenticated_http_image_and_failure_diagnostics(self):
        self.publish()
        r=Receiver(self.root);p=Pairing();_,token=p.redeem(p.code)
        h=make_handler(r,p,'https://192.168.10.116:8765');cookie=f'quest_session={token}'
        self.assertEqual(request(h,'/preview.jpg').status,401)
        response=request(h,'/preview.jpg',cookie=cookie)
        self.assertEqual(response.status,200);self.assertEqual(response.read(),b'jpeg bytes')
        self.assertEqual(response.getheader('Content-Type'),'image/jpeg')
        self.assertEqual(response.getheader('X-Preview-Frame'),'7')
        self.assertEqual(response.getheader('X-Preview-Run'),'run')
        self.assertEqual(response.getheader('Cache-Control'),'no-store')
        stop_preview(self.root,'run')
        response=request(h,'/preview.jpg',cookie=cookie)
        self.assertEqual(response.status,503)
        self.assertEqual(json.loads(response.read())['reason'],'producer_stopped')
        self.assertEqual(r.preview_http['sent'],1);self.assertEqual(r.preview_http['requests'],3)
        r.bridge_lock.close()
    def test_legacy_client_is_held_even_if_claiming_live_preview(self):
        r=Receiver();p=sample()['packet'];p.pop('client_protocol')
        r.accept(p,now=10)
        self.assertFalse(r.packet['preview_ok'])
        self.assertEqual(r.packet['preview_guard_reason'],'client_version_mismatch_or_missing')
    def test_decode_without_draw_and_wrong_run_are_not_confirmation(self):
        self.publish(10);r=Receiver(self.root);p=sample()['packet']
        p['preview_status']=dict(stage='decoded',run_id='run',drawn_frame_id='7')
        r.accept(p,now=10.1);self.assertFalse(r.packet['preview_ok'])
        p['seq']=1;p['preview_status'].update(stage='draw_submitted',run_id='wrong')
        r.accept(p,now=10.2);self.assertFalse(r.packet['preview_ok'])
        p['seq']=2;p['preview_status']['run_id']='run'
        r.accept(p,now=10.3);self.assertTrue(r.packet['preview_ok'])
        p['seq']=3;r.accept(p,now=11.1);self.assertFalse(r.packet['preview_ok'])
        r.bridge_lock.close()
    def test_page_is_read_on_request_and_stamped(self):
        r=Receiver();h=make_handler(r,Pairing(),'https://192.168.10.116:8765')
        response=request(h,'/');html=response.read().decode()
        self.assertIn(build_id(),html);self.assertNotIn('__QUEST_BUILD__',html)
        version=json.loads(request(h,'/version').read())
        self.assertEqual(version['server_build'],build_id())
        # Reading is deferred to GET, not captured by make_handler().
        with patch('server.Path.read_text',return_value='NEW __QUEST_BUILD__'):
            self.assertTrue(request(h,'/').read().startswith(b'NEW preview-v3-'))

if __name__=='__main__':unittest.main()
