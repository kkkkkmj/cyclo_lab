"""CPU-only explicit episode lifecycle and edge-triggered Quest buttons."""
class EpisodeLifecycle:
    def __init__(self):
        self.state='WAITING'; self.number=0; self.reason='explicit_start_required';self.result=None;self.pending_result=None
    def start(self, allowed):
        if self.state!='WAITING' or not allowed:return False
        self.number+=1;self.state='RUNNING';self.reason='running';self.result=None;self.pending_result=None;return True
    def finish(self, reason, result=None):
        if self.state!='RUNNING':return False
        self.state='WAITING';self.result=result or episode_result(reason);self.reason=self.result['reason'];return True


def can_start(snapshot):
    p=snapshot.get('packet') or {};hands=p.get('controllers',{})
    return bool(snapshot.get('live') and p.get('preview_ok') and all(
        h.get('valid') is True and h.get('mapping')=='xr-standard' and 'meta-quest-touch-plus' in h.get('profiles',[]) and
        not any('hand' in x.lower() for x in h.get('profiles',[])) and
        len(h.get('buttons',[]))>=6 and h['buttons'][1]['value']<.2
        for h in (hands.get('left',{}),hands.get('right',{}))))


class ButtonEdges:
    def __init__(self):self.previous={'left':True,'right':True}
    def commands(self,snapshot):
        p=snapshot.get('packet') or {};result=[]
        for side,command in (('left','n'),('right','s')):
            h=p.get('controllers',{}).get(side,{})
            if not snapshot.get('live') or not h.get('valid') or len(h.get('buttons',[]))<5:
                self.previous[side]=True;continue
            pressed=h['buttons'][4]['pressed']
            if pressed and not self.previous[side]: result.append(command)
            self.previous[side]=pressed
        return result


def episode_result(reason=None, terms=None):
    """One outcome policy for display and storage; terms are pre-reset snapshots.

    Explicit stops override stale terms. Otherwise non-timeout failures beat success;
    success beats a simultaneous time limit. Isaac Lab ORs termination terms and its
    generic recorder labels any success term; this launcher resolves that ambiguity.
    """
    terms=dict(terms or {})
    if reason in (None, 'environment_termination'):
        failures=sorted(k for k,v in terms.items() if v and k not in ('success','time_out','timeout'))
        if failures:reason='+'.join(failures)
        elif terms.get('success'):reason='success'
        elif terms.get('time_out') or terms.get('timeout'):reason='timeout'
        else:reason='environment_termination'
    labels={'success':'SUCCESS','manual_stop':'STOPPED','tracking_stall':'TRACKING STALL',
            'timeout':'TIMEOUT','short_test_duration':'RECORDING TIME LIMIT',
            'bread_dropping':'BREAD DROPPED','operator_exit':'OPERATOR EXIT',
            'environment_termination':'ENVIRONMENT TERMINATION'}
    return dict(reason=reason,label=labels.get(reason,reason.replace('_',' ').upper()),
                success=reason=='success',termination_terms=terms)


def capture_termination_results(manager, lifecycle):
    """Capture env 0 immediately after compute, before recorder export/automatic reset.

    This launcher runs one environment. Do not change the returned termination tensor.
    Works with no recorder, including practice mode.
    """
    original=manager.compute
    def compute(*args,**kwargs):
        observed={};restore=[]
        # The pinned manager keeps only the last true get_term() entry, and can
        # retain it on nonterminal steps. Observe each real predicate once instead.
        for name in manager.active_terms:
            cfg=manager.get_term_cfg(name);func=cfg.func;restore.append((cfg,func))
            def observe(*a,_name=name,_func=func,**kw):
                value=_func(*a,**kw)
                observed[_name]=bool(value[0])
                return value
            cfg.func=observe
        try:value=original(*args,**kwargs)
        finally:
            for cfg,func in restore:cfg.func=func
        if lifecycle.state=='RUNNING':
            lifecycle.pending_result=episode_result(terms=observed) if any(observed.values()) else None
        return value
    manager.compute=compute
    return original
