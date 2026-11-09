"""CPU mock of API surface confirmed in container installation.json; not MDL execution."""
import unittest,tempfile,types,sys
from pathlib import Path
from unittest.mock import patch
from asset_dependencies import load_mdl
class Tests(unittest.TestCase):
 def run_case(self,valid,missing=False,cleanup_error=False,filename_error=False):
  calls=[]
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'Test.mdl';f.write_text('mock only')
   if missing:f.unlink()
   class Module:
    dbName='mdl::Test';dbScopeName='';qualifiedName='::Test'
    def valid(self):return valid
   class DbModule:
    def __enter__(self):return self
    def __exit__(self,*args):
     if any(x is not None for x in args):raise TypeError('simulated SWIG void const * failure')
    def is_valid_interface(self):return True
    def get_filename(self):
     if filename_error:raise ValueError('original filename error')
     return 'file:'+str(f)
   class Tx:
    def access_as(self,*args):return DbModule()
    def abort(self):calls.append('abort')
   class API:
    def createMdlModule(self,name):calls.append('load');return Module()
    def createReadingTransaction(self,scope):return 1
    def destroyMdlModule(self,module):
     calls.append('destroy')
     if cleanup_error:raise RuntimeError('cleanup error')
   api=API()
   def get():calls.append('get');return api
   names=['carb','carb.settings','carb.tokens','omni','omni.mdl','omni.mdl.neuraylib','omni.mdl.pymdlsdk'];mods={n:types.ModuleType(n) for n in names}
   for n,m in mods.items():
    if '.' in n:
     parent,attr=n.rsplit('.',1);setattr(mods[parent],attr,m)
   mods['carb.settings'].get_settings=lambda:types.SimpleNamespace(get=lambda k:[])
   mods['carb.tokens'].get_tokens_interface=lambda:types.SimpleNamespace(resolve=lambda x:x)
   nr=mods['omni.mdl.neuraylib'];nr.__file__='container/wrapper/__init__.py';nr.ensure_running=lambda:calls.append('ensure');nr.get_neuraylib=get
   sdk=mods['omni.mdl.pymdlsdk'];sdk.attach_itransaction=lambda handle:Tx();sdk.IModule=object
   with patch.dict(sys.modules,mods):
    if missing or cleanup_error or filename_error:
     with self.assertRaises(Exception) as ctx:load_mdl('Test.mdl')
     e=ctx.exception
     self.assertTrue(hasattr(e,'mdl_evidence'))
     if missing:self.assertIn('no verifiable local source file',str(e))
     elif filename_error:self.assertEqual(str(e),'original filename error')
     else:self.assertIn('cleanup failed',str(e))
     self.assertEqual(bool(e.mdl_evidence['cleanup_errors']),cleanup_error)
    elif valid:
     r=load_mdl('Test.mdl');self.assertEqual(r['wrapper_file'],nr.__file__);self.assertTrue(r['sha256'])
    else:
     with self.assertRaisesRegex(RuntimeError,'could not load'):load_mdl('Test.mdl')
   self.assertEqual(calls, ['ensure','get','load','destroy','abort'] if valid else ['ensure','get','load','destroy'])
 def test_missing_file_primary_survives_cleanup_error(self):self.run_case(True,missing=True,cleanup_error=True)
 def test_filename_exception_not_forwarded_to_swig(self):self.run_case(True,filename_error=True)
 def test_cleanup_only_failure_is_not_success(self):self.run_case(True,cleanup_error=True)
 def test_file_uri_rules(self):
  from asset_dependencies import local_module_path
  for uri in ['file:/tmp/a%20b.mdl','file:///tmp/a%20b.mdl','file://localhost/tmp/a%20b.mdl']:
   self.assertEqual(str(local_module_path(uri)),'/tmp/a b.mdl')
  for uri in ['http://host/a.mdl','file://remote/tmp/a.mdl','relative.mdl','file:/tmp/a?query']:
   with self.assertRaises(ValueError):local_module_path(uri)
 def test_public_cached_wrapper_only(self):self.run_case(True)
 def test_invalid_load_fails_and_destroys(self):self.run_case(False)
if __name__=='__main__':unittest.main()
