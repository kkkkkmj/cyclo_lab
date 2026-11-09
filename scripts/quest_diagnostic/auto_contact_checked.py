"""Supervisor: child exit 0 cannot conceal incomplete cleanup or captured limit violation."""
import argparse,json,subprocess,sys
from pathlib import Path

def process_error(line):
    """Native process failure is separate from PhysX measurement errors."""
    return any(marker in line.lower() for marker in ('segmentation fault', 'core dumped', 'fatal python error', 'aborted ('))

def effective_code(child_code,outcome,native_errors):
    if outcome is None:return 1
    if not outcome.get('app_close_completed'):return 1
    if native_errors:return 1
    if outcome.get('cleanup_errors') or outcome.get('cleanup_error'):return 1
    if child_code!=0:return child_code if child_code>0 else 1
    if outcome.get('status')=='limit_excess_captured':return 2
    return int(outcome.get('requested_exit_code',1))

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--protocol',choices=('contact','free-gripper'),default='contact')
    p.add_argument('--quiet',action='store_true',help='Keep full child log on disk; print final status only')
    a,remaining=p.parse_known_args()
    path=a.output.resolve();log=path.with_suffix('.supervisor.log');status=path.with_suffix('.supervisor.json')
    if path.exists() or log.exists() or status.exists():p.error('Choose a new output path; no overwrite')
    path.parent.mkdir(parents=True,exist_ok=True)
    script='free_gripper.py' if a.protocol=='free-gripper' else 'auto_contact_toast.py'
    cmd=['/isaac-sim/python.sh',str(Path(__file__).with_name(script)),'--output',str(path),*remaining]
    errors=[];process_errors=[]
    with log.open('x') as f:
        child=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        for line in child.stdout:
            f.write(line);f.flush()
            if not a.quiet:print(line,end='',flush=True)
            if ('omni.physx' in line or 'physics.tensors' in line) and any(x in line.lower() for x in ('[error]','did not match','overflow')):errors.append(line.strip())
            if process_error(line):process_errors.append(line.strip())
        rc=child.wait()
    outcome=None
    try:outcome=json.loads((path/'outcome.json').read_text())
    except (OSError,ValueError):pass
    code=effective_code(rc,outcome,errors)
    if process_errors:code=1
    report=dict(command=cmd,child_exit=rc,effective_exit=code,outcome=outcome,native_errors=errors,
                process_errors=process_errors,process_exit_clean=rc==0 and not process_errors,
                note='No HDF5 demonstration recording in this automatic protocol; JSON evidence separate from app finalization')
    status.write_text(json.dumps(report,indent=2))
    print('AUTOMATIC_CONTACT_SUPERVISOR '+json.dumps(dict(child_exit=rc,effective_exit=code,
        process_exit_clean=report['process_exit_clean'],status=None if outcome is None else outcome.get('status'),
        reason=None if outcome is None else outcome.get('reason'),report=str(status)) if a.quiet else report),flush=True)
    return code
if __name__=='__main__':sys.exit(main())
