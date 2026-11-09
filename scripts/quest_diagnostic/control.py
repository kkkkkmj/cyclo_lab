"""CPU-only bounded Cartesian target controller. Quaternions are xyzw, metres/radians."""
import copy
import math


def add(a,b): return [x+y for x,y in zip(a,b)]
def sub(a,b): return [x-y for x,y in zip(a,b)]
def scale(a,s): return [x*s for x in a]
def norm(a): return math.sqrt(sum(x*x for x in a))
def clip_vector(a, maximum): return list(a) if maximum is None else scale(a, min(1., maximum/max(norm(a), 1e-12)))
def qinv(q): return [-q[0], -q[1], -q[2], q[3]]
def qmul(a,b):
    x,y,z,w=a; X,Y,Z,W=b
    return [w*X+x*W+y*Z-z*Y, w*Y-x*Z+y*W+z*X, w*Z+x*Y-y*X+z*W, w*W-x*X-y*Y-z*Z]
def qrotate(q,v): return qmul(qmul(q, v+[0]), qinv(q))[:3]
def rotvec(q):
    q=scale(q, 1/max(norm(q),1e-12))
    if q[3]<0: q=scale(q,-1)
    n=norm(q[:3])
    return scale(q[:3], 2*math.atan2(n,q[3])/n) if n>1e-9 else [0.,0.,0.]
def quat(v):
    a=norm(v)
    return scale(v, math.sin(a/2)/a)+[math.cos(a/2)] if a>1e-9 else [0.,0.,0.,1.]
def button(h,i): return h.get('buttons',[])[i]['value'] if len(h.get('buttons',[]))>i else 0.


