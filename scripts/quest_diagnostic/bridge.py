"""Atomic local IPC only; JSON freshness uses Linux CLOCK_MONOTONIC across Docker/host."""
import json
import os
from pathlib import Path
import tempfile
import time


def atomic_write(path, data, mode=0o600):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_input(directory, now=None):
    now = time.monotonic() if now is None else now
    try:
        envelope = json.loads((Path(directory) / 'input.json').read_text())
        age = now - envelope['received_monotonic']
        packet = envelope['packet']
        live = (envelope['protocol'] == 2 and 0 <= age < .25 and
                packet is not None and packet.get('visibility') == 'visible')
        return {'live': live, 'packet': packet, 'server_id': envelope['server_id'], 'age_ms': age*1000, 'received_monotonic': envelope['received_monotonic']}
    except (OSError, ValueError, KeyError, TypeError):
        return {'live': False, 'packet': None, 'server_id': None}
