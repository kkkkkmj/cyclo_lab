"""Read-only USD/runtime evidence. Missing values remain unknown, never cfg defaults."""
import json
from pathlib import Path
import time


def plain(value):
    if hasattr(value,'detach'):return value.detach().cpu().tolist()
    if value is None or isinstance(value,(str,bool,int,float)):return value
    if isinstance(value,dict):return {str(k):plain(v) for k,v in value.items()}
    try:return [plain(v) for v in value]
    except TypeError:return str(value)


def emit(env,kind,report):
    report=dict(report,kind=kind,wall_monotonic=time.monotonic(),episode=getattr(env,'_replay_audit_episode',None))
    directory=getattr(env,'_replay_audit_dir',None)
    if directory:
        with (Path(directory)/'audit.jsonl').open('a') as file:file.write(json.dumps(plain(report))+'\n')
    return report


def runtime_properties(env):
    from pxr import Usd,UsdPhysics,UsdShade
    from isaacsim.core.utils.stage import get_current_stage
    from isaaclab.sim import find_matching_prim_paths
    stage=get_current_stage()
    def attrs(prim):
        result={}
        for attr in prim.GetAttributes():
            name=attr.GetName()
            if name.startswith(('physics:','physx','collision')):
                value=attr.Get()
                result[name]=dict(value=plain(value),resolved=value is not None,authored=attr.HasAuthoredValueOpinion(),
                                  source='USD resolved value/schema fallback; not automatically a queried PhysX value')
        return result
    result={'bodies':{},'scene_prims':{},'limitations':[
        'USD resolved values and live PhysX getter values are separate evidence.',
        'Unavailable tensor getters are unknown, not inferred from cfg None.',
        'Solver/contact manifold and historical cooked-mesh caches are not serialized.']}
    for name in ('plate','table'):
        cfg=getattr(env.cfg.scene,name)
        pattern=cfg.prim_path.replace('{ENV_REGEX_NS}',env.scene.env_prim_paths[0])
        matches=find_matching_prim_paths(pattern)
        path=next((p for p in matches if p.startswith(env.scene.env_prim_paths[0]+'/')),matches[0] if matches else None)
        root=stage.GetPrimAtPath(path) if path else Usd.Prim()
        body={'path':path,'pattern':pattern,'matches':matches,'usd':{},'live_physx':{}}
        if root.IsValid():
            for prim in Usd.PrimRange(root):
                if not (prim.HasAPI(UsdPhysics.CollisionAPI) or prim.HasAPI(UsdPhysics.RigidBodyAPI)):continue
                entry={'attributes':attrs(prim),'type':prim.GetTypeName()}
                try:
                    material,relation=UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial(materialPurpose='physics')
                    entry['bound_physics_material']=str(material.GetPath()) if material else None
                    entry['material_attributes']=attrs(material.GetPrim()) if material else {}
                    entry['binding_relationship']=str(relation.GetPath()) if relation else None
                except Exception as error:entry['material_query_error']=str(error)
                body['usd'][str(prim.GetPath())]=entry
        else:body['usd_error']='prim not found'
        asset=env.scene.rigid_objects.get(name)
        if asset is not None:
            view=asset.root_physx_view
            for method in ('get_masses','get_inertias','get_coms','get_material_properties','get_contact_offsets','get_rest_offsets','get_solver_position_iteration_counts','get_solver_velocity_iteration_counts'):
                try:
                    getter=getattr(view,method,None)
                    body['live_physx'][method]={'status':'queried','value':plain(getter())} if callable(getter) else {'status':'unavailable'}
                except Exception as error:body['live_physx'][method]={'status':'query_failed','error':str(error)}
        else:body['live_physx']['status']='no existing rigid tensor view (static table); USD evidence only'
        result['bodies'][name]=body
    for prim in stage.Traverse():
        if prim.IsA(UsdPhysics.Scene):result['scene_prims'][str(prim.GetPath())]=attrs(prim)
    emit(env,'runtime_physics',result)
    print('RUNTIME_PHYSICS '+json.dumps(result),flush=True)
    return result


class TimelineProbe:
    def __init__(self,env):
        self.env=env;self.counts={name:0 for name in ('step','forward','render')};self.original={}
        for name in self.counts:
            original=getattr(env.sim,name);self.original[name]=original
            def wrapper(*args,_name=name,_original=original,**kwargs):
                self.counts[_name]+=1
                return _original(*args,**kwargs)
            setattr(env.sim,name,wrapper)
    def mark(self,stage):
        report=dict(stage=stage,public_sim_calls=dict(self.counts),env_physics_counter=self.env._sim_step_counter)
        for name in ('current_time','current_time_step_index'):
            try:report[name]=plain(getattr(self.env.sim,name))
            except Exception as error:report[name]={'status':'unavailable','error':str(error)}
        report['plate_physx_velocity']=plain(self.env.scene['plate'].root_physx_view.get_velocities())
        emit(self.env,'timeline',report);print('REPLAY_TIMELINE '+json.dumps(report),flush=True)
    def close(self):
        for name,original in self.original.items():setattr(self.env.sim,name,original)
