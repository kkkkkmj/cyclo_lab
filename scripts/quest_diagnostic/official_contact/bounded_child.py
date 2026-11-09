"""Bounded ownership-scoped child supervision. Never marks forced exits successful."""
import json,os,signal,subprocess,time
from pathlib import Path

def run_child(command,log_path,output,wall_timeout=600,shutdown_timeout=120,grace=15):
 if min(wall_timeout,shutdown_timeout,grace)<=0:raise ValueError('Timeouts must be positive')
 output=Path(output);start=time.monotonic();closing=None;reason=None;signals=[]
 def send(sig):
  # Only this newly created process group, never a discovered existing task.
  try:os.killpg(child.pid,sig);signals.append(sig.name)
  except ProcessLookupError:pass
 def wait(seconds):
  try:child.wait(timeout=seconds);return True
  except subprocess.TimeoutExpired:return False
 with Path(log_path).open('x') as log:
  child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   while child.poll() is None:
    now=time.monotonic()
    try:
     o=json.loads((output/'outcome.json').read_text())
     if 'close' in str(o.get('shutdown_phase','')) and closing is None:closing=now
    except (OSError,ValueError):pass
    if now-start>=wall_timeout:reason='child_wall_timeout'
    if closing is not None and now-closing>=shutdown_timeout:reason='shutdown_timeout'
    if reason:break
    time.sleep(.1)
  except KeyboardInterrupt:reason='supervisor_interrupted'
  if reason:
   evidence={'reason':reason,'child_pid':child.pid,'elapsed_s':time.monotonic()-start,'forced_cleanup':True}
   output.mkdir(parents=True,exist_ok=True)
   try:
    pid=json.loads((output/'child_ready.json').read_text())['pid']
    if os.getpgid(pid)==child.pid:os.kill(pid,signal.SIGUSR1);time.sleep(.2)
   except (OSError,ValueError,KeyError):pass
   try:evidence['proc_status']=Path(f'/proc/{child.pid}/status').read_text()
   except OSError:evidence['proc_status']=None
   (output/'supervisor_timeout.json').write_text(json.dumps(evidence,indent=2))
   send(signal.SIGINT)
   if not wait(grace):
    send(signal.SIGTERM)
    if not wait(grace):send(signal.SIGKILL);wait(grace)
   # Shell may exit before its descendants; clean only the owned group.
   send(signal.SIGKILL)
 return dict(child_exit=child.poll(),timeout_reason=reason,signals=signals,elapsed_s=time.monotonic()-start,forced_cleanup=bool(reason))
