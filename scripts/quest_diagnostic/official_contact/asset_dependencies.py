"""USD file dependencies versus actual renderer-resolved MDL shader modules.
No name allowlist, no MDL search path edits, fail closed if backend cannot verify.
"""
import json,hashlib
from pathlib import Path

def shader_only(identifier,uses,structural):
 return bool(uses) and identifier not in structural and all(u['shader'] and u['attribute']=='info:mdl:sourceAsset' for u in uses)

def local_module_path(filename):
 from urllib.parse import urlsplit,unquote
 if not isinstance(filename,str) or not filename:raise ValueError('Missing MDL filename')
 uri=urlsplit(filename)
 if uri.scheme:
  if uri.scheme!='file' or uri.netloc not in ('','localhost') or uri.query or uri.fragment:raise ValueError('Not a local file URI: '+filename)
  path=Path(unquote(uri.path,errors='strict'))
 else:path=Path(filename)
 if not path.is_absolute() or '\x00' in str(path):raise ValueError('Invalid local MDL path: '+filename)
 return path

def module_filename(transaction,sdk,evidence):
 """Installed examples use with; SWIG exception arguments are broken in this build.
 Catch within the body so normal __exit__(None,None,None) runs once. No manual release.
 """
 pending=None;filename=None
 try:
  with transaction.access_as(sdk.IModule,evidence['db_name']) as m:
   try:
    if not m.is_valid_interface():raise RuntimeError('Loaded MDL database module invalid')
    evidence['stages'].append(dict(stage='db_module_valid',status='ok'))
    filename=m.get_filename()
    evidence['returned_filename']=filename
    evidence['stages'].append(dict(stage='get_filename',status='ok'))
   except BaseException as e:
    pending=(e,e.__traceback__)
   finally:
    m=None
  evidence['stages'].append(dict(stage='imodule_scope_exit',status='ok'))
 except BaseException as e:
  evidence['cleanup_errors'].append(dict(stage='imodule_scope',error=repr(e)))
  if pending is None:pending=(e,e.__traceback__)
 if pending is not None:raise pending[0].with_traceback(pending[1])
 return filename

def load_mdl(identifier):
 evidence=dict(identifier=identifier,stages=[],cleanup_errors=[])
 api=None;module=None;transaction=None;primary=None;result=None;stage='imports'
 try:
  import carb.settings,carb.tokens
  import omni.mdl.neuraylib as nr
  import omni.mdl.pymdlsdk as sdk
  settings=carb.settings.get_settings();tokens=carb.tokens.get_tokens_interface()
  paths={key:settings.get('/renderer/mdl/searchPaths/'+key) for key in ('required','templates','custom')}
  evidence.update(wrapper_file=nr.__file__,search_path_settings=paths)
  stage='backend_init';nr.ensure_running();api=nr.get_neuraylib()
  evidence['stages'].append(dict(stage=stage,status='ok'))
  stage='load_module';module=api.createMdlModule(identifier)
  evidence['stages'].append(dict(stage=stage,status='ok' if module is not None else 'failed'))
  stage='module_valid'
  if module is None or not module.valid():raise RuntimeError('MDL backend could not load '+identifier)
  evidence['stages'].append(dict(stage=stage,status='ok'))
  evidence.update(db_name=module.dbName,qualified_name=module.qualifiedName)
  stage='reading_transaction';transaction=sdk.attach_itransaction(api.createReadingTransaction(module.dbScopeName))
  evidence['stages'].append(dict(stage=stage,status='ok'))
  stage='read_module_filename';filename=module_filename(transaction,sdk,evidence)
  stage='local_file_check';path=local_module_path(filename)
  evidence['normalized_filename']=str(path)
  if not path.is_file():raise RuntimeError('Loaded MDL has no verifiable local source file: '+str(path))
  digest=hashlib.sha256(path.read_bytes()).hexdigest()
  evidence['stages'].append(dict(stage=stage,status='ok'))
  result=dict(identifier=identifier,backend='ensure_running/get_neuraylib/createMdlModule + valid + IModule.get_filename',wrapper_file=nr.__file__,public_api=['ensure_running','get_neuraylib'],call_phase='after AppLauncher, before robot construction',qualified_name=evidence['qualified_name'],db_name=evidence['db_name'],loaded_file=str(path.resolve()),returned_filename=filename,sha256=digest,search_path_settings=paths)
  result['expanded_search_paths']={k:[tokens.resolve(x) for x in (v.split(';') if isinstance(v,str) else v)] if isinstance(v,(list,tuple,str)) else v for k,v in paths.items()}
 except BaseException as e:
  primary=(e,e.__traceback__);evidence['primary_error']=dict(stage=stage,error=repr(e));evidence['stages'].append(dict(stage=stage,status='failed',error=repr(e)))
 finally:
  # Container usd_converter.py: scope exit, destroyMdlModule, then abort transaction.
  # No release of the cached get_neuraylib interface; each owned object cleaned once.
  for name,obj,cleanup in [('destroy_module',module,lambda x:api.destroyMdlModule(x)),('abort_transaction',transaction,lambda x:x.abort())]:
   if obj is None:continue
   try:cleanup(obj);evidence['stages'].append(dict(stage=name,status='ok'))
   except BaseException as e:
    evidence['cleanup_errors'].append(dict(stage=name,error=repr(e)))
    evidence['stages'].append(dict(stage=name,status='failed',error=repr(e)))
  module=None;transaction=None;obj=None
 if primary is not None:
  primary[0].mdl_evidence=evidence
  raise primary[0].with_traceback(primary[1])
 if evidence['cleanup_errors']:
  error=RuntimeError('MDL cleanup failed');error.mdl_evidence=evidence;raise error
 result['lifecycle']=evidence
 return result

