"""Fetch exact official tree into a NEW independent directory; never touch worktree."""
import argparse,subprocess,json
from pathlib import Path
from common import SHA,verify_checkout,sha
p=argparse.ArgumentParser();p.add_argument('--destination',type=Path,required=True);a=p.parse_args()
if a.destination.exists():p.error('New independent directory required')
a.destination.mkdir(parents=True)
def run(*args):subprocess.run(list(args),cwd=a.destination,check=True)
run('git','init');run('git','remote','add','origin','https://github.com/ROBOTIS-GIT/cyclo_lab.git');run('git','fetch','--depth','1','origin',SHA);run('git','checkout','--detach','FETCH_HEAD')
run('git','submodule','update','--init','--recursive')
# local LFS hooks only; no global git config mutations.
run('git','lfs','install','--local');run('git','lfs','pull','origin',SHA)
verify_checkout(a.destination)
print(json.dumps(dict(official_sha=SHA,root=str(a.destination.resolve()),note='USD composition dependencies still verified by GPU initialization; checkout alone does not prove assets complete')))
