"""Authentication, HTTP routing and real TLS tests without listening sockets."""
import io
import json
import ssl
import tempfile
import unittest
from http.client import HTTPResponse
from pathlib import Path
from server import Pairing, Receiver, make_handler
from tls import prepare_certificate


class MemorySocket:
    def __init__(self, data=b''):
        self.input = io.BytesIO(data)
        self.output = io.BytesIO()
    def makefile(self, *args, **kwargs):
        return self.input
    def sendall(self, data):
        self.output.write(data)
    def settimeout(self, value):
        pass


def request(handler, path, method='GET', body=None, cookie=None, origin='https://192.168.10.116:8765'):
    data = json.dumps(body).encode() if body is not None else b''
    headers = [f'{method} {path} HTTP/1.0', 'Host: 192.168.10.116:8765',
               f'Origin: {origin}', f'Content-Length: {len(data)}']
    if cookie:
        headers.append(f'Cookie: {cookie}')
    sock = MemorySocket(('\r\n'.join(headers)+'\r\n\r\n').encode()+data)
    handler(sock, ('192.168.10.125', 10000), None)
    response = HTTPResponse(MemorySocket(sock.output.getvalue()))
    response.begin()
    return response


class PairingTests(unittest.TestCase):
    def setUp(self):
        self.now = 10
        self.p = Pairing(clock=lambda: self.now)

    def test_code_format_single_use_and_cookie_expiry(self):
        self.assertRegex(self.p.code, r'^\d{6}$')
        status, token = self.p.redeem(self.p.code)
        self.assertEqual(status, 200)
        self.assertTrue(self.p.authorized(f'quest_session={token}'))
        self.assertEqual(self.p.redeem(self.p.code)[0], 410)
        self.now += 28800
        self.assertFalse(self.p.authorized(f'quest_session={token}'))

    def test_expiry(self):
        self.now += 300
        self.assertEqual(self.p.redeem(self.p.code)[0], 410)

    def test_global_attempt_limit_and_manual_rotation(self):
        for _ in range(4):
            self.assertEqual(self.p.redeem('wrong')[0], 401)
        self.assertEqual(self.p.redeem('wrong')[0], 429)
        self.assertEqual(self.p.redeem(self.p.code)[0], 429)
        self.p.rotate()
        self.assertEqual(self.p.redeem(self.p.code)[0], 200)

    def test_old_and_malformed_auth_rejected(self):
        for cookie in (None, '', 'token=old', 'quest_session=forged', 'bad[=cookie'):
            self.assertFalse(self.p.authorized(cookie))

    def test_routes_and_secure_cookie(self):
        handler = make_handler(Receiver(), self.p, 'https://192.168.10.116:8765')
        self.assertEqual(request(handler, '/').status, 200)
        self.assertEqual(request(handler, '/status?token=old').status, 401)
        self.assertEqual(request(handler, '/input', 'POST', {}).status, 401)
        self.assertEqual(request(handler, '/pair', 'POST', {'code': self.p.code}, origin='https://other').status, 403)
        self.assertEqual(self.p.attempts, 0)
        r = request(handler, '/pair', 'POST', {'code': self.p.code})
        self.assertEqual(r.status, 200)
        cookie = r.getheader('Set-Cookie')
        for flag in ('Secure', 'HttpOnly', 'SameSite=Strict', 'Max-Age=28800'):
            self.assertIn(flag, cookie)
        self.assertEqual(request(handler, '/status', cookie=cookie.split(';')[0]).status, 200)
        self.assertEqual(request(handler, '/pair', 'POST', {'code': self.p.code}).status, 410)

    def test_http_attempt_limit(self):
        handler = make_handler(Receiver(), self.p, 'https://192.168.10.116:8765')
        for _ in range(4):
            self.assertEqual(request(handler, '/pair', 'POST', {'code': 'bad'}).status, 401)
        self.assertEqual(request(handler, '/pair', 'POST', {'code': 'bad'}).status, 429)


class TLSTests(unittest.TestCase):
    def test_certificate_persistence_and_authenticated_handshake(self):
        with tempfile.TemporaryDirectory() as directory:
            cert, key = prepare_certificate('192.168.10.116', Path(directory))
            original = (cert.read_bytes(), key.read_bytes())
            self.assertEqual(prepare_certificate('192.168.10.116', directory), (cert, key))
            self.assertEqual(original, (cert.read_bytes(), key.read_bytes()))
            self.assertEqual(key.stat().st_mode & 0o777, 0o600)
            server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            server_context.load_cert_chain(cert, key)
            client_context = ssl.create_default_context(cafile=str(cert))
            ci, co, si, so = [ssl.MemoryBIO() for _ in range(4)]
            client = client_context.wrap_bio(ci, co, server_hostname='192.168.10.116')
            server = server_context.wrap_bio(si, so, server_side=True)
            complete = set()
            for _ in range(20):
                for name, endpoint in [('client', client), ('server', server)]:
                    try:
                        endpoint.do_handshake()
                        complete.add(name)
                    except ssl.SSLWantReadError:
                        pass
                if co.pending: si.write(co.read())
                if so.pending: ci.write(so.read())
                if len(complete) == 2: break
            self.assertEqual(complete, {'client', 'server'})
            self.assertIn(client.version(), ('TLSv1.2', 'TLSv1.3'))
            client.write(b'GET / HTTP/1.0\r\n\r\n')
            si.write(co.read())
            self.assertEqual(server.read(), b'GET / HTTP/1.0\r\n\r\n')

    def test_incomplete_certificate_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            key = Path(directory) / '192.168.10.116.key'
            key.write_text('preserve')
            with self.assertRaises(ValueError): prepare_certificate('192.168.10.116', directory)
            self.assertEqual(key.read_text(), 'preserve')


if __name__ == '__main__':
    unittest.main()
