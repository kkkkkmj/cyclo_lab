"""Persistent LAN development certificate; never installs trust or modifies browser settings."""
import ipaddress
import os
from pathlib import Path
import subprocess
import tempfile


def prepare_certificate(host, directory):
    address = str(ipaddress.ip_address(host))
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    cert, key = directory / f'{address}.crt', directory / f'{address}.key'
    if cert.exists() != key.exists():
        raise ValueError(f'Incomplete certificate pair in {directory}; use a fresh --cert-dir')
    if not cert.exists():
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            temp = Path(temporary)
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-sha256', '-nodes',
                            '-days', '30', '-subj', '/CN=Quest LAN diagnostic',
                            '-addext', f'subjectAltName=IP:{address}',
                            '-addext', 'extendedKeyUsage=serverAuth',
                            '-keyout', str(temp / 'key'), '-out', str(temp / 'cert')],
                           check=True, capture_output=True)
            os.chmod(temp / 'key', 0o600)
            # Exclusive creation: never replace certificates of an existing server.
            with key.open('xb') as out:
                os.chmod(key, 0o600)
                out.write((temp / 'key').read_bytes())
            with cert.open('xb') as out:
                out.write((temp / 'cert').read_bytes())
    for check in (['-checkend', '0'], ['-checkip', address]):
        result = subprocess.run(['openssl', 'x509', '-in', str(cert), '-noout', *check], capture_output=True)
        if result.returncode:
            raise ValueError('Expired/wrong-IP certificate. Use a fresh --cert-dir; existing files are preserved.')
    return cert, key
