"""Read existing files only; concise distinction between experiment, measurement and shutdown."""
import argparse,json
from pathlib import Path
from auto_contact_checked import process_error

def read(path):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return None

def summarize(path):
    supervisor=read(path.with_suffix('.supervisor.json')) or {};outcome=read(path/'outcome.json') or {}
    checks=read(path/'contact_setup_validation.json') or []
    after=read(path/'after_episode_reset.json') or {}
    result=dict(status=outcome.get('status'),reason=outcome.get('reason'),child_exit=supervisor.get('child_exit'),effective_exit=supervisor.get('effective_exit'),
        resources_close_completed=outcome.get('resources_close_completed'),app_close_completed=outcome.get('app_close_completed'),app_close_returned=outcome.get('app_close_returned'),shutdown_phase=outcome.get('shutdown_phase'),
        initial_motions=after.get('motions',{}).get('value'),initial_contact_api_checks_passed=bool(checks) and all(c.get('validation') is not None for c in checks),
        physics_samples=0,modes_seen=[],max_limit_excess_rad=None,invalid_contact_samples=0,reported_contact_steps=0,parse_errors=0,native_error_count=len(supervisor.get('native_errors',[])),probe_closed=False)
    f=path/'contact.jsonl'
    if f.exists():
        for line in f.open():
            try:r=json.loads(line)
            except ValueError:result['parse_errors']+=1;continue
            if r.get('event')=='closed':result['probe_closed']=True
            if r.get('event')!='physics':continue
            result['physics_samples']+=1
            mode=r.get('dof_motions',{}).get('value')
            if mode not in result['modes_seen']:result['modes_seen'].append(mode)
            excess=r.get('limit_excess_rad')
            if excess is not None:result['max_limit_excess_rad']=list(excess) if result['max_limit_excess_rad'] is None else [max(a,b) for a,b in zip(result['max_limit_excess_rad'],excess)]
            contacts=r.get('contacts',[])
            valid=bool(contacts) and all(c.get('validation') is not None for c in contacts)
            if not valid:result['invalid_contact_samples']+=1
            if valid and any(c.get('counts') is not None and sum(sum(v) for v in c['counts'])>0 for c in contacts):result['reported_contact_steps']+=1
    result['note']='No-contact API checks are not calibration under contact. Missing supervisor/close evidence is not success.'
    log=path.with_suffix('.supervisor.log')
    errors=supervisor.get('process_errors')
    if errors is None:errors=[line.strip() for line in log.open(errors='replace') if process_error(line)] if log.exists() else []
    result.update(requested_exit_code=outcome.get('requested_exit_code'),process_errors=errors,
                  process_exit_clean=supervisor.get('child_exit')==0 and not errors,
                  geometry_snapshot_available=(path/'collision_geometry.json').exists())
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(summarize(a.output),indent=2,ensure_ascii=False))
