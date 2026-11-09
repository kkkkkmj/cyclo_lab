import json,tempfile,unittest,subprocess,sys
from pathlib import Path
from auto_contact_shutdown import finish
from auto_contact_checked import effective_code
class Resource:
 def __init__(self,error=False):self.error=error
 def close(self):
  if self.error:raise RuntimeError('resource failed')
class App:
 config={'fast_shutdown':False}
 def close(self,**kw):assert kw==dict(wait_for_replicator=True,skip_cleanup=False)
class Tests(unittest.TestCase):
 def test_return_and_cleanup_error(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'out.json';s={'status':'completed'}
   self.assertEqual(finish(App(),Resource(),Resource(),p,s,0),0)
   x=json.loads(p.read_text());self.assertTrue(x['app_close_returned']);self.assertEqual(x['shutdown_phase'],'app_close_returned')
   s={'status':'completed'};self.assertEqual(finish(App(),Resource(True),Resource(),p,s,0),1)
   self.assertTrue(s['app_close_completed']);self.assertFalse(s['resources_close_completed']);self.assertEqual(effective_code(0,s,[]),1)
 def test_nonreturn_does_not_become_success(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'out.json'
   script='''import os,sys
from auto_contact_shutdown import finish
class A:
 config={'fast_shutdown':True}
 def close(self,**kwargs):os._exit(0)
finish(A(),None,None,sys.argv[1],{'status':'completed'},0)
'''
   r=subprocess.run([sys.executable,'-c',script,str(p)],cwd=Path(__file__).parent,capture_output=True)
   self.assertEqual(r.returncode,0);x=json.loads(p.read_text());self.assertFalse(x['app_close_completed']);self.assertEqual(x['shutdown_phase'],'app_close_begin');self.assertEqual(effective_code(0,x,[]),1)
 def test_close_exception(self):
  class Bad(App):
   def close(self,**kw):raise RuntimeError('close failed')
  with tempfile.TemporaryDirectory() as t:
   s={};self.assertEqual(finish(Bad(),None,None,Path(t)/'o',s,0),1);self.assertFalse(s['app_close_completed'])
if __name__=='__main__':unittest.main()
