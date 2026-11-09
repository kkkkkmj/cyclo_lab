"""CPU/USD checks only; no claim of cooked PhysX or bread dynamics validation."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
import numpy as np
import torch
from pxr import Usd, UsdGeom, UsdPhysics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT/'source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2'


def intersects(triangle, lo, hi):
    """Triangle/axis-aligned box SAT, including coplanar contact."""
    center, half = (lo+hi)/2, (hi-lo)/2
    t = triangle-center
    edges = [t[1]-t[0],t[2]-t[1],t[0]-t[2]]
    axes = [*np.eye(3),np.cross(edges[0],edges[1])]
    axes += [np.cross(e,a) for e in edges for a in np.eye(3)]
    for a in axes:
        if np.linalg.norm(a)<1e-14: continue
        proj = t@a
        radius = half@np.abs(a)
        if proj.min()>radius+1e-12 or proj.max() < -radius-1e-12:
            return False
    return True


def main():
    params = {}
    exec((SOURCE/'toast_parameters.py').read_text(),params)
    height = params['SERVING_POPUP_HEIGHT']
    assert height == .035
    cfg_tree = ast.parse((SOURCE/'bimanual_env_cfg.py').read_text())
    cls = next(x for x in cfg_tree.body if isinstance(x,ast.ClassDef) and x.name=='MakeToastFFWBG2BimanualServeEnvCfg')
    value = next(x.value for x in cls.body if isinstance(x,ast.AnnAssign) and x.target.id=='toast_popup_extra_height')
    assert isinstance(value,ast.Name) and value.id=='SERVING_POPUP_HEIGHT'
    asset = ROOT/'source/cyclo_lab/data/objects/robodojo_make_toast/toaster/object.usdz'
    stage = Usd.Stage.Open(str(asset))  # edits are in memory only; never saved to asset
    lever = stage.GetPrimAtPath('/root/joints/joint_1')
    lever_before = {a.GetName():str(a.Get()) for a in lever.GetAttributes()}
    spawn = types.SimpleNamespace(__wrapped__=lambda *a,**kw:stage.GetDefaultPrim())
    namespace = dict(spawn_toast_bimanual_toaster=spawn,get_current_stage=lambda:stage,SERVING_POPUP_HEIGHT=height)
    tree = ast.parse((SOURCE/'scene.py').read_text())
    for name in ('spawn_toast_popup_toaster','spawn_toast_serving_toaster'):
        node = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
        node.decorator_list=[]
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE/'scene.py'),'exec'),namespace)
        namespace[name].__wrapped__=namespace[name]
    namespace['spawn_toast_serving_toaster']('/root',None)
    joint = UsdPhysics.PrismaticJoint(stage.GetPrimAtPath('/root/joints/carriage_joint'))
    np.testing.assert_allclose([joint.GetLowerLimitAttr().Get(),joint.GetUpperLimitAttr().Get()],[-.045,.035],atol=1e-8)
    assert lever_before == {a.GetName():str(a.Get()) for a in lever.GetAttributes()}
    # Test the actual cycle implementation with CPU tensor state and appliance inputs.
    package = types.ModuleType('lift_check');package.__path__=[]
    mdp = types.ModuleType('lift_check.mdp')
    bmdp = types.ModuleType('lift_check.bimanual_mdp')
    mdp.lever_press_ratio=lambda env:env.ratio
    bmdp.bread_in_slot=lambda env,name,slot:env.present[:,int(name[-1])]
    sys.modules.update({'lift_check':package,'lift_check.mdp':mdp,'lift_check.bimanual_mdp':bmdp})
    spec=importlib.util.spec_from_file_location('lift_check.toast_cycle',SOURCE/'toast_cycle.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    data=types.SimpleNamespace(joint_pos=torch.zeros(1,2),joint_vel=torch.zeros(1,2),joint_pos_limits=torch.tensor([[[-.045,.035],[-.0138,.0642]]]))
    toaster=types.SimpleNamespace(data=data,joint_names=['carriage_joint','joint_1'],
        set_joint_position_target=lambda *a:None,write_joint_stiffness_to_sim=lambda *a:None)
    env=types.SimpleNamespace(scene={'toaster':toaster},cfg=types.SimpleNamespace(toast_popup_extra_height=height),
        device='cpu',num_envs=1,ratio=torch.tensor([0.]),present=torch.zeros(1,4,dtype=torch.bool))
    cycle=module.ToastCycle(env)
    for bread_id in range(4):
        cycle.reset([0]);env.present[:]=False;env.present[0,bread_id]=True;env.ratio[:]=.89
        cycle.update(.04);assert cycle.phase.item()==0
        env.ratio[:]=.90;cycle.update(.04);assert cycle.phase.item()==1
    cycle.reset([0]);env.present[:]=False;cycle.update(.04);assert cycle.phase.item()==0
    env.present[0,0]=True;cycle.reset([0]);cycle.update(.04)
    cycle.elapsed[:]=.6;data.joint_pos[0,0]=-.045;cycle.update(.04)
    assert cycle.phase.item()==2 and cycle.elapsed.item()==0
    cycle.elapsed[:]=3.90;cycle.update(.04);assert cycle.phase.item()==2
    cycle.elapsed[:]=4.;cycle.update(.04);assert cycle.phase.item()==3
    for elapsed in (.0,.2,.4,.6,.8):
        cycle.phase[:]=3;cycle.elapsed[:]=elapsed-.04;cycle.update(.04)
        u=elapsed/.8;expected=-.045+.080*(u*u*(3-2*u))
        assert abs(cycle.command.item()-expected)<1e-7
    cycle.elapsed[:]=1.;data.joint_pos[0,0]=.015;cycle.update(.04);assert cycle.phase.item()==3
    data.joint_pos[0,0]=.035;cycle.elapsed[:]=.86;cycle.update(.04);assert cycle.phase.item()==3
    cycle.elapsed[:]=.93;cycle.update(.04);assert cycle.phase.item()==4
    assert abs(cycle.command.item()-.035)<1e-7
    assert (cycle.STROKE,cycle.HEATING_SECONDS,cycle.LOWER_SECONDS,cycle.RISE_SECONDS)==(.045,4.,.6,.8)
    # Review original authored collision surfaces against the swept carriage boxes.
    # PhysX convex-decomposition/cooking and moving lever poses require runtime checks.
    triangles=[]
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh) or not prim.HasAPI(UsdPhysics.CollisionAPI):continue
        if UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get() is False:continue
        mesh=UsdGeom.Mesh(prim)
        matrix=np.asarray(mesh.ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
        points=np.asarray(mesh.GetPointsAttr().Get())@matrix[:3,:3]+matrix[3,:3]
        indices=list(mesh.GetFaceVertexIndicesAttr().Get());offset=0
        for face,count in enumerate(mesh.GetFaceVertexCountsAttr().Get()):
            poly=points[indices[offset:offset+count]];offset+=count
            for i in range(1,count-1):
                triangles.append((str(prim.GetPath()),face,poly[[0,i,i+1]]))
    sweeps=[]
    for slot,y in enumerate((-.026455,.0253585)):
        for label,q0,q1 in [('old_full',-.045,.015),('new_full',-.045,.035),('extension_only',.015,.035)]:
            for margin in (0.,.001):
                lo=np.array([-.070,y-.010,.0056+q0])-margin
                hi=np.array([.064,y+.010,.0086+q1])+margin
                hits=[dict(prim=p,face=f) for p,f,t in triangles
                      if np.all(t.max(0)>=lo) and np.all(t.min(0)<=hi) and intersects(t,lo,hi)]
                sweeps.append(dict(slot=slot,sweep=label,margin_m=margin,bounds=[lo.tolist(),hi.tolist()],hits=hits))
    report=dict(status='CPU_LOGIC_AND_AUTHORED_USD_CHECKS_PASSED_NOT_PHYSX',
        target_before_m=.015,target_after_m=height,limits_before_m=[-.045,.015],limits_after_m=[-.045,.035],
        cycle_checks='90% edge; all four bread IDs; empty toaster; 4 s heating; curve; old target rejected; minimum completion time; new target accepted',
        lever_attributes_unchanged=True,lever_attributes=lever_before,
        command_peak_velocity_before_m_s=.060*1.5/.8,command_peak_velocity_after_m_s=.080*1.5/.8,
        unchanged_carriage_velocity_limit_m_s=.12,
        sweep_checks=sweeps,authored_collision_triangles=len(triangles),
        limitations='Swept boxes vs authored collision mesh surfaces at authored joint poses, not cooked convex shapes, bread contacts or dynamic lever sweep. Articulation self-collision remains disabled as in existing cfg. Physical ejection/contact requires actual PhysX.',
        asset_sha256=hashlib.sha256(asset.read_bytes()).hexdigest())
    (HERE/'static_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('sweep_checks','lever_attributes')},indent=2))
    print('Sweep hits:',[(x['slot'],x['sweep'],x['margin_m'],len(x['hits'])) for x in sweeps])


if __name__=='__main__':main()
