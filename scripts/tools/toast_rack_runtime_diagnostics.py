"""Read live composed colliders/RGB; optional PhysX contact reports (not shape edits)."""
import json
from pathlib import Path

def reporting_spawner(original):
    # Isaac's activate_contact_sensors helper also changes sleepThreshold: do not use it.
    def spawn(*args,**kwargs):
        from pxr import Usd,UsdPhysics,PhysxSchema
        root=original(*args,**kwargs)
        for p in Usd.PrimRange(root):
            if p.HasAPI(UsdPhysics.RigidBodyAPI):
                PhysxSchema.PhysxContactReportAPI.Apply(p).CreateThresholdAttr(0.)
        return root
    return spawn

def capture(env,out,sid,label):
    import numpy as np
    from pxr import Usd,UsdGeom,UsdPhysics
    from PIL import Image
    result={'label':label,'colliders':[],'cameras':{},'cooked_geometry':'NOT_EXPORTED; composed USD is not the cooked PhysX mesh'}
    for p in env.scene.stage.Traverse():
        if 'bread' not in str(p.GetPath()).lower() or not p.HasAPI(UsdPhysics.CollisionAPI):continue
        item=dict(path=str(p.GetPath()),collision_enabled=UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr().Get(),
                  approximation=UsdPhysics.MeshCollisionAPI(p).GetApproximationAttr().Get(),
                  world_matrix=np.asarray(UsdGeom.Xformable(p).ComputeLocalToWorldTransform(Usd.TimeCode.Default())).tolist(),
                  physics_attributes={a.GetName():str(a.Get()) for a in p.GetAttributes() if 'physics' in a.GetName().lower()})
        if p.IsA(UsdGeom.Mesh):
            m=UsdGeom.Mesh(p);item.update(points=np.asarray(m.GetPointsAttr().Get()).tolist(),indices=list(m.GetFaceVertexIndicesAttr().Get()),counts=list(m.GetFaceVertexCountsAttr().Get()),orientation=m.GetOrientationAttr().Get())
        result['colliders'].append(item)
    for name,camera in env.scene.sensors.items():
        try:
            rgb=camera.data.output.get('rgb')
            if rgb is None:continue
            values=rgb[0].detach().cpu().numpy()
            if values.dtype!=np.uint8:values=(np.clip(values,0,1)*255).astype(np.uint8)
            path=Path(out)/f'{sid}.{label}.{name}.png';Image.fromarray(values[:,:,:3]).save(path)
            result['cameras'][name]=path.name
        except Exception as exc:result['cameras'][name]={'error':repr(exc)}
    (Path(out)/f'{sid}.{label}.colliders.json').write_text(json.dumps(result,indent=2)+'\n')

class Contacts:
    def __init__(self,env,out,sid):
        import omni.physx
        from pxr import PhysxSchema,UsdPhysics,PhysicsSchemaTools
        self.file=(Path(out)/f'{sid}.contacts.jsonl').open('w');self.steps=0;self.errors=[]
        for p in env.scene.stage.Traverse():
            if 'bread_' in str(p.GetPath()).lower() and p.HasAPI(UsdPhysics.RigidBodyAPI):
                PhysxSchema.PhysxContactReportAPI.Apply(p).CreateThresholdAttr(0.)
        def callback(headers,data):
            try:
                for h in headers:
                    row={'callback':self.steps,'type':str(h.type)}
                    for key in ('actor0','actor1','collider0','collider1'):
                        value=getattr(h,key,None)
                        row[key]=str(PhysicsSchemaTools.intToSdfPath(value)) if value is not None else None
                    offset=getattr(h,'contact_data_offset',0);count=getattr(h,'num_contact_data',0)
                    row['contacts']=[{'position':list(x.position),'normal':list(x.normal),'impulse':list(x.impulse),'separation':float(x.separation)} for x in (data[i] for i in range(offset,offset+count))]
                    self.file.write(json.dumps(row)+'\n')
                self.steps+=1;self.file.flush()
            except Exception as exc:
                if len(self.errors)<100:self.errors.append(repr(exc))
        self.subscription=omni.physx.get_physx_simulation_interface().subscribe_contact_report_events(callback)
    def close(self):
        self.subscription=None;self.file.close()
