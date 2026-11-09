"""Exercise the real public GET handlers without sockets/GPU or a running server."""
import io
import json
import re
import tempfile
import unittest
from server import Receiver, Pairing, make_handler
from preview import build_id


class PageRoutesTests(unittest.TestCase):
    def test_base_address_and_scripts_are_versioned_and_uncached(self):
        with tempfile.TemporaryDirectory() as directory:
            receiver = Receiver(bridge_dir=directory)
            handler = make_handler(receiver, Pairing(), 'https://192.168.10.116:8765')
            def get(path):
                request = handler.__new__(handler)
                request.path = path
                request.headers = {}
                request.wfile = io.BytesIO()
                response = dict(headers={})
                request.send_response = lambda code: response.update(code=code)
                request.send_header = lambda k, v: response['headers'].update({k: v})
                request.end_headers = lambda: None
                request.do_GET()
                self.assertEqual(response['code'], 200)
                self.assertEqual(response['headers']['Cache-Control'], 'no-store')
                self.assertEqual(response['headers']['X-Quest-Server-Build'], build_id())
                return request.wfile.getvalue()
            try:
                html = get('/').decode()
                self.assertNotIn('__QUEST_BUILD__', html)
                scripts = re.findall(r'<script src="([^"]+)"', html)
                self.assertEqual(len(scripts), 3)
                for script in scripts:
                    self.assertIn('?v='+build_id(), script)
                    self.assertTrue(get(script))
                version = json.loads(get('/version'))
                self.assertEqual(version['server_build'], build_id())
                self.assertEqual(version['disk_build'], build_id())
            finally:
                receiver.bridge_lock.close()

if __name__ == '__main__':
    unittest.main()
