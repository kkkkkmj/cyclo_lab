"""Versioned camera publications and fail-closed freshness/integrity checks."""
import hashlib
import json
from pathlib import Path
import time
from bridge import atomic_write

CLIENT_PROTOCOL = 3


def build_id():
    root = Path(__file__).parent
    digest = hashlib.sha256()
    for name in ('index.html', 'input.js', 'hud.js', 'preview_client.js'):
        digest.update((root / name).read_bytes())
    return 'preview-v3-' + digest.hexdigest()[:12]


def publish_preview(directory, data, run_id, frame_id, cameras, timings, captured=None):
    captured = time.monotonic() if captured is None else captured
    metadata = dict(status='running', run_id=run_id, frame_id=frame_id,
                    captured_monotonic=captured, published_unix=time.time(),
                    bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                    cameras=cameras, timings=timings)
    # One atomic commit for HTTP/ack readers: metadata and bytes cannot cross generations.
    atomic_write(Path(directory)/'preview.frame', json.dumps(metadata).encode()+b'\n'+data, mode=0o644)
    atomic_write(Path(directory)/'preview.jpg', data, mode=0o644)
    # Metadata is the commit record. A racing reader rejects a hash mismatch.
    atomic_write(Path(directory)/'preview.json', json.dumps(metadata).encode(), mode=0o644)
    return metadata


def read_preview(directory, now=None):
    if directory is None:
        return None, {'reason': 'bridge_not_configured'}
    now = time.monotonic() if now is None else now
    try:
        root = Path(directory)
        try:
            header, data = (root/'preview.frame').read_bytes().split(b'\n', 1)
            meta = json.loads(header)
        except FileNotFoundError:
            # Compatibility with an older producer; never fall back on a corrupt bundle.
            meta = json.loads((root/'preview.json').read_text())
            data = None
        if meta.get('status') != 'running':
            return None, dict(meta, reason='producer_stopped')
        age = (now-meta['captured_monotonic'])*1000
        if not 0 <= age < 1000:
            return None, dict(meta, reason='frame_stale', age_ms=age)
        if data is None:
            data = (root/'preview.jpg').read_bytes()
        if len(data) != meta['bytes'] or hashlib.sha256(data).hexdigest() != meta['sha256']:
            return None, dict(meta, reason='publication_in_progress', age_ms=age)
        return data, dict(meta, reason='ok', age_ms=age)
    except FileNotFoundError as error:
        return None, {'reason': 'file_missing', 'error': str(error)}
    except PermissionError as error:
        return None, {'reason': 'permission_denied', 'error': str(error)}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return None, {'reason': 'metadata_or_io_error', 'error': str(error)}


def stop_preview(directory, run_id, error=None):
    # Retain the JPEG for forensics; stopped metadata prevents serving it as live.
    stopped = json.dumps(dict(status='stopped',run_id=run_id,stopped_unix=time.time(),error=error)).encode()
    atomic_write(Path(directory)/'preview.frame', stopped+b'\n', mode=0o644)
    atomic_write(Path(directory)/'preview.json', stopped, mode=0o644)
