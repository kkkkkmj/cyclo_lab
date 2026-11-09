"""Analyze preserved PhysX trace against authored collision geometry, not cooked contacts."""
import argparse,json,gzip,sys
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from pxr import Usd,UsdGeom,UsdPhysics
from check_bread_slot_geometry import mesh_points,rotation,triangle_intersects_hull,ROOT,ASSETS
from validate_toast_collection import sha

def clip(t,eq):
    if np.any(np.all(t@eq[:,:3].T+eq[:,3]>1e-10,axis=0)):return []
    poly=list(t)
    for plane in eq:
        out=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            da=a@plane[:3]+plane[3];db=b@plane[:3]+plane[3]
            if da<=0:out.append(a)
            if (da<=0)!=(db<=0):out.append(a+(b-a)*da/(da-db))
        poly=out
        if not poly:break
    return poly

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    result=json.loads(args.input.read_text());sid=result['scenario_id']
    rack=Usd.Stage.Open(str(ASSETS/'bread_slot/rack.usda'));rp=next(p for p in rack.Traverse() if p.HasAPI(UsdPhysics.CollisionAPI));mesh=UsdGeom.Mesh(rp)
    rv=mesh_points(rack,rp);tri=rv[np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1,3)]
    bread=Usd.Stage.Open(str(ASSETS/'robodojo_make_toast/bread/object.usdz'));bv=mesh_points(bread,bread.GetPrimAtPath('/World/collision'))
    report={'source':str(args.input),'source_sha256':sha(args.input),'runtime_cooked_contacts':'NOT_RECORDED_IN_OLD_TRACE','runs':[]};candidate={};plots=[]
    for k,run in enumerate(result['runs']):
        frames=[json.loads(line) for line in gzip.open(args.input.parent/run['trace'],'rt')]
        row=dict(run=k+1,robot_max_joint_drift=run['robot_max_joint_drift'],events=run['events'],bread={})
        for i in range(4):
            n=f'bread_{i}';o=run['objects'][n];s=run['objects']['bread_shelf']['initial'];rs=rotation(s['quaternion'])
            samples=[]
            for index in (0,9,24,49,99,len(frames)-1):
                f=frames[min(index,len(frames)-1)];samples.append(dict(physics_sample=f['physics_sample'],**f['pose'][n]))
            states={}
            for name in ('initial','final'):
                x=o[name];world=bv@rotation(x['quaternion']).T+x['position'];local=(world-s['position'])@rs
                eq=ConvexHull(local-([0,0,.001] if name=='initial' else [0,0,0])).equations
                contact=np.array([q for t in tri for q in clip(t,eq)])
                states[name]=dict(world_collision_min_z=float(world[:,2].min()),root_rack_local=((np.array(x['position'])-s['position'])@rs).tolist(),
                    clipped_contact_bounds=[] if not len(contact) else [contact.min(0).tolist(),contact.max(0).tolist()],
                    contact_method='initial: shifted down1mm; final: unchanged authored convex vs triangles')
                if k==0:plots.append((i,name,local))
            if k==0:
                # Measured resting orientation/XY plus minimum upward nonintersection clearance.
                x=o['final'];local=(bv@rotation(x['quaternion']).T+x['position']-np.array(s['position']))@rs
                def hits(dz):
                    eq=ConvexHull(local+[0,0,dz]).equations
                    return any(triangle_intersects_hull(t,eq) for t in tri)
                lo=0.;hi=.03
                if hits(hi):raise RuntimeError('No safe seated candidate within30mm')
                for _ in range(20):
                    mid=(lo+hi)/2
                    if hits(mid):lo=mid
                    else:hi=mid
                pos=np.array(x['position']);pos[2]+=hi+.0003
                candidate[n]=dict(position_m=pos.tolist(),quaternion_wxyz=x['quaternion'],clearance_raise_m=hi+.0003)
            row['bread'][n]=dict(delta=(np.array(o['final']['position'])-o['initial']['position']).tolist(),max_rotation_deg=o['max_rotation_deg'],final_speed=o['final_linear_speed_m_s'],states=states,samples=samples)
        report['runs'].append(row)
    manifest=ROOT/'scenario_delivery/manifest.json'
    proposal=dict(version='seated_candidate_v1',status='EXPERIMENTAL_NOT_RUNTIME_VERIFIED',scenario_id=sid,manifest_sha256=sha(manifest),
        source_result_sha256=sha(args.input),method='Measured final orientation and XY; upward exact-authored-convex nonintersection search +0.3mm, not uniform lowering',poses=candidate)
    (out/'analysis.json').write_text(json.dumps(report,indent=2)+'\n');(out/'seated_candidate_v1.json').write_text(json.dumps(proposal,indent=2)+'\n')
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    for state in ('initial','final'):
        fig=plt.figure(figsize=(10,6));ax=fig.add_subplot(projection='3d')
        ax.add_collection3d(Poly3DCollection(tri,facecolor='#8497a1',alpha=.35,edgecolor='#65747b',linewidth=.1))
        for i,n,v in plots:
            if n==state:ax.add_collection3d(Poly3DCollection(v[ConvexHull(v).simplices],facecolor=['#e8be76','#e0ab69','#d19c5c','#c5934f'][i],alpha=.65))
        ax.set(xlim=(-.12,.12),ylim=(-.07,.07),zlim=(-.05,.12),xlabel='rack X m',ylabel='rack Y m',zlabel='rack Z m')
        ax.set_box_aspect((.24,.14,.17));ax.view_init(elev=18,azim=20)
        ax.set_title(state+': recorded PhysX pose + authored collision geometry (NOT simulator screenshot)')
        fig.savefig(out/(state+'_collision_reconstruction.png'),dpi=150);plt.close(fig)
    print(json.dumps(candidate,indent=2))
if __name__=='__main__':main()
