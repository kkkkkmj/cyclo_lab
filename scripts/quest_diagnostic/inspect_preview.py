"""Read-only host/container bridge report; no GPU, sockets, auth tokens or file changes."""
import argparse
import json
from pathlib import Path
from preview import read_preview, build_id

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bridge-dir',type=Path,required=True)
args=parser.parse_args()
root=args.bridge_dir.resolve()
report=dict(bridge_path=str(root),disk_build=build_id(),files={})
for name in ('input.json','preview.jpg','preview.json','server_status.json'):
    try:
        stat=(root/name).stat()
        report['files'][name]=dict(bytes=stat.st_size,mode=oct(stat.st_mode&0o777),uid=stat.st_uid,gid=stat.st_gid,mtime=stat.st_mtime)
    except OSError as error: report['files'][name]=dict(error=str(error))
data,metadata=read_preview(root)
report['producer']=metadata
try:
    envelope=json.loads((root/'input.json').read_text());p=envelope.get('packet') or {}
    report['client']={k:p.get(k) for k in ('client_protocol','client_build','preview_ok','preview_client_claim',
                                         'preview_guard_reason','preview_status','visibility')}
except (OSError,ValueError) as error: report['client']=dict(error=str(error))
try:
    status=json.loads((root/'server_status.json').read_text())
    report['server']={k:status.get(k) for k in ('server_build','preview_http','live','age_ms')}
except (OSError,ValueError) as error: report['server']=dict(error=str(error))
print(json.dumps(report,indent=2))
