"""CPU USD/convex geometry checks and orthographic previews; NOT a PhysX test."""
from pathlib import Path
import json
import hashlib
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from pxr import Usd, UsdGeom, UsdPhysics

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'logs/bread_slot_validation'
ASSETS = ROOT/'source/cyclo_lab/data/objects'

def mesh_points(stage, prim):
    mesh = UsdGeom.Mesh(prim)
    matrix = np.asarray(mesh.ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    return np.asarray(mesh.GetPointsAttr().Get()) @ matrix[:3,:3] + matrix[3,:3]

def rotation(q):
    return Rotation.from_quat([*q[1:], q[0]]).as_matrix()

def triangle_intersects_hull(triangle, equations):
    # Clip each rack surface triangle against the closed convex bread collider.
    if np.any(np.all(triangle @ equations[:,:3].T + equations[:,3] > 1e-10, axis=0)):
        return False
    polygon = list(triangle)
    for plane in equations:
        clipped = []
        for a,b in zip(polygon, polygon[1:]+polygon[:1]):
            da,db = a @ plane[:3]+plane[3], b @ plane[:3]+plane[3]
            if da <= 0: clipped.append(a)
            if (da <= 0) != (db <= 0): clipped.append(a+(b-a)*(da/(da-db)))
        polygon = clipped
        if not polygon: return False
    return True

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source=Usd.Stage.Open(str(ASSETS/'bread_slot/bread_slot.usdz'))
    assert UsdGeom.GetStageMetersPerUnit(source)==.001 and UsdGeom.GetStageUpAxis(source)=='Y'
    assert len([p for p in source.Traverse() if p.IsA(UsdGeom.Mesh)])==1
    assert not any(p.HasAPI(UsdPhysics.RigidBodyAPI) or p.HasAPI(UsdPhysics.CollisionAPI)
                   or p.IsA(UsdPhysics.Joint) for p in source.Traverse())
    stage=Usd.Stage.Open(str(ASSETS/'bread_slot/rack.usda'))
    colliders=[p for p in stage.Traverse() if p.HasAPI(UsdPhysics.CollisionAPI)]
    assert len(colliders)==1
    assert not any(p.HasAPI(UsdPhysics.RigidBodyAPI) for p in stage.Traverse())
    prim=colliders[0];mesh=UsdGeom.Mesh(prim)
    assert UsdPhysics.MeshCollisionAPI(prim).GetApproximationAttr().Get()=='none'
    assert all(n==3 for n in mesh.GetFaceVertexCountsAttr().Get())
    v=mesh_points(stage,prim);f=np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1,3)
    np.testing.assert_allclose(np.ptp(v,axis=0),[.23,.13,.045],atol=1e-7)
    np.testing.assert_allclose(v.min(0)[2],(.994051338865205 - 1.0382),atol=1e-7)
    breadstage=Usd.Stage.Open(str(ASSETS/'robodojo_make_toast/bread/object.usdz'))
    bp=breadstage.GetPrimAtPath('/World/collision')
    assert UsdPhysics.MeshCollisionAPI(bp).GetApproximationAttr().Get()=='convexHull'
    b=mesh_points(breadstage,bp)
    manifest=json.loads((ROOT/'scenario_delivery/manifest_bread_slot.json').read_text())
    old=json.loads((ROOT/'scenario_delivery/manifest.json').read_text())
    assert len(manifest['scenarios'])==100
    for before,after in zip(old['scenarios'],manifest['scenarios']):
        for key in ('id','operator','order_positive_to_negative_y'): assert before[key]==after[key]
        for name in ('toaster','plate','bread_shelf'):
            assert before['poses'][name]['position_m']==after['poses'][name]['position_m']
            assert before['poses'][name]['quaternion_wxyz']==after['poses'][name]['quaternion_wxyz']
    positions=[]; hulls=[]
    for i in range(4):
        p=manifest['baseline_bread'][f'bread_{i}'];s=manifest['baseline']['bread_shelf'];rs=rotation(s['quaternion_wxyz'])
        rb=rotation(p['quaternion_wxyz']);offset=(np.asarray(p['position_m'])-s['position_m'])@rs
        points=b@rb.T@rs+offset
        hull=ConvexHull(points)
        assert not any(triangle_intersects_hull(t,hull.equations) for t in v[f]), f'bread_{i} penetrates rack'
        # Lower by 1 mm: contact must occur, excluding suspended initial placement.
        lower=points-[0,0,.001];lowerhull=ConvexHull(lower)
        assert any(triangle_intersects_hull(t,lowerhull.equations) for t in v[f]), 'No support within 1 mm'
        positions.append(points);hulls.append(hull)
    # Conservative XY hull includes both rack and all four unchanged bread hulls.
    local = np.concatenate([v, *positions])
    table = ConvexHull(np.asarray(old['extracted_table_support']['convex_surface_polygons_xy'][0]))
    minimum_table_margin = float('inf')
    minimum_axis_gap = float('inf')
    for entry,previous in zip(manifest['scenarios'],old['scenarios']):
        pose=entry['poses']['bread_shelf']
        world=local@rotation(pose['quaternion_wxyz']).T+pose['position_m']
        xy=world[:,:2];poly=xy[ConvexHull(xy).vertices]
        margin=-(poly@table.equations[:,:2].T+table.equations[:,2]).max()
        minimum_table_margin=min(minimum_table_margin,float(margin))
        assert margin>.02, (entry['id'],margin)
        for name in ('toaster','plate'):
            other=np.asarray(previous['footprints_xy'][name])
            axes=[]
            for polygon in (poly,other):
                edges=np.roll(polygon,-1,axis=0)-polygon
                axes.extend(np.stack([-edges[:,1],edges[:,0]],axis=1))
            gaps=[]
            for axis in axes:
                axis=axis/np.linalg.norm(axis);pa=poly@axis;pb=other@axis
                gaps.append(max(pb.min()-pa.max(),pa.min()-pb.max()))
            gap=max(gaps);minimum_axis_gap=min(minimum_axis_gap,float(gap))
            assert gap>.03, (entry['id'],name,gap)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    for name,elev,azim in [('front',8,-90),('top',90,-90),('oblique',30,-55)]:
        fig=plt.figure(figsize=(11,7));ax=fig.add_subplot(projection='3d')
        ax.add_collection3d(Poly3DCollection(v[f],facecolors='#9aa7ad',edgecolors='#53616b',linewidths=.06,alpha=.8))
        for i,(points,hull) in enumerate(zip(positions,hulls)):
            ax.add_collection3d(Poly3DCollection(points[hull.simplices],facecolors=['#e7b56a','#ddb270','#c99a55','#ba904e'][i],edgecolors='none'))
        ax.set(xlim=(-.125,.125),ylim=(-.075,.075),zlim=(-.04415,.115),xlabel='rack X (m)',ylabel='rack Y (m)',zlabel='rack Z (m)')
        ax.set_box_aspect((.25,.15,.1532));ax.set_proj_type("ortho");ax.view_init(elev,azim)
        if name == "top":
            ax.set_zticks([]);ax.set_zlabel("");ax.grid(False)
        ax.set_title('CPU USD geometry + exact authored collision triangles; NOT simulation')
        fig.savefig(OUT/f'{name}.png',dpi=160);plt.close(fig)
    result=dict(native_dimensions_m=np.ptp(v,axis=0).tolist(),collision=str(prim.GetPath()),
                collision_approximation='none (static triangle mesh)',bread_rack_intersections=0,
                support_within_m=.001,scenarios_preserved=100,
                minimum_table_edge_margin_m=minimum_table_margin,
                minimum_separating_axis_gap_to_other_objects_m=minimum_axis_gap,
                source_sha256=hashlib.sha256((ASSETS/'bread_slot/bread_slot.usdz').read_bytes()).hexdigest(),
                physics_runtime_verified=False,robot_grasp_verified=False)
    (OUT/'geometry_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
