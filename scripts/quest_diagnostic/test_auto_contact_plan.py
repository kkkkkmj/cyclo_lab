import copy,unittest
from auto_contact_protocol import PlannedProtocol,Protocol
from auto_contact_plan import validate_geometry
class PlanTests(unittest.TestCase):
    def fixture(self):
        eye=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]];poses={k:eye for k in ['left','right','body']};fb=[[[.4,-.4,1.39],[.5,-.3,1.45]]]*4;tb=[[.3,-1,0],[1,1,1]]
        p=dict(schema_version=1,scenario='s',seed=1,initial_eef_poses=poses,finger_bounds=fb,table_bounds=tb,contact_depth_m=.39,max_down_m=.393,horizontal_offset_m=[.19,0])
        g=dict(errors=[],meters_per_unit=1,up_axis='Z',initial_eef_poses=poses,table=[{'world_vertex_bounds':tb}],fingers=[{'world_vertex_bounds':f} for f in fb]);return p,g
    def test_geometry_checks(self):
        p,g=self.fixture();validate_geometry(p,g,'s',1)
        for key,val in [('meters_per_unit',.01),('errors',['missing']),('up_axis','Y')]:
            x=copy.deepcopy(g);x[key]=val
            with self.assertRaises(ValueError):validate_geometry(p,x,'s',1)
        g['fingers'][0]['world_vertex_bounds'][0][2]+=.01
        with self.assertRaises(ValueError):validate_geometry(p,g,'s',1)
    def test_plan_mismatch(self):
        p,g=self.fixture()
        for k,v in [('max_down_m',.4),('contact_depth_m',.37),('seed',2),('horizontal_offset_m',[float('nan'),0])]:
            x=copy.deepcopy(p);x[k]=v
            with self.assertRaises(ValueError):validate_geometry(x,g,'s',1)
    def test_complete_route(self):
        p,_=self.fixture();r=PlannedProtocol(p);last=r.offset();seen=set()
        for i in range(4000):
            seen.add(r.phase);contact=r.phase in ['approach','contact_hold'] and r.down>=.39
            r.advance(.04,contact);now=r.offset()
            self.assertLessEqual(sum((a-b)**2 for a,b in zip(now,last))**.5,.00040000001);last=now
            if r.phase=='done':break
        self.assertEqual(r.offset(),[0,0,0]);self.assertTrue(r.contact_observed)
        self.assertEqual(seen,{'baseline','translate','approach','contact_hold','release','return_horizontal'})
    def test_no_contact_finishes_unconfirmed(self):
        p,_=self.fixture();r=PlannedProtocol(p)
        for i in range(4000):
            r.advance(.04,False)
            if r.phase=='done':break
        self.assertEqual(r.phase,'done');self.assertFalse(r.contact_observed);self.assertEqual(r.offset(),[0,0,0])
    def test_unexpected_contact(self):
        p,_=self.fixture()
        for phase in ['baseline','translate','return_horizontal']:
            r=PlannedProtocol(p);r.phase=phase
            with self.assertRaises(RuntimeError):r.advance(.04,True)
    def test_default_limits_unchanged(self):
        self.assertEqual(Protocol().max_down,.25)
        with self.assertRaises(ValueError):Protocol(max_down=.4)
        p,_=self.fixture();p['max_down_m']=.46
        with self.assertRaises(ValueError):PlannedProtocol(p)
    def test_runtime_hash_guard(self):
        import tempfile,hashlib,json
        from pathlib import Path
        from types import SimpleNamespace
        from auto_contact_plan import validate_runtime
        p,g=self.fixture();g['table'][0]['meshes']=[]
        p['table_mesh_sha256']=hashlib.sha256(json.dumps([],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        p['obstacle_reset_poses']={}
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'asset';f.write_text('original');p['asset_hashes']={'asset':hashlib.sha256(f.read_bytes()).hexdigest()}
            validate_runtime(p,g,SimpleNamespace(),d,'s',1)
            f.write_text('changed')
            with self.assertRaises(ValueError):validate_runtime(p,g,SimpleNamespace(),d,'s',1)
if __name__=='__main__':unittest.main()
