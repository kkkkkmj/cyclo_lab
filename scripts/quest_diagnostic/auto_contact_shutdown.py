"""Persist separate resource cleanup and actual SimulationApp.close return evidence."""
import json,os,time
from pathlib import Path

def persist(path,state):
    path=Path(path);temporary=path.with_name(path.name+'.tmp')
    with temporary.open('w') as f:
        json.dump(state,f,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(temporary,path)

def finish(app,env,probe,path,state,code):
    state.update(app_close_completed=False,app_close_returned=False,cleanup_steps=[],cleanup_errors=[],requested_exit_code=code)
    def mark(phase):
        state['shutdown_phase']=phase;state['shutdown_monotonic']=time.monotonic();state['requested_exit_code']=code;persist(path,state)
    mark('resource_cleanup_begin')
    for name,obj in (('probe',probe),('environment',env)):
        if obj is None:continue
        mark(name+'_close_begin')
        try:obj.close()
        except BaseException as e:state['cleanup_errors'].append(dict(resource=name,error=repr(e)));code=1
        else:state['cleanup_steps'].append(name+'_close_returned')
        mark(name+'_close_end')
    state['resources_close_completed']=not state['cleanup_errors']
    if app is None:
        state['app_close_error']='Application was not initialized';code=1;mark('app_not_initialized');return code
    state['fast_shutdown_at_close']=getattr(app,'config',{}).get('fast_shutdown')
    mark('app_close_begin')
    print('APP_CLOSE BEGIN fast_shutdown='+str(state['fast_shutdown_at_close']),flush=True)
    try:app.close(wait_for_replicator=True,skip_cleanup=False)
    except BaseException as e:
        state['app_close_error']=repr(e);code=1;mark('app_close_exception')
    else:
        state['app_close_returned']=True;state['app_close_completed']=True
        mark('app_close_returned')
        print('APP_CLOSE RETURNED',flush=True)
    return code
