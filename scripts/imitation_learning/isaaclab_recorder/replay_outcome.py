"""Explicit replay verdict channel, independent of Kit's process-exit behavior."""
import json
import os
from pathlib import Path

_result={}

def record_outcome(status, **values):
    _result.update(values,status=status,run_id=os.environ.get('CYCLO_REPLAY_RUN_ID'),schema=1)
    destination=os.environ.get('CYCLO_REPLAY_RESULT')
    if destination:
        path=Path(destination);temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps(_result,allow_nan=False))
        os.replace(temporary,path)


def effective_exit_code(raw_code, result, run_id, require_validation):
    if raw_code!=0:return raw_code if raw_code>0 else 128-raw_code
    if not isinstance(result,dict) or result.get('schema')!=1 or result.get('run_id')!=run_id:return 2
    if result.get('status') not in ('completed','validated'):return 1
    if require_validation:
        checked=result.get('checked');expected=result.get('expected');mismatched=result.get('mismatched')
        if type(checked) is not int or type(expected) is not int or type(mismatched) is not int:return 2
        if checked<=0 or checked!=expected or mismatched!=0:return 1
    return 0
