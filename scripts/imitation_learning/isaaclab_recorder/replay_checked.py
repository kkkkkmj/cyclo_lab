"""Supervise one child; fail closed on missing/failed verdict even if Kit exits 0."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
from replay_outcome import effective_exit_code


def run_command(command, require_validation=False):
    started=time.monotonic();run_id=secrets.token_hex(16)
    with tempfile.TemporaryDirectory(prefix='cyclo-replay-result-') as tmp:
        result_path=Path(tmp)/'outcome.json'
        env=dict(os.environ,CYCLO_REPLAY_RESULT=str(result_path),CYCLO_REPLAY_RUN_ID=run_id)
        child=subprocess.Popen(command,env=env)
        print(f'REPLAY_PROCESS_STARTED pid={child.pid}',flush=True)
        interrupted=False
        try:code=child.wait()
        except KeyboardInterrupt:
            interrupted=True
            if child.poll() is None:
                import signal
                child.send_signal(signal.SIGINT)
            code=child.wait()
        try:result=json.loads(result_path.read_text())
        except (OSError,ValueError):result=None
        effective=130 if interrupted else effective_exit_code(code,result,run_id,require_validation)
        print(f'REPLAY_PROCESS_EXIT pid={child.pid} returncode={code} elapsed_s={time.monotonic()-started:.3f}',flush=True)
        summary={k:result.get(k) for k in ('status','checked','mismatched','expected')} if isinstance(result,dict) else None
        print('REPLAY_SUPERVISOR '+json.dumps(dict(verdict=summary,effective_exit_code=effective)),flush=True)
        return effective


if __name__=='__main__':
    sys.exit(run_command([sys.executable,str(Path(__file__).with_name('replay_demos.py')),*sys.argv[1:]],
                         require_validation='--validate_states' in sys.argv[1:]))