def audit(usd,source,official,report_path):
 from pxr import Usd,UsdShade,Sdf,UsdUtils
 layers,assets,missing=UsdUtils.ComputeAllDependencies(str(usd));uses={};structural=set()
 for layer in layers:
  structural.update(layer.subLayerPaths)
  def visit(path):
   spec=layer.GetObjectAtPath(path)
   if isinstance(spec,Sdf.PrimSpec):
    for items in (spec.referenceList.GetAddedOrExplicitItems(),spec.payloadList.GetAddedOrExplicitItems()):
     structural.update(x.assetPath for x in items if x.assetPath)
  layer.Traverse('/',visit)
  stage=Usd.Stage.Open(layer)
  for prim in stage.TraverseAll():
   for attr in prim.GetAttributes():
    values=[attr.Get()]+[attr.Get(t) for t in attr.GetTimeSamples()]
    for val in values:
     vals=[val] if isinstance(val,Sdf.AssetPath) else list(val) if attr.GetTypeName()==Sdf.ValueTypeNames.AssetArray and val is not None else []
     for x in vals:
      if isinstance(x,Sdf.AssetPath):uses.setdefault(x.path,[]).append(dict(layer=layer.identifier,prim=str(prim.GetPath()),attribute=attr.GetName(),shader=prim.IsA(UsdShade.Shader)))
 result=dict(usd=str(usd),usd_unresolved=list(missing),mdl_modules={},asset_hashes={},uses=uses,errors=[])
 try:
  # Only unresolved authored MDL shader sources can use the MDL backend.
  # A missing reference/payload/collision/texture remains a hard failure.
  for identifier in missing:
   if not shader_only(identifier,uses.get(identifier,[]),structural):raise RuntimeError('Unresolved non-MDL-shader dependency: '+identifier)
   result['mdl_modules'][identifier]=load_mdl(identifier)
  paths={str(usd)}|{x.realPath for x in layers if x.realPath}|{str(x) for x in assets}
  for path in paths:
   f=Path(path)
   if not f.is_file():raise RuntimeError('Nonlocal/unresolved file dependency '+path)
   if official and not f.resolve().is_relative_to(Path(source).resolve()):raise RuntimeError('Official file asset escapes checkout '+path)
   if f.read_bytes()[:60].startswith(b'version https://git-lfs'):raise RuntimeError('LFS pointer instead of asset '+path)
   result['asset_hashes'][str(f.resolve())]=hashlib.sha256(f.read_bytes()).hexdigest()
  result['validated']=True
 except BaseException as e:
  result['validated']=False;result['errors'].append(repr(e))
  if hasattr(e,'mdl_evidence'):result['mdl_failure']=e.mdl_evidence
  raise
 finally:Path(report_path).write_text(json.dumps(result,indent=2,default=str))
 return result['asset_hashes']
