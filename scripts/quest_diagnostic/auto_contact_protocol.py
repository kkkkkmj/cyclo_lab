"""Pure deterministic command schedule. Never declares contact without validated reports."""
class Protocol:
    def __init__(self,speed=.01,max_down=.25,baseline=1.,hold=.2):
        if not .001<=speed<=.02 or not .005<=max_down<=.3:raise ValueError('speed .001.. .02 m/s; max_down .005.. .30 m')
        self.speed=speed;self.max_down=max_down;self.baseline=baseline;self.hold=hold
        self.phase='baseline';self.elapsed=0.;self.down=0.;self.contact_observed=False
    def advance(self,dt,contact):
        if self.phase=='done':return self.down
        self.elapsed+=dt
        if self.phase=='baseline':
            if contact:raise RuntimeError('unexpected_baseline_contact')
            if self.elapsed>=self.baseline:self.phase='approach';self.elapsed=0.
        elif self.phase=='approach':
            if contact:self.phase='contact_hold';self.elapsed=0.;self.contact_observed=True
            elif self.down>=self.max_down:self.phase='release';self.elapsed=0.
            else:self.down=min(self.max_down,self.down+self.speed*dt)
        elif self.phase=='contact_hold':
            if self.elapsed>=self.hold:self.phase='release';self.elapsed=0.
        elif self.phase=='release':
            if self.down==0:self.phase='done'
            else:self.down=max(0.,self.down-self.speed*dt)
        return self.down

class PlannedProtocol(Protocol):
    """High-level translate, descend, retract, return. No physics parameters changed."""
    def __init__(self,plan,speed=.01):
        import math
        super().__init__(speed=speed)
        self.xy=list(plan['horizontal_offset_m'])
        self.length=math.hypot(*self.xy)
        self.max_down=float(plan['max_down_m'])
        if not 0<self.length<=.25 or not .005<=self.max_down<=.45:
            raise ValueError('Plan horizontal travel (0,.25]m, descent [.005,.45]m')
        self.horizontal=0.

    def offset(self):
        return [self.xy[0]*self.horizontal/self.length,self.xy[1]*self.horizontal/self.length,-self.down]

    def advance(self,dt,contact):
        if self.phase=='done':return self.down
        self.elapsed+=dt
        if self.phase=='baseline':
            if contact:raise RuntimeError('unexpected_baseline_contact')
            if self.elapsed>=self.baseline:self.phase='translate';self.elapsed=0.
        elif self.phase=='translate':
            if contact:raise RuntimeError('unexpected_horizontal_contact')
            if self.horizontal>=self.length:self.phase='approach';self.elapsed=0.
            else:self.horizontal=min(self.length,self.horizontal+self.speed*dt)
        elif self.phase=='approach':
            if contact:self.phase='contact_hold';self.elapsed=0.;self.contact_observed=True
            elif self.down>=self.max_down:self.phase='release';self.elapsed=0.
            else:self.down=min(self.max_down,self.down+self.speed*dt)
        elif self.phase=='contact_hold':
            if self.elapsed>=self.hold:self.phase='release';self.elapsed=0.
        elif self.phase=='release':
            if self.down==0:self.phase='return_horizontal';self.elapsed=0.
            else:self.down=max(0.,self.down-self.speed*dt)
        elif self.phase=='return_horizontal':
            if contact:raise RuntimeError('contact_persists_after_retraction')
            if self.horizontal==0:self.phase='done'
            else:self.horizontal=max(0.,self.horizontal-self.speed*dt)
        return self.down
