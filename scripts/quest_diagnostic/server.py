#!/usr/bin/env python3
"""CPU-only Quest controller diagnostic. No simulator or robot connection."""
import argparse
import copy
import json
import math
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import ssl
import threading
import time
from urllib.parse import urlparse
from http.cookies import SimpleCookie, CookieError
import sys
import fcntl
from tls import prepare_certificate
from bridge import atomic_write
from preview import CLIENT_PROTOCOL, build_id, read_preview


class Receiver:
    def __init__(self, bridge_dir=None):
        self.bridge_dir = bridge_dir
        self.build = build_id()
        self.preview_http = dict(requests=0, sent=0, last=None)
        self.server_id = secrets.token_hex(16)
        if bridge_dir:
            Path(bridge_dir).mkdir(parents=True, exist_ok=True, mode=0o700)
            self.bridge_lock = (Path(bridge_dir) / '.input.lock').open('a')
            fcntl.flock(self.bridge_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.lock = threading.Lock()
        self.packet = None
        self.received = 0.0
        self.session = None
        self.seq = -1
        self.count = 0
        self.safety_epoch = 0
        self.safety_event = None
        self._publish()

    def _publish(self):
        if self.bridge_dir:
            atomic_write(Path(self.bridge_dir) / "input.json", json.dumps(dict(
                protocol=2, server_id=self.server_id, received_monotonic=self.received,
                packet=self.packet)).encode())

    def accept(self, packet, now=None):
        now = time.monotonic() if now is None else now
        if not isinstance(packet, dict):
            raise ValueError('packet must be an object')
        if not isinstance(packet.get('session'), str) or not 1 <= len(packet['session']) <= 80:
            raise ValueError('invalid session')
        if type(packet.get('seq')) is not int or packet['seq'] < 0:
            raise ValueError('invalid sequence')
        if packet.get('visibility') not in ('visible', 'visible-blurred', 'hidden', 'ended'):
            raise ValueError('invalid visibility')
        def vector(v, length):
            return (isinstance(v, list) and len(v) == length and
                    all(type(x) in (int, float) and math.isfinite(x) for x in v))
        if not vector([packet.get('client_ms')], 1):
            raise ValueError('invalid timestamp')
        if packet.get('head_quaternion_xyzw') is not None:
            head = packet['head_quaternion_xyzw']
            if not vector(head, 4) or abs(sum(x*x for x in head)-1) > .02:
                raise ValueError('invalid head quaternion')
        if 'preview_ok' in packet and type(packet['preview_ok']) is not bool:
            raise ValueError('invalid preview flag')
        if 'preview_status' in packet and not isinstance(packet['preview_status'], dict):
            raise ValueError('invalid preview status')
        packet = copy.deepcopy(packet)
        client_preview = packet.get('preview_status') or {}
        packet['server_build'] = self.build
        packet['preview_client_claim'] = packet.get('preview_ok')
        packet['client_compatibility'] = ('ok' if packet.get('client_protocol') == CLIENT_PROTOCOL
                                        and packet.get('client_build') == self.build else 'reload_required')
        if packet['client_compatibility'] != 'ok':
            packet['preview_ok'] = False
            packet['preview_guard_reason'] = 'client_version_mismatch_or_missing'
        elif packet.get('preview_ok'):
            _, meta = read_preview(self.bridge_dir, now=now)
            packet['producer_age_at_receive_ms'] = meta.get('age_ms')
            packet['producer_validation'] = {k: meta.get(k) for k in ('reason','run_id','frame_id','age_ms','error')}
            frame = client_preview.get('drawn_frame_id')
            try:
                confirmed = (meta.get('reason') == 'ok' and client_preview.get('stage') == 'draw_submitted'
                             and client_preview.get('run_id') == meta['run_id']
                             and 0 < int(frame) <= meta['frame_id'])
            except (TypeError, ValueError, KeyError):
                confirmed = False
            packet['preview_ok'] = confirmed
            packet['preview_guard_reason'] = 'ok' if confirmed else 'producer_or_draw_ack_invalid'
        else:
            packet['preview_guard_reason'] = 'browser_has_not_confirmed_draw'
        hands = packet.get('controllers')
        if not isinstance(hands, dict) or set(hands) != {'left', 'right'}:
            raise ValueError('expected left and right controller slots')
        for hand in hands.values():
            if not isinstance(hand, dict) or type(hand.get('valid')) is not bool:
                raise ValueError('invalid tracking flag')
            profiles = hand.get('profiles', [])
            allowed = (isinstance(profiles, list) and 'meta-quest-touch-plus' in profiles
                       and all(isinstance(p, str) and 'hand' not in p.lower() for p in profiles)
                       and hand.get('reason') != 'hand_input_excluded')
            if not allowed:
                hand.update(valid=False, reason='controller_profile_not_allowed', buttons=[], axes=[])
                hand.pop('position', None)
                hand.pop('quaternion_xyzw', None)
            if not hand['valid']:
                hand['buttons'], hand['axes'] = [], []
                hand.pop('position', None)
                hand.pop('quaternion_xyzw', None)
            if hand['valid']:
                if not vector(hand.get('position'), 3) or not vector(hand.get('quaternion_xyzw'), 4):
                    raise ValueError('invalid pose')
                if abs(sum(x*x for x in hand['quaternion_xyzw']) - 1) > .02:
                    raise ValueError('quaternion is not normalized')
                if hand.get('mapping') != 'xr-standard':
                    raise ValueError('unsupported gamepad mapping')
            buttons = hand.get('buttons', [])
            if not isinstance(buttons, list) or len(buttons) > 16:
                raise ValueError('invalid buttons')
            for b in buttons:
                if not isinstance(b, dict) or not vector([b.get('value')], 1) or not 0 <= b['value'] <= 1:
                    raise ValueError('invalid button value')
                if type(b.get('pressed')) is not bool or type(b.get('touched')) is not bool:
                    raise ValueError('invalid button flags')
            axes = hand.get('axes', [])
            if not isinstance(axes, list) or len(axes) > 8 or not vector(axes, len(axes)):
                raise ValueError('invalid axes')
        with self.lock:
            if self.session != packet['session'] and now - self.received < 1 and self.packet is not None:
                raise ValueError('another XR session is active; wait one second')
            if self.session == packet['session'] and packet['seq'] <= self.seq:
                raise ValueError('out-of-order packet')
            def usable(p):
                return p and p.get('visibility') == 'visible' and p.get('preview_ok') is True and all(
                    h.get('valid') for h in p['controllers'].values())
            if (self.packet and now-self.received >= .25) or (usable(self.packet) and not usable(packet)):
                self.safety_epoch += 1
                self.safety_event = dict(epoch=self.safety_epoch,seq=packet['seq'],received_monotonic=now,
                    receive_gap_ms=None if self.packet is None else (now-self.received)*1000,
                    visibility=packet.get('visibility'),preview_ok=packet.get('preview_ok'),
                    preview_guard=packet.get('preview_guard_reason'),producer=packet.get('producer_validation'),
                    invalid_hands={s:h.get('reason') for s,h in packet['controllers'].items() if not h.get('valid')})
            packet['safety_epoch'] = self.safety_epoch
            packet['safety_event'] = copy.deepcopy(self.safety_event)
            self.session, self.seq = packet['session'], packet['seq']
            self.packet, self.received = copy.deepcopy(packet), now
            self.count += 1
            self._publish()

    def snapshot(self, now=None):
        now = time.monotonic() if now is None else now
        with self.lock:
            age = now - self.received
            packet = copy.deepcopy(self.packet)
            live = packet is not None and age < .25 and packet['visibility'] == 'visible'
            if packet and not live:
                for hand in packet['controllers'].values():
                    hand['valid'] = False
                    hand['reason'] = 'stale_packet' if age >= .25 else 'session_not_visible'
                    hand['buttons'] = []
                    hand['axes'] = []
                    hand.pop('position', None)
                    hand.pop('quaternion_xyzw', None)
            return dict(server_build=self.build, preview_http=copy.deepcopy(self.preview_http), communication=('waiting' if packet is None else 'stale' if age >= .25 else 'receiving'),
                        live=live, age_ms=round(age*1000) if packet else None,
                        received_packets=self.count, packet=packet)


class Pairing:
    """Single-use 6-digit code: 5 minutes, 5 attempts total (not per IP)."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.Lock()
        self.tokens = {}
        self.rotate()

    def rotate(self):
        with self.lock:
            self.code = f"{secrets.randbelow(1000000):06d}"
            self.deadline = self.clock() + 300
            self.attempts = 0
            self.used = False
            return self.code

    def redeem(self, code):
        with self.lock:
            if self.used or self.clock() >= self.deadline:
                return 410, None
            if self.attempts >= 5:
                return 429, None
            self.attempts += 1
            if not isinstance(code, str) or not secrets.compare_digest(code.encode(), self.code.encode()):
                return (429 if self.attempts == 5 else 401), None
            token = secrets.token_urlsafe(32)
            self.tokens = {t: end for t, end in self.tokens.items() if end > self.clock()}
            if len(self.tokens) >= 8:
                self.tokens.pop(next(iter(self.tokens)))
            self.tokens[token] = self.clock() + 8 * 3600
            self.used = True
            return 200, token

    def authorized(self, cookie):
        try:
            jar = SimpleCookie(cookie or '')
            token = jar['quest_session'].value
        except (KeyError, ValueError, CookieError):
            return False
        with self.lock:
            return self.tokens.get(token, 0) > self.clock()


def make_handler(receiver, pairing, origin):
    # Read HTML on GET; an old open tab still requires explicit reload.
    def page():
        return Path(__file__).with_name('index.html').read_text().replace('__QUEST_BUILD__', build_id()).encode()

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(3)

        def log_message(self, *args):
            pass

        def reply(self, code, body, content_type='application/json', cookie=None, preview_age=None, preview_meta=None):
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Permissions-Policy', 'xr-spatial-tracking=(self)')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Quest-Server-Build', receiver.build)
            if preview_meta:
                self.send_header('X-Preview-Frame', str(preview_meta['frame_id']))
                self.send_header('X-Preview-Run', preview_meta['run_id'])
                self.send_header('X-Teleop-Status', json.dumps(preview_meta.get('timings', {}).get('teleop'), ensure_ascii=True, separators=(',', ':')))
            if preview_age is not None:
                self.send_header('X-Preview-Age-Ms', str(preview_age))
            if cookie:
                self.send_header('Set-Cookie', cookie)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == '/':
                self.reply(200, page(), 'text/html; charset=utf-8')
            elif path == '/version':
                self.reply(200, json.dumps(dict(server_build=receiver.build, disk_build=build_id(),
                                               client_protocol=CLIENT_PROTOCOL)).encode())
            elif path in ('/input.js', '/hud.js', '/preview_client.js'):
                self.reply(200, Path(__file__).with_name(path[1:]).read_bytes(), 'application/javascript')
            elif path == '/preview.jpg':
                with receiver.lock:
                    receiver.preview_http['requests'] += 1
                if not pairing.authorized(self.headers.get('Cookie')):
                    with receiver.lock:
                        receiver.preview_http['last'] = {'reason': 'unauthorized'}
                    self.reply(401, b'{}')
                else:
                    data, meta = read_preview(receiver.bridge_dir)
                    with receiver.lock:
                        receiver.preview_http['sent'] += int(data is not None)
                        receiver.preview_http['last'] = meta
                    if data is None:
                        self.reply(503, json.dumps(meta).encode())
                    else:
                        self.reply(200, data, 'image/jpeg', preview_age=meta['age_ms'], preview_meta=meta)
            elif path == '/status':
                if not pairing.authorized(self.headers.get('Cookie')):
                    self.reply(401, b'{"error":"Pair using the PC code"}')
                else:
                    self.reply(200, json.dumps(receiver.snapshot()).encode())
            else:
                self.reply(404, b'{}')

        def do_POST(self):
            if self.headers.get('Origin') != origin:
                self.reply(403, b'{"error":"Origin mismatch"}')
                return
            path = urlparse(self.path).path
            if path not in ('/pair', '/input'):
                self.reply(404, b'{}')
                return
            if path == '/input' and not pairing.authorized(self.headers.get('Cookie')):
                self.reply(401, b'{"error":"Pair again"}')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if self.headers.get('Transfer-Encoding') or not 0 < length <= 16384:
                    raise ValueError('invalid packet length')
                packet = json.loads(self.rfile.read(length))
                if not isinstance(packet, dict):
                    raise ValueError('expected an object')
                if path == '/pair':
                    code, token = pairing.redeem(packet.get('code'))
                    if token:
                        self.reply(200, b'{"ok":true}', cookie=(
                            f'quest_session={token}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=28800'))
                    else:
                        errors = {401: 'Incorrect code', 410: 'Code expired or already used. Type p in PC terminal.',
                                  429: 'Five attempts used. Type p in PC terminal.'}
                        self.reply(code, json.dumps({'error': errors[code]}).encode())
                else:
                    receiver.accept(packet)
                    self.reply(200, b'{"ok":true}')
            except (ValueError, TypeError, OSError) as error:
                self.reply(400, json.dumps({'error': str(error)}).encode())

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True, help='PC address reachable from Quest; used for the HTTPS origin and certificate')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--bridge-dir', type=Path, help='Opt-in local IPC directory for the simulation test')
    parser.add_argument('--cert', type=Path, help='Existing trusted certificate, with --key')
    parser.add_argument('--key', type=Path)
    parser.add_argument('--cert-dir', type=Path,
                        default=Path.home() / '.local/state/cyclo-quest-tls')
    args = parser.parse_args()
    if bool(args.cert) != bool(args.key):
        parser.error('--cert and --key must be used together')
    try:
        cert, key = (args.cert, args.key) if args.cert else prepare_certificate(args.host, args.cert_dir)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cert, key)
        receiver, pairing = Receiver(args.bridge_dir), Pairing()
        origin = f'https://{args.host}:{args.port}'
        server = ThreadingHTTPServer((args.host, args.port), make_handler(receiver, pairing, origin))
        server.socket = context.wrap_socket(server.socket, server_side=True)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Cannot start HTTPS diagnostic: {error}\nExisting servers were not stopped.\n')
    print(f'QUEST ADDRESS: {origin}/', flush=True)
    print(f'SERVER BUILD: {receiver.build}; refresh Quest page and verify this build.', flush=True)
    def print_code():
        print(f'PAIRING CODE: {pairing.code}  (single use; expires in 5 minutes; max 5 attempts)', flush=True)
    print_code()
    print(f'TLS certificate: {cert}', flush=True)
    print('INPUT SERVER (no simulator). Type p + Enter for a new code; Ctrl+C stops only this server.', flush=True)
    if args.bridge_dir:
        print(f'LOCAL SIM BRIDGE: {args.bridge_dir}', flush=True)
    def console():
        for line in sys.stdin:
            if line.strip().lower() == 'p':
                pairing.rotate()
                print_code()
    if sys.stdin.isatty():
        threading.Thread(target=console, daemon=True).start()
    def report():
        while True:
            time.sleep(1)
            status = receiver.snapshot()
            packet = status['packet']
            if packet:
                print(json.dumps(dict(communication=status['communication'], live=status['live'], age_ms=status['age_ms'],
                                      received_packets=status['received_packets'],
                                      client_build=packet.get('client_build'),
                                      compatibility=packet.get('client_compatibility'),
                                      preview_ok=packet.get('preview_ok'),
                                      preview_guard_reason=packet.get('preview_guard_reason'),
                                      preview_status=packet.get('preview_status'),
                                      preview_http=status['preview_http'],
                                      controllers=packet['controllers'])), flush=True)
            if args.bridge_dir:
                atomic_write(args.bridge_dir/'server_status.json',json.dumps(status).encode())
    threading.Thread(target=report, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
