"""Read installed MDL wrapper/examples. No Kit launch, extension enable, or interface call."""
import argparse,ast,datetime,hashlib,importlib,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():p.error('New output directory required')
a.output.mkdir(parents=True)
report={'python':sys.executable,'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'note':'No SimulationApp/Kit launch. Import may fail before extensions activate; static declarations are not runtime dir().','files':{},'extensions':[]}
roots=[]
for cache in (Path('/isaac-sim/extscache'),Path('/isaac-sim/exts'),Path('/isaac-sim/kit/exts')):
 for name in ('omni.mdl.neuraylib*','omni.mdl.usd_converter*','omni.mdl-*'):
  roots.extend(sorted(cache.glob(name)))
for root in dict.fromkeys(roots):
 report['extensions'].append(str(root))
 paths=[]
 for pattern in ('config/extension.toml','omni/mdl/neuraylib/__init__.py','omni/mdl/neuraylib/scripts/*.py','omni/mdl/neuraylib/_neuraylib.pyi','omni/mdl/neuraylib/tests/basic.py','omni/mdl/neuraylib/tests/tmp_scope_recreation.py','omni/mdl/usd_converter/usd_converter.py'):
  paths.extend(root.glob(pattern))
 for f in dict.fromkeys(paths):
  text=f.read_text(errors='replace');item={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'text':text}
  if f.suffix in ('.py','.pyi'):
   try:
    tree=ast.parse(text);item['top_level_definitions']=[x.name for x in tree.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))];item['imports']=[ast.unparse(x) for x in tree.body if isinstance(x,(ast.Import,ast.ImportFrom))]
   except SyntaxError as e:item['parse_error']=str(e)
  report['files'][str(f)]=item
# Attempt only ordinary import in the provided Python environment; do not alter sys.path.
try:
 m=importlib.import_module('omni.mdl.neuraylib')
 report['runtime_import']={'file':getattr(m,'__file__',None),'public_symbols':[s for s in dir(m) if not s.startswith('_')],'context':'before Kit/extension activation; no interface called'}
except Exception as e:report['runtime_import']={'error':repr(e),'context':'before Kit/extension activation; not evidence that an enabled Kit extension lacks an API'}
out=a.output/'installation.json';out.write_text(json.dumps(report,indent=2))
print('REPORT:',out)
print('PYTHON:',sys.executable)
print('RUNTIME_IMPORT:',json.dumps(report['runtime_import']))
for f,v in report['files'].items():
 if f.endswith('/neuraylib/__init__.py') or f.endswith('/neuraylib/scripts/extension.py'):
  print('WRAPPER:',f);print('DECLARED_DEFINITIONS:',v.get('top_level_definitions'));print('IMPORTS:',v.get('imports'))
print('FILES_CAPTURED:',len(report['files']))
if not report['files']:raise SystemExit('No installed sources found at expected Isaac roots; do not infer API names.')
