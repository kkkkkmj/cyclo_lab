import unittest
import numpy as np
from pxr import Usd,UsdGeom,Gf
from contact_geometry_snapshot import geometry_record
from auto_contact_checked import effective_code,process_error
class GeometryTests(unittest.TestCase):
    def test_static_box(self):
        s=Usd.Stage.CreateInMemory();p=UsdGeom.Cube.Define(s,'/Table');p.CreateSizeAttr(2);p.AddTranslateOp().Set(Gf.Vec3d(0,0,1))
        r=geometry_record(s,'/Table');np.testing.assert_allclose(r['world_vertex_bounds'],[[-1,-1,0],[1,1,2]])
        self.assertIsNone(r['cooked_physx_shape'])
    def test_runtime_body_overrides_stale_usd_world(self):
        s=Usd.Stage.CreateInMemory();b=UsdGeom.Xform.Define(s,'/Body');b.AddTranslateOp().Set(Gf.Vec3d(100,0,0));m=UsdGeom.Mesh.Define(s,'/Body/Collision')
        m.CreatePointsAttr([(0,0,0),(1,0,0),(0,1,0)]);m.CreateFaceVertexCountsAttr([3]);m.CreateFaceVertexIndicesAttr([0,1,2])
        r=geometry_record(s,'/Body/Collision','/Body',[2,3,4,0,0,0,1]);np.testing.assert_allclose(r['world_vertex_bounds'],[[2,3,4],[3,4,4]])
        self.assertEqual(r['meshes'][0]['faces']['indices'],[0,1,2])
    def test_missing_not_zero(self):
        s=Usd.Stage.CreateInMemory();UsdGeom.Xform.Define(s,'/Unknown');r=geometry_record(s,'/Unknown');self.assertIsNone(r['world_vertex_bounds'])
        with self.assertRaises(ValueError):geometry_record(s,'/Missing')
    def test_actual_crash_not_protocol_code(self):
        o=dict(status='completed',requested_exit_code=3,app_close_completed=True,cleanup_errors=[])
        self.assertEqual(effective_code(1,o,[]),1)
        self.assertEqual(effective_code(0,o,[]),3)
        self.assertTrue(process_error('/isaac-sim/python.sh: line 73: 57248 Segmentation fault (core dumped)'))
        self.assertFalse(process_error('APP_CLOSE RETURNED'))
if __name__=='__main__':unittest.main()
