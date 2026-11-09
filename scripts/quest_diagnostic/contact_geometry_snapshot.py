"""Read-only composed USD geometry snapshot; NOT cooked PhysX shape calibration.
No physics/render/update call. Mesh vertices retain faces for later CPU analysis.
"""
import itertools
import numpy as np
from pxr import Usd,UsdGeom,Gf
from contact_probe import rotation

def geometry_record(stage,path,body_path=None,body_pose_xyzw=None):
    prim=stage.GetPrimAtPath(path)
    if not prim:raise ValueError('Missing collider '+path)
    cache=UsdGeom.XformCache();result=dict(path=path,type=prim.GetTypeName(),schemas=prim.GetAppliedSchemas(),
        attributes={a.GetName():dict(value=str(a.Get()),authored=a.HasAuthoredValueOpinion(),sources=[str(s.layer.identifier) for s in a.GetPropertyStack()]) for a in prim.GetAttributes() if a.GetName().startswith(('physics:','physx'))},
        transform_source='PhysX body transform + composed USD relative mesh transform' if body_pose_xyzw is not None else 'composed static USD transform',
        meshes=[],world_vertex_bounds=None,cooked_physx_shape=None,cooked_shape_reason='Not queried; source mesh bounds are not cooked contact geometry',
        world_from_collider_usd=np.array(cache.GetLocalToWorldTransform(prim)).T.tolist())
    world=[]
    for mesh in Usd.PrimRange(prim,Usd.TraverseInstanceProxies()):
        if mesh.IsA(UsdGeom.Mesh):
            g=UsdGeom.Mesh(mesh);pts=g.GetPointsAttr().Get()
            if pts is None:continue
            pts=np.array(pts,dtype=float);faces=dict(counts=list(g.GetFaceVertexCountsAttr().Get() or []),indices=list(g.GetFaceVertexIndicesAttr().Get() or []))
        elif mesh.IsA(UsdGeom.Cube):
            size=float(UsdGeom.Cube(mesh).GetSizeAttr().Get());pts=np.array(list(itertools.product([-.5*size,.5*size],repeat=3)));faces=None
        else:continue
        if body_pose_xyzw is None:M=np.array(cache.GetLocalToWorldTransform(mesh)).T
        else:
            if not body_path:raise ValueError('Body path required for PhysX transform')
            local=np.array(cache.ComputeRelativeTransform(mesh,stage.GetPrimAtPath(body_path))[0]).T
            p=body_pose_xyzw;B=np.eye(4);B[:3,:3]=rotation([p[6],*p[3:6]]);B[:3,3]=p[:3];M=B@local
        q=pts@M[:3,:3].T+M[:3,3]
        if not np.isfinite(q).all():raise ValueError('Nonfinite geometry')
        result['meshes'].append(dict(path=str(mesh.GetPath()),type=mesh.GetTypeName(),world_points=q.tolist(),faces=faces));world.extend(q.tolist())
    if world:
        a=np.array(world);result['world_vertex_bounds']=[a.min(0).tolist(),a.max(0).tolist()]
    else:result['unavailable_reason']='No resolved Mesh/Cube descendants; no bound inferred'
    return result

def snapshot(env,probe,initial):
    stage=env.sim.stage;robot=env.scene['robot'];poses=robot.root_physx_view.get_link_transforms()[0].detach().cpu().numpy()
    out=dict(phase='after_episode_reset_before_commanded_physics',physics_step_global=int(env._sim_step_counter),
        meters_per_unit=UsdGeom.GetStageMetersPerUnit(stage),up_axis=str(UsdGeom.GetStageUpAxis(stage)),
        initial_eef_poses={k:v.detach().cpu().tolist() for k,v in initial.items()},
        table_spawn=str(env.cfg.scene.table.spawn),table_initial_state=str(env.cfg.scene.table.init_state),
        table=[],fingers=[],errors=[],note='USD geometry and actual initial PhysX link poses only; no contact or cooked-shape verification. No approach route is automatically approved.')
    from pxr import UsdPhysics
    for path in probe.table_setup['colliders']:
        try:out['table'].append(geometry_record(stage,path))
        except Exception as e:out['errors'].append(dict(path=path,error=repr(e)))
    for f in probe.frames:
        body=f['bodies'][1]
        for prim in Usd.PrimRange(stage.GetPrimAtPath(body),Usd.TraverseInstanceProxies()):
            if not prim.HasAPI(UsdPhysics.CollisionAPI):continue
            path=str(prim.GetPath())
            try:
                row=geometry_record(stage,path,body,poses[f['body_indices'][1]])
                row.update(body=body,joint=f['name']);out['fingers'].append(row)
            except Exception as e:out['errors'].append(dict(path=path,error=repr(e)))
    return out
