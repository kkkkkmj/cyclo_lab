"""CPU-only explicit episode lifecycle and edge-triggered Quest buttons."""
class EpisodeLifecycle:
    def __init__(self):
        self.state='WAITING'; self.number=0; self.reason='explicit_start_required'
    def start(self, allowed):
        if self.state!='WAITING' or not allowed:return False
        self.number+=1;self.state='RUNNING';self.reason='running';return True
    def finish(self, reason):
        if self.state!='RUNNING':return False
        self.state='WAITING';self.reason=reason;return True


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
