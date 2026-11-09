"""Exact-path contact view validation. Read-only scene inspection, no physics setters."""
import numpy as np


def exact_targets(stage,table_root):
    from pxr import Usd,UsdPhysics
    root=stage.GetPrimAtPath(table_root)
    if not root.IsValid():raise ValueError(f'Missing table root {table_root}')
    colliders=[];targets=[];owners={}
    for p in Usd.PrimRange(root,Usd.TraverseInstanceProxies()):
        if not p.HasAPI(UsdPhysics.CollisionAPI):continue
        if UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr().Get() is False:continue
        path=str(p.GetPath());colliders.append(path);owner=p;actor=None
        while owner.IsValid() and str(owner.GetPath())!='/':
            if owner.HasAPI(UsdPhysics.RigidBodyAPI):actor=str(owner.GetPath());break
            owner=owner.GetParent()
        # Static geometry may have CollisionAPI without a RigidBodyAPI ancestor.
        target=actor or path;owners[path]=dict(rigid_body=actor,filter_path=target)
        if target not in targets:targets.append(target)
    if not targets:raise ValueError('No enabled table collider found')
    if any(any(c in p for c in '*?[]') for p in targets):raise ValueError('Filter targets must be exact prim paths')
    return dict(table_root=table_root,colliders=colliders,targets=targets,owners=owners)


def flatten_paths(v):
    if isinstance(v,str):return [v]
    return [p for group in v for p in flatten_paths(group)]


def validate_view(view,body,targets):
    if not view.check():raise ValueError('RigidContactView.check() false')
    if int(view.sensor_count)!=1 or int(view.filter_count)!=len(targets):raise ValueError('Contact view count mismatch')
    sensors=flatten_paths(view.sensor_paths);filters=flatten_paths(view.filter_paths)
    if sensors!=[body] or filters!=targets:raise ValueError(f'Contact path mismatch: {sensors}, {filters}')
    return dict(sensor_paths=sensors,filter_paths=filters,sensor_count=1,filter_count=len(targets),check=True)


def numeric(x,shape):
    if hasattr(x,'detach'):x=x.detach().cpu().numpy()
    a=np.asarray(x)
    if a.shape!=shape:raise ValueError(f'Expected shape {shape}, got {a.shape}')
    if not np.isfinite(a).all():raise ValueError('Nonfinite contact data')
    return a


class NativePhysicsErrors:
    def __init__(self):
        self.errors=[];self.reason=None;self.handle=None;self.logging=None
        try:
            import carb.logging
            self.logging=carb.logging.acquire_logging()
            def callback(*args):
                text=' '.join(str(x) for x in args);low=text.lower()
                if ('physx' in low or 'physics.tensors' in low) and any(x in low for x in ('did not match','failed','invalid','error','overflow','cannot')):
                    self.errors.append(text)
            self.callback=callback;self.handle=self.logging.add_logger(callback)
        except Exception as e:self.reason=repr(e)
    def close(self):
        if self.handle is not None:self.logging.remove_logger(self.handle);self.handle=None


def read_contact(view,setup,dt,native,details=False):
    """No valid force unless both backend checks and native-error monitor are available."""
    missing=lambda why:dict(value=None,reason=why)
    try:
        if native.reason:raise ValueError('Native error monitor unavailable: '+native.reason)
        if native.errors:raise ValueError('Native physics error: '+native.errors[-1])
        if view is None:raise ValueError(setup['reason'])
        validated=validate_view(view,setup['body'],setup['filters']);n=len(setup['filters'])
        net=numeric(view.get_net_contact_forces(dt=dt),(1,3))
        force=numeric(view.get_contact_force_matrix(dt=dt),(1,n,3))
        data=view.get_contact_data(dt=dt)
        counts=numeric(data[4],(1,n));starts=numeric(data[5],(1,n))
        capacity=int(view.max_contact_data_count)
        if np.any(counts<0) or np.any(starts<0) or np.any(counts!=counts.astype(int)) or np.any(starts+counts>capacity):raise ValueError('Contact buffer bounds/count invalid')
        detail_rows=[]
        if details:
            if int(counts.sum())>=capacity:raise ValueError('Contact detail buffer full; completeness unverified')
            # Inspect only populated slots, not unused backend buffer memory.
            for i,target in enumerate(setup['filters']):
                start,count=int(starts[0,i]),int(counts[0,i])
                if not count:continue
                chunks=[numeric(data[k][start:start+count],(count,width)) for k,width in enumerate((1,3,3,1))]
                detail_rows.append(dict(other=target,points_world_m=chunks[1].tolist(),
                    normals_world=chunks[2].tolist(),normal_force_n=chunks[0][:,0].tolist(),
                    separation_m=chunks[3][:,0].tolist()))
        if native.errors:raise ValueError('Native physics error during read: '+native.errors[-1])
        return dict(net=dict(value=net.tolist(),reason=None),table=dict(value=force.tolist(),reason=None),
                    counts=counts.tolist(),validation=validated,
                    details=detail_rows if details else None,
                    status='api_validated_not_externally_calibrated',table_contact_evidence='reported contact points' if np.any(counts>0) else 'no reported points this step; not proof of separation')
    except Exception as e:
        return dict(net=missing(repr(e)),table=missing(repr(e)),counts=None,validation=None,status='invalid_or_unverified',table_contact_evidence='unknown')
