import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from asset_dependencies import shader_only,audit
class PolicyTests(unittest.TestCase):
 def test_no_filename_allowlist(self):
  u=[dict(shader=True,attribute='info:mdl:sourceAsset')]
  self.assertTrue(shader_only('AnyModule.mdl',u,set()))
  self.assertFalse(shader_only('OmniPBR.mdl',[],set()))
  self.assertFalse(shader_only('AnyModule.mdl',u,{'AnyModule.mdl'}))
  self.assertFalse(shader_only('AnyModule.mdl',u+[dict(shader=False,attribute='collision_asset')],set()))
class UsdTests(unittest.TestCase):
 def setUp(self):
  try:from pxr import Usd
  except ImportError:self.skipTest('pxr requires installed USD Python')
 def make(self,p,extra=False):
  from pxr import Usd,UsdShade,Sdf
  s=Usd.Stage.CreateNew(str(p));sh=UsdShade.Shader.Define(s,'/Material/Shader')
  sh.GetPrim().CreateAttribute('info:mdl:sourceAsset',Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('AnyModule.mdl'))
  if extra:s.DefinePrim('/Missing').GetReferences().AddReference('missing_collision.usd')
  s.GetRootLayer().Save()
 def test_backend_success_only(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'robot.usda';self.make(p)
   with patch('asset_dependencies.load_mdl',return_value={'backend':'mock_valid'}) as m:
    r=audit(p,Path(d),True,Path(d)/'audit.json');self.assertIn(str(p),r);m.assert_called_once_with('AnyModule.mdl')
 def test_backend_failure_blocks(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'robot.usda';self.make(p)
   with patch('asset_dependencies.load_mdl',side_effect=RuntimeError('backend invalid')):
    with self.assertRaisesRegex(RuntimeError,'backend invalid'):audit(p,Path(d),True,Path(d)/'audit.json')
 def test_missing_collision_still_blocks(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'robot.usda';self.make(p,True)
   with patch('asset_dependencies.load_mdl',return_value={'backend':'mock_valid'}):
    with self.assertRaisesRegex(RuntimeError,'non-MDL'):audit(p,Path(d),True,Path(d)/'audit.json')
if __name__=='__main__':unittest.main()
