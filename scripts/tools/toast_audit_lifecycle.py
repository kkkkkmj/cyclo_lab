"""Keep physics results independent of worker lifecycle failures."""
import json
import os
import traceback
from pathlib import Path

def atomic_json(path,data):
    path=Path(path);temp=path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n');os.replace(temp,path)

def result_status(path):
    path=Path(path)
    if not path.exists():return {'status':'MISSING','error':'worker produced no result JSON'}
    try:
        data=json.loads(path.read_text())
        if not isinstance(data,dict) or 'stability' not in data or 'reset' not in data:raise ValueError('missing result fields')
        return {'status':'VALID','data':data}
    except (OSError,ValueError,TypeError) as exc:return {'status':'CORRUPT','error':str(exc)}

def process_record(out,sid,returncode):
    out=Path(out);checked=result_status(out/(sid+'.json'));life=out/(sid+'.lifecycle.json')
    try:lifecycle=json.loads(life.read_text()) if life.exists() else {'status':'MISSING'}
    except (OSError,ValueError):lifecycle={'status':'CORRUPT'}
    record=dict(returncode=returncode,result_json_status=checked['status'],
        process_status='PASS' if returncode==0 and lifecycle.get('status')=='PASS' else 'ERROR',lifecycle=lifecycle)
    if 'error' in checked:record['result_error']=checked['error']
    log=out/(sid+'.log')
    if log.exists():
        text=log.read_text(errors='replace')
        record['weakref_error_in_log']='weakly-referenced object no longer exists' in text
        if record['weakref_error_in_log']:record['process_status']='ERROR'
    atomic_json(out/(sid+'.process.json'),record)
    return record # Never rewrite, delete or replace worker result, even if corrupt.

def close_safely(env,app):
    errors=[];retained=[]
    if env is not None:
        # Keep manager/scene weak-proxy targets alive while replicator detaches cameras.
        retained=[getattr(env,n,None) for n in ('scene','observation_manager','action_manager','event_manager','recorder_manager','termination_manager','reward_manager','command_manager')]
        scene=getattr(env,'scene',None)
        for sensor in list(getattr(scene,'sensors',{}).values()):
            try:
                sensor._clear_callbacks()
                registry=getattr(sensor,'_rep_registry',None)
                if registry is not None:
                    for annotators in list(registry.values()):
                        for annotator,path in zip(annotators,sensor._render_product_paths):annotator.detach([path])
                    registry.clear() # destructor becomes idempotent after explicit detach
            except Exception:errors.append(dict(stage='sensor_detach',traceback=traceback.format_exc()))
        try:env.close()
        except Exception:errors.append(dict(stage='env.close',traceback=traceback.format_exc()))
    if app is not None:
        try:app.close()
        except Exception:errors.append(dict(stage='app.close',traceback=traceback.format_exc()))
    return errors