class BoundedTeleop:
    position_scale=.25
    rotation_scale=.5
    max_translation=.05
    max_rotation=math.radians(15)
    practice=False
    gripper_trigger_official_binary=False
    linear_speed=.05
    angular_speed=.5
    max_target_lead=None
    max_angular_lead=None
    workspace_min=None
    workspace_max=None
    def __init__(self, poses, lift_action, enable_grippers=False):
        self.home=copy.deepcopy(poses)
        self.targets=copy.deepcopy(poses)
        self.grippers={'left':1.,'right':1.}
        self.lift_action=lift_action
        self.enable_grippers=enable_grippers
        self.measured=None
        self.limits_hit={s:{} for s in poses}
        self.raw_targets={}
        self.reference_changes=[]
        self.signature=None
        self.basis=None
        self.states={s:dict(ready=False, anchor=None, last=None, reason='waiting') for s in poses}

    def gripper_command(self, trigger):
        if self.gripper_trigger_official_binary:
            # Toast maps (1-action)/2 * 1.1 rad; -1 would close to 1.1, not 1.0.
            return 1. if trigger < .5 else 1.-2./1.1
        return 1-2*max(0.,min(1.,trigger))

    def freeze(self,side):
        if self.practice and self.measured is not None:self.targets[side]=copy.deepcopy(self.measured[side])

    def hold(self, side, reason):
        self.freeze(side)
        self.states[side].update(ready=False, anchor=None, last=None, reason=reason)

    def map_vector(self,v):
        forward,right=self.basis
        return [sum(a*b for a,b in zip(v,forward)), -sum(a*b for a,b in zip(v,right)), v[1]]

    def update(self, snapshot, loop_gap=False, measured=None):
        self.raw_targets={}
        self.reference_changes=[]
        self.measured=measured
        self.limits_hit={s:{} for s in self.states}
        if self.practice and measured is None:
            for side in self.states:self.hold(side,'measured_pose_missing')
            return
        p=snapshot.get('packet') or {}
        hands=p.get('controllers',{})
        signature=(snapshot.get('server_id'),p.get('session'),p.get('reference_generation'),p.get('safety_epoch'),
                   *(hands.get(s,{}).get('source_id') for s in ('left','right')))
        if signature!=self.signature:
            names=('server_id','session','reference_generation','safety_epoch','left_source','right_source')
            self.reference_changes=[name for i,name in enumerate(names) if self.signature is None or self.signature[i]!=signature[i]]
            self.signature=signature; self.basis=None
            for side in self.states: self.hold(side,'new_reference_release_buttons')
        if not snapshot.get('live') or loop_gap or not p.get('preview_ok',False):
            reason='loop_gap' if loop_gap else 'input_not_live' if not snapshot.get('live') else 'preview_not_live'
            for side in self.states: self.hold(side,reason)
            return
        def valid(h):
            profiles=h.get('profiles',[])
            return (h.get('valid') is True and 'meta-quest-touch-plus' in profiles
                    and not any('hand' in x.lower() for x in profiles)
                    and h.get('mapping')=='xr-standard' and len(h.get('buttons',[]))>=6)
        released=all(valid(hands.get(s,{})) and button(hands[s],1)<.2 for s in self.states)
        rebase=any(button(hands.get(s,{}),5)>.8 for s in self.states)
        if self.basis is None or rebase:
            for side in self.states: self.hold(side,'look_forward_release_both_squeezes')
            head=p.get('head_quaternion_xyzw')
            if not released or not isinstance(head,list) or len(head)!=4: return
            forward=qrotate(head,[0,0,-1]);forward[1]=0
            if norm(forward)<.5: return
            forward=scale(forward,1/norm(forward))
            self.basis=(forward,[-forward[2],0,forward[0]])
            for side in self.states: self.states[side].update(ready=True, reason='ready')
            return
        for side,state in self.states.items():
            h=hands.get(side,{})
            if not valid(h):
                self.hold(side,h.get('reason','invalid_controller'));continue
            if button(h,1)<.2:
                self.freeze(side)
                state.update(ready=True,anchor=None,last=None,reason='ready');continue
            if button(h,1)<.8 or not state['ready']:
                if self.practice:self.freeze(side);state['anchor']=None
                state['reason']='release_then_squeeze';continue
            current=(h['position'],h['quaternion_xyzw'])
            if state['anchor'] is None:
                self.freeze(side)
                if (self.practice or self.gripper_trigger_official_binary) and self.enable_grippers:self.grippers[side]=self.gripper_command(button(h,0))
                state['anchor']=(copy.deepcopy(current),copy.deepcopy(self.targets[side]))
                state['last']=copy.deepcopy(current);state['reason']='anchored';continue
            if norm(sub(current[0],state['last'][0]))>.20 or norm(rotvec(qmul(current[1],qinv(state['last'][1]))))>math.radians(60):
                self.hold(side,'controller_jump_release');continue
            state['last']=copy.deepcopy(current)
            (cp,cq),(rp,rq)=state['anchor']
            position=add(rp,scale(self.map_vector(sub(current[0],cp)),self.position_scale))
            raw_position=position[:]
            self.limits_hit[side]['home_translation']=self.max_translation is not None and norm(sub(position,self.home[side][0]))>self.max_translation
            position=add(self.home[side][0],clip_vector(sub(position,self.home[side][0]),self.max_translation))
            delta=self.map_vector(rotvec(qmul(current[1],qinv(cq))))
            orientation=qmul(quat(scale(delta,self.rotation_scale)),rq)
            self.raw_targets[side]=(raw_position,orientation[:])
            home_delta=rotvec(qmul(orientation,qinv(self.home[side][1])))
            self.limits_hit[side]['home_rotation']=self.max_rotation is not None and norm(home_delta)>self.max_rotation
            orientation=qmul(quat(clip_vector(home_delta,self.max_rotation)),self.home[side][1])
            if self.workspace_min is not None:
                self.limits_hit[side]['workspace']=any(v<lo or v>hi for v,lo,hi in zip(position,self.workspace_min,self.workspace_max))
                position=[max(lo,min(hi,v)) for v,lo,hi in zip(position,self.workspace_min,self.workspace_max)]
            if self.max_target_lead is not None:
                if measured is None:
                    self.hold(side,'measured_pose_missing');continue
                mp,mq=measured[side]
                self.limits_hit[side]['translation_lead']=norm(sub(position,mp))>self.max_target_lead
                self.limits_hit[side]['rotation_lead']=norm(rotvec(qmul(orientation,qinv(mq))))>self.max_angular_lead
                position=add(mp,clip_vector(sub(position,mp),self.max_target_lead))
                orientation=qmul(quat(clip_vector(rotvec(qmul(orientation,qinv(mq))),self.max_angular_lead)),mq)
            # Final projections retain workspace bounds even if measured tracking has drifted.
            if self.max_target_lead is not None:
                position=add(self.home[side][0],clip_vector(sub(position,self.home[side][0]),self.max_translation))
                if self.workspace_min is not None:position=[max(lo,min(hi,v)) for v,lo,hi in zip(position,self.workspace_min,self.workspace_max)]
                orientation=qmul(quat(clip_vector(rotvec(qmul(orientation,qinv(self.home[side][1]))),self.max_rotation)),self.home[side][1])
            self.targets[side]=(position,orientation)
            if self.enable_grippers:
                self.grippers[side]=self.gripper_command(button(h,0))
            state['reason']='active'

    def action(self, current, dt):
        """Relative pose error / existing IK scale .3; bounded corrections, not integrated velocity."""
        result=[]
        for side in ('left','right'):
            p,q=current[side];tp,tq=self.targets[side]
            if self.practice and self.states[side]['reason'] not in ('active','anchored'):
                result += [0.]*6
                continue
            delta=sub(tp,p);rotation=rotvec(qmul(tq,qinv(q)))
            linear_cap=None if self.linear_speed is None else self.linear_speed*dt
            angular_cap=None if self.angular_speed is None else self.angular_speed*dt
            self.limits_hit[side]['linear_speed']=linear_cap is not None and norm(delta)>linear_cap
            self.limits_hit[side]['angular_speed']=angular_cap is not None and norm(rotation)>angular_cap
            result+=scale(clip_vector(delta,linear_cap),1/.3)
            result+=scale(clip_vector(rotation,angular_cap),1/.3)
        return result+[self.grippers['left'],self.grippers['right'],self.lift_action]
