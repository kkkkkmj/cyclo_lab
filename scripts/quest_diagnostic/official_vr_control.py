"""Official 7D adapter only. Does not change action manager or physical state."""
import copy,math
from control import BoundedTeleop,sub,rotvec,qmul,qinv,clip_vector,scale,button
class OfficialController(BoundedTeleop):
    position_scale=1.;rotation_scale=1.
    max_translation=.30;max_rotation=math.radians(60)
    def __init__(self,poses):super().__init__(poses,0,False)
    def freeze(self,side):
        if self.measured is not None:self.targets[side]=copy.deepcopy(self.measured[side])
    def update(self,snapshot,loop_gap=False,measured=None):
        super().update(snapshot,loop_gap,measured)
        self.states['left']['reason']='unsupported_official_left_arm'
        if self.states['right']['reason'] in ('active','anchored'):
            h=(snapshot.get('packet') or {}).get('controllers',{}).get('right',{})
            self.grippers['right']=-1. if button(h,0)>=.5 else 1.
    def action(self,current,dt):
        if self.states['right']['reason'] not in ('active','anchored'):return [0.]*6+[self.grippers['right']]
        p,q=current['right'];tp,tq=self.targets['right']
        return scale(clip_vector(sub(tp,p),.01),1/.3)+scale(clip_vector(rotvec(qmul(tq,qinv(q))),.05),1/.3)+[self.grippers['right']]
