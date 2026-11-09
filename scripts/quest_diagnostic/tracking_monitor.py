"""Practice lag/stall guard. Wall-time progress, no extra robot reads or physics calls."""
import copy,math
from control import norm,sub,rotvec,qmul,qinv

class TrackingMonitor:
    def __init__(self,stall_seconds=2.):
        self.stall_seconds=stall_seconds;self.windows={};self.stats={}
    def check(self,controller,current,now):
        for side in ('left','right'):
            target=controller.targets[side];pose=current[side]
            distance=norm(sub(target[0],pose[0]));angle=norm(rotvec(qmul(target[1],qinv(pose[1]))))
            active=controller.states[side]['reason'] in ('active','anchored')
            self.stats[side]=dict(error_m=distance,error_rad=angle,active=active,stall_wall_s=0.,progress_samples=0)
            if not active or (distance<=.08 and angle<=math.radians(30)):
                self.windows.pop(side,None);continue
            # A gross discontinuity is never sent to IK, even with optional teleop limits disabled.
            if distance>.6 or angle>math.radians(170):return side,'tracking_discontinuity'
            metric=distance+.1*angle
            window=self.windows.get(side)
            moved=window is not None and (norm(sub(target[0],window['target'][0]))>.02 or
                  norm(rotvec(qmul(target[1],qinv(window['target'][1]))))>math.radians(5))
            if window is None or moved or metric<window['best']-.002:
                self.windows[side]=dict(target=copy.deepcopy(target),since=now,best=metric,count=1)
                continue
            window['count']+=1
            self.stats[side].update(stall_wall_s=now-window['since'],progress_samples=window['count'])
            if now-window['since']>=self.stall_seconds and window['count']>=5:return side,'tracking_stall'
        return None
