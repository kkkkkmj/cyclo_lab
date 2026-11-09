"""Offline geometry audit and transform checks; does not produce PhysX measurements."""
import hashlib
import json
from pathlib import Path
import numpy as np
from pxr import Gf, Usd, UsdGeom
from exposure_geometry import bake_bread, bake_rim, world, measure

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSETS = ROOT/'source/cyclo_lab/data/objects/robodojo_make_toast'


def main():
    bread_path, toaster_path = ASSETS/'bread/object.usdz', ASSETS/'toaster/object.usdz'
    bread = Usd.Stage.Open(str(bread_path))
    toaster = Usd.Stage.Open(str(toaster_path))
    bv, be = bake_bread(bread.GetDefaultPrim())
    rv, re = bake_rim(toaster.GetPrimAtPath('/root/base'))
    # Independent reference: Gf.Transform each original point for arbitrary pose.
    q = Gf.Quatd(np.cos(.31), Gf.Vec3d(0, np.sin(.31), 0))
    rigid = Gf.Matrix4d(1)
    rigid.SetRotate(q)
    rigid.SetTranslateOnly(Gf.Vec3d(.25, -.1, 1.2))
    actual = world(bv, [.25,-.1,1.2], [q.GetReal(), *q.GetImaginary()])
    expected = np.array([rigid.Transform(Gf.Vec3d(*p)) for p in bv])
    np.testing.assert_allclose(actual, expected, atol=1e-12)
    # Explicit nonuniform root scale plus child transforms must survive baking.
    test = Usd.Stage.CreateInMemory()
    root = UsdGeom.Xform.Define(test, '/Bread')
    root.AddTranslateOp().Set(Gf.Vec3d(1,2,3))
    root.AddRotateZOp().Set(37.)
    root.AddScaleOp().Set(Gf.Vec3f(2,3,4))
    child = UsdGeom.Mesh.Define(test, '/Bread/Visual')
    child.AddTranslateOp().Set(Gf.Vec3d(.1,.2,.3))
    child.CreatePointsAttr([(0,0,0),(1,0,0),(0,1,1)])
    child.CreateSubdivisionSchemeAttr('none')
    baked, _ = bake_bread(root.GetPrim())
    np.testing.assert_allclose(baked, [[.2,.6,1.2],[2.2,.6,1.2],[.2,3.6,5.2]], atol=1e-6)
    # Tilted deck must evaluate Z at bread center XY, not use its highest corner.
    rim = np.array([[-1,-1,-.1],[1,-1,.3],[1,1,.3],[-1,1,-.1]])
    visual = np.array([[.4,-.1,-.2],[.6,.1,.4]])
    values, _, _ = measure(visual, rim)
    np.testing.assert_allclose([values['z_rim'], values['height_mm'],values['exposed_mm']], [.2,600,200], atol=1e-8)
    for dz, pct in [(-2,0), (2,100)]:
        shifted = visual + [0,0,dz]
        assert abs(measure(shifted,rim)[0]['exposed_pct']-pct)<1e-8
    report = dict(status='STATIC_GEOMETRY_VERIFIED_NOT_SIMULATION',
        assets={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (bread_path,toaster_path)},
        bread=be, bread_vertices=len(bv), rim=re,
        checks=['All bread mesh points vs independent Gf rigid transformation',
                'Nonuniform scale and composed parent/child transforms',
                'Tilted rim plane evaluated at bread visual center XY', 'Exposure clamps at 0 and 100 percent'],
        note='Asset geometry and synthetic math checks only. No actual toast exposure values have been measured.')
    (HERE/'static_geometry_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    # Top view of the reviewed real deck faces: opening is explicitly not a face.
    colors = ['#bfd7e8','#aed5c3','#f3d3a2','#dbbfe8']
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="780" viewBox="0 0 1000 780">',
           '<rect width="1000" height="780" fill="white"/>',
           '<text x="30" y="30" font-size="20">Actual toaster deck mesh, top view: base_body_30 faces 0-13</text>',
           '<text x="30" y="60" font-size="16">Static asset geometry only. Black gaps are the two slot openings.</text>']
    def xy(p):
        return [500+3600*p[0], 400-3600*p[1]]
    for i, poly in enumerate(re['face_vertices_body_m']):
        poly = np.asarray(poly)
        points = ' '.join(f'{x:.2f},{y:.2f}' for x,y in map(xy,poly))
        svg.append(f'<polygon points="{points}" fill="{colors[i%4]}" stroke="#555"/>')
        x,y = xy(poly.mean(0))
        svg.append(f'<text x="{x}" y="{y}" font-size="16">{i}</text>')
    for slot,y in enumerate((-.026455,.0253585)):
        x,py=xy([-.003,y,0])
        svg.append(f'<text x="{x-25}" y="{py}" font-size="20">slot {slot}</text>')
    svg.append('<text x="30" y="740" font-size="16">Rim: fitted plane of these faces, extended over slot at bread center XY (world Z).</text></svg>')
    (HERE/'rim_faces_static.svg').write_text('\n'.join(svg))
    print(json.dumps(dict(status=report['status'], vertices=len(bv), rim_plane=re['plane_body'], residual_m=re['fit_max_residual_m'], checks='PASS'), indent=2))


if __name__ == '__main__':
    main()
