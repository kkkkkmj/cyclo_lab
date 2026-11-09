"""Offline SVG card visualization; no scenario, asset or verification edits."""
import csv,json,hashlib,html
from pathlib import Path
import numpy as np
from pxr import Usd,UsdGeom
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import polygons, area, union_all
from shapely.affinity import affine_transform
from check_bread_slot_geometry import rotation
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'scenario_delivery'
SOURCE=ROOT/'scenario_delivery/inputs/table_frame.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mesh_parts(path):
 s=Usd.Stage.Open(str(path));root=s.GetDefaultPrim();inv=np.linalg.inv(np.array(UsdGeom.Xformable(root).ComputeLocalToWorldTransform(0)));parts=[]
 for p in Usd.PrimRange(root):
  if not p.IsA(UsdGeom.Mesh) or 'collision' in str(p.GetPath()).lower():continue
  m=UsdGeom.Mesh(p);t=np.array(m.ComputeLocalToWorldTransform(0))@inv
  v=np.array(m.GetPointsAttr().Get())@t[:3,:3]+t[3,:3]
  idx=list(m.GetFaceVertexIndicesAttr().Get());counts=list(m.GetFaceVertexCountsAttr().Get());faces=[];offset=0
  for count in counts:faces.append(idx[offset:offset+count]);offset+=count
  parts.append((v,faces))
 return parts

def project(parts,pose,top=False):
 groups=[];r=rotation(pose['quaternion_wxyz']);scale=np.array(pose['scale']);pos=np.array(pose['position_m'])
 for v,faces in parts:
  world=(v*scale)@r.T+pos
  triangles=np.array([[f[0],f[i],f[i+1]] for f in faces for i in range(1,len(f)-1)])
  if top:
   vv=v[triangles,2];triangles=triangles[(np.ptp(vv,axis=1)<1e-7)&(np.abs(vv.mean(1)-v[:,2].max())<1e-7)]
  if not len(triangles):continue
  shapes=polygons(world[triangles,:2]);shapes=shapes[area(shapes)>1e-12]
  if len(shapes):groups.append(union_all(shapes))
 return unary_union(groups).simplify(1e-6,preserve_topology=True)

def svgpath(geom):
 polys=list(geom.geoms) if geom.geom_type=='MultiPolygon' else [geom]
 def ring(points):return 'M'+' L'.join(f'{-y*1000:.3f},{-x*1000:.3f}' for x,y in points)+'Z'
 return ''.join(ring(p.exterior.coords)+''.join(ring(i.coords) for i in p.interiors) for p in polys if p.geom_type=='Polygon')

def main():
 manifest=OUT/'manifest.json';assign=OUT/'assignments.csv';data=json.loads(manifest.read_text());rows=list(csv.DictReader(assign.open()))
 assert len(rows)==len(data['scenarios'])==100 and len({r['scenario_id'] for r in rows})==100
 byid={e['id']:e for e in data['scenarios']};assert set(byid)=={r['scenario_id'] for r in rows}
 for r in rows:
  assert r['scenario_id'].startswith('toast_v20261108_')
  for key in ('operator','scenario_group','operator_index','group_index'):assert str(byid[r['scenario_id']][key])==r[key]
 for g in data['generation']['groups']:assert sorted(int(r['group_index']) for r in rows if r['scenario_group']==g)==list(range(1,26))
 # Independent authored world mesh snapshot, with current same table configuration.
 table=json.loads(SOURCE.read_text());assert 'pos=[0.7, -0.1, 0.0]' in table['table_initial_state']
 cfg=(ROOT/'source/cyclo_lab/cyclo_lab/manager_based/manipulation/pick_place/config/ffw_bg2/pick_place_env_cfg.py').read_text()
 assert 'pos=[0.70, -0.1, 0.0]' in cfg and 'rot=[-0.70710678, 0.0, 0.0, 0.70710678]' in cfg and 'scale=(1.0, 1.0, 1.0)' in cfg
 lo,hi=np.asarray(table['frame_bounds_m'])
 frame=Polygon([(lo[0],lo[1]),(hi[0],lo[1]),(hi[0],hi[1]),(lo[0],hi[1])])
 support=Polygon(data['extracted_table_support']['convex_surface_polygons_xy'][0])
 top_points=np.asarray(table['table_top_points'])
 measured=Polygon(top_points[ConvexHull(top_points[:,:2]).vertices,:2]);assert measured.hausdorff_distance(support)<1e-5
 assets=ROOT/'source/cyclo_lab/data/objects';paths={n:assets/'robodojo_make_toast'/n/'object.usdz' for n in ('toaster','plate','bread')};paths['bread_shelf']=assets/'bread_slot/rack.usda'
 parts={n:mesh_parts(p) for n,p in paths.items()};assert all(parts.values())
 view=f'{-hi[1]*1000-35:.3f} {-hi[0]*1000-85:.3f} {(hi[1]-lo[1])*1000+70:.3f} {(hi[0]-lo[0])*1000+145:.3f}'
 payload=[];local={};bases={};cache={}
 for n,pose in {**data['baseline'],**data['baseline_bread']}.items():
  asset='bread' if n.startswith('bread_') and n!='bread_shelf' else n
  q=pose['quaternion_wxyz'];scale=data['scales'].get(n,[1,1,1]);key=(asset,tuple(q),tuple(scale))
  if key not in cache:cache[key]=project(parts[asset],dict(position_m=[0,0,0],quaternion_wxyz=q,scale=scale))
  local[n]=cache[key];bases[n]=rotation(q)
 shelf=data['baseline']['bread_shelf'];toplocal=project(parts['bread_shelf'],dict(position_m=[0,0,0],quaternion_wxyz=shelf['quaternion_wxyz'],scale=data['scales']['bread_shelf']),top=True)
 def moved(poly,n,pose):
  r=rotation(pose['quaternion_wxyz'])@bases[n].T
  assert np.allclose(r[2],[0,0,1],atol=1e-6)
  return affine_transform(poly,[r[0,0],r[0,1],r[1,0],r[1,1],*pose['position_m'][:2]])
 for row in rows:
  e=byid[row['scenario_id']];shapes={n:svgpath(moved(local[n],n,p)) for n,p in e['poses'].items()}
  top=svgpath(moved(toplocal,'bread_shelf',e['poses']['bread_shelf']))
  payload.append(dict(id=e['id'],operator=e['operator'],group=e['scenario_group'],index=e['group_index'],operator_index=e['operator_index'],order=e['order_positive_to_negative_y'],shapes=shapes,rack_top=top))
 meta=dict(manifest_sha256=sha(manifest),assignments_sha256=sha(assign),asset_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths.values()},table_snapshot=str(SOURCE.relative_to(ROOT)),table_snapshot_sha256=sha(SOURCE),frame_bounds_m=[lo.tolist(),hi.tolist()],table_support=list(support.exterior.coords),table_check='Current pose/scale matched to local authored world mesh snapshot; tabletop independently matches manifest support polygon. Frame is mesh AABB, not support.',viewBox=view)
 template=Path(__file__).with_name('toast_overview_cards_template.html').read_text()
 output=template.replace('__DATA__',json.dumps(payload,separators=(',',':'))).replace('__META__',json.dumps(meta,separators=(',',':'))).replace('__FRAME__',svgpath(frame)).replace('__SUPPORT__',svgpath(support)).replace('__VIEWBOX__',view)
 (OUT/'overview_cards.html').write_text(output)
 print(json.dumps(dict(count=len(payload),frame_bounds=meta['frame_bounds_m'],output=str(OUT/'overview_cards.html')),indent=2))
if __name__=='__main__':main()
