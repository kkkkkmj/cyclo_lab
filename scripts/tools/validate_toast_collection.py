"""Read-only precollection audit; static, isolated PhysX workers, and merged reports.

Never edits the manifest, task configuration, robot drives or assets.
"""
import argparse
import csv
import gzip
import hashlib
import itertools
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DEFAULT=ROOT/'scenario_delivery/manifest.json'
NAMES=('toaster','plate','bread_shelf',*(f'bread_{i}' for i in range(4)))
# Frozen before runtime; failures are not automatically repaired or relaxed.
LIMITS=dict(duration_s=5.,object_translation_m=.010,toaster_rotation_deg=5.,
    plate_rotation_deg=math.degrees(math.acos(.985)),bread_rotation_deg=20.,
    bread_rack_local_error_m=[.005,.003,.006],final_linear_speed_m_s=.15,
    final_angular_speed_rad_s=.5,below_table_m=.010,reset_position_m=5e-5,
    reset_quaternion_dot_error=5e-5,robot_joint_drift_rad_or_m=.05)

def dump(p,data):Path(p).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def angle(a,b):
    import numpy as np
    dot=abs(float(np.dot(a,b)))/(float(np.linalg.norm(a))*float(np.linalg.norm(b)))
    return math.degrees(2*math.acos(min(1.,max(0.,dot))))

def base_row(e):
    r=dict(scenario_id=e['id'],group=e['scenario_group'],group_index=e['group_index'],
           layout_type='>'.join(e['order_positive_to_negative_y']),static='NOT_RUN',
           stability='NOT_RUN',reset='NOT_RUN',full_task='NOT_VERIFIED',reasons=[])
    for task in ('grasp_bread_0','grasp_bread_1','grasp_bread_2','grasp_bread_3','insert','lever','serve','at_least_one_bread'):
        for check in ('ik','collision','path'):r[f'{task}_{check}']='UNVERIFIED'
    return r

def write_report(out,rows):
    dump(out/'results.json',rows)
    flat=[]
    for r in rows:
        flat.append({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
    fields=list(dict.fromkeys(k for r in flat for k in r))
    with (out/'results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(flat)
    lines=['# 시연 수집 전 검증 결과','',
      'STATIC_PASS는 아래 정적 범위만 통과했다는 뜻이다. PhysX 미실행과 작업 접근/충돌/경로 미검증을 전체 작업 PASS로 취급하지 않는다.', '',
      '| scenario | 그룹/번호 | 종류 | table 여유 m | 보수적 표면 XY 간격 m | 정적 | 안정성 | reset | 이유/미검증 |',
      '|---|---|---|---:|---:|---|---|---|---|']
    for r in rows:
        lines.append(f"| {r['scenario_id']} | {r['group']}/{r['group_index']} | {r['layout_type']} | {r.get('table_margin_m',float('nan')):.4f} | {r.get('surface_xy_lower_bound_m',float('nan')):.4f} | {r['static']} | {r['stability']} | {r['reset']} | {'; '.join(r['reasons'])} |")
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    dump(out/'failures.json',[r for r in rows if any(r[k] in ('FAIL','ERROR') for k in ('static','stability','reset')) or r.get('process_status')=='ERROR'])

def static(args,out):
    import numpy as np
    import torch
    from scipy.spatial import ConvexHull
    from pxr import Usd,UsdGeom,UsdPhysics
    import generate_current_toast_scenarios as gen
    from check_bread_slot_geometry import mesh_points,rotation,triangle_intersects_hull
    from test_toast_scenario_runtime import m as loader,fixture
    from test_toast_serving_success import ServingSuccess
    data=loader.load_manifest(args.manifest);before=sha(args.manifest)
    base,contract=gen.current_contract();points,hashes=gen.geometry(base)
    evidence=load(Path(args.manifest).parent/'inputs/geometry_evidence.json')
    assert gen.sha(ROOT/'source/cyclo_lab/data/robots/FFW/FFW_BG2_without_mimic.usd')==evidence['robot_usd_sha256']
    # Authored static rack triangle vs authored convex bread collider; reuse existing clipper.
    rack=Usd.Stage.Open(str(ROOT/'source/cyclo_lab/data/objects/bread_slot/rack.usda'))
    prim=next(p for p in rack.Traverse() if p.HasAPI(UsdPhysics.CollisionAPI))
    rv=mesh_points(rack,prim);tri=rv[np.asarray(UsdGeom.Mesh(prim).GetFaceVertexIndicesAttr().Get()).reshape(-1,3)]
    bread=Usd.Stage.Open(str(ROOT/'source/cyclo_lab/data/objects/robodojo_make_toast/bread/object.usdz'))
    bv=mesh_points(bread,bread.GetPrimAtPath('/World/collision'))
    support={};locals_=[]
    for i in range(4):
        p=base['baseline_bread'][f'bread_{i}'];s=base['baseline']['bread_shelf'];rs=rotation(s['quaternion_wxyz'])
        v=bv@rotation(p['quaternion_wxyz']).T@rs+(np.array(p['position_m'])-s['position_m'])@rs
        locals_.append(v);eq=ConvexHull(v).equations;lower=ConvexHull(v-[0,0,.001]).equations
        support[f'bread_{i}']=dict(intersects=any(triangle_intersects_hull(t,eq) for t in tri),
                                 support_within_1mm=any(triangle_intersects_hull(t,lower) for t in tri))
    surfaces=evidence['table_support']['convex_surface_polygons_xy']
    if len(surfaces)!=1:raise ValueError('Numeric edge margin currently requires single convex tabletop; no hull of a disjoint union')
    table=ConvexHull(np.asarray(surfaces[0]));rows=[]
    ServingSuccess.setUpClass();predicate=ServingSuccess()
    for e in data['scenarios']:
        row=base_row(e);fail,polys,checks=gen.validate_layout(e['poses'],points,evidence,base)
        cfg=fixture(data);cfg.scenario_manifest=str(Path(args.manifest).resolve());loader.apply_scenario(cfg,e['id'])
        margin=min(float(-(np.asarray(p)@table.equations[:,:2].T+table.equations[:,2]).max()) for p in polys.values())
        centers={a+'/'+b:float(np.linalg.norm(np.array(e['poses'][a]['position_m'])-e['poses'][b]['position_m'])) for a,b in itertools.combinations(('toaster','plate','bread_shelf'),2)}
        local_ok=True
        for i in range(4):
            p=e['poses'][f'bread_{i}'];s=e['poses']['bread_shelf'];rs=rotation(s['quaternion_wxyz'])
            v=bv@rotation(p['quaternion_wxyz']).T@rs+(np.array(p['position_m'])-s['position_m'])@rs
            local_ok &= bool(np.allclose(v,locals_[i],atol=1e-7,rtol=0))
        if not local_ok or any(v['intersects'] or not v['support_within_1mm'] for v in support.values()):fail.append('rack_bread_support')
        # Logical satisfiability using the real task_done function and every actual plate pose.
        # This constructs synthetic states, NOT physical placements or reachable robot poses.
        feasible=[]
        for i in range(4):
            predicate.setUp();plate=predicate.env.scene['plate'].data;p=e['poses']['plate']
            plate.root_pos_w=torch.tensor([p['position_m']],dtype=torch.float64)+predicate.env.scene.env_origins
            plate.root_quat_w=torch.tensor([p['quaternion_wxyz']],dtype=torch.float64)
            plate.default_root_state=torch.tensor([list(cfg.scene.plate.init_state.pos)],dtype=torch.float64)
            predicate.place(i);predicate.env.toast_cycle.heated_bread[0,i]=True
            feasible.append(bool(predicate.done(predicate.env).item()))
        if not all(feasible):fail.append('success_predicate_synthetic_witness_failed')
        row.update(static='FAIL' if fail else 'STATIC_PASS',table_margin_m=margin,
            center_distances_3d_m=centers,surface_xy_lower_bounds_m=checks['pair_gaps_m'],
            surface_xy_lower_bound_m=min(checks['pair_gaps_m'].values()),rack_support=support,
            plate_default_pose_matches=True,success_logical_witness_by_bread=feasible,
            distance_prefilter=checks['model_prefilter']['status'],
            reasons=fail+['PhysX_NOT_RUN','grasp_frames_IK_collision_path_UNVERIFIED'])
        rows.append(row)
    assert before==sha(args.manifest)
    dump(out/'audit.json',dict(manifest_sha256=before,asset_hashes=hashes,contract=contract,limits=LIMITS,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in gen.CFG.glob('*.py')},
        static_method='Actual USD meshes/transforms/scales projected to convex XY hulls, major objects expanded 1mm; conservative lower bound, not exact 3D surface distance or cooked contact',
        rack_method='Exact authored static triangles vs authored convex bread hull; 1mm lowered support; rigid-local equivalence all scenarios',
        success_method='Actual predicate, synthetic cooked/placed states for each bread ID; logical witness only',
        robot='Existing distance upper-bound filter only. Existing DLS action uses soft joint limits; historical IK probes have heuristic unvalidated grasp frames. No physical task IK, collision or path PASS.',
        runtime='NOT_RUN'))
    write_report(out,rows);select_vr(out,data,rows,args.manifest)

def select_vr(out,data,rows,manifest):
    chosen={};entries=data['scenarios'];byid={r['scenario_id']:r for r in rows}
    def add(e,why):chosen.setdefault(e['id'],[]).append(why)
    for g in data['generation']['groups']:
        group=[e for e in entries if e['scenario_group']==g]
        for typ in range(6):
            items=[e for e in group if e['type_index']==typ]
            # Pick the median distance member; explicit extremes added separately.
            add(sorted(items,key=lambda e:e['metrics']['max_probe_shoulder_distance_m'])[len(items)//2],f'{g} type {typ+1} representative')
        add(max(group,key=lambda e:e['metrics']['max_probe_shoulder_distance_m']),f'{g} farthest heuristic probe distance')
        add(min(group,key=lambda e:byid[e['id']]['surface_xy_lower_bound_m']),f'{g} narrowest surface-bound gap')
        add(max(group,key=lambda e:max(abs(v[2]) for v in e['jitter'].values())),f'{g} largest absolute yaw perturbation')
    selected=[];lines=['# VR 수집 전 확인 대상','',
        '6종류 × 4그룹 대표 24개 + 그룹별 최장 거리/최소 간격/최대 yaw 변화. 중복 ID는 한 번만 실행한다. 거리의 의미는 휴리스틱 probe–리프트 어깨 구간 거리이며 도달성 증명이 아니다.', '',
        '먼저 Ubuntu GUI 터미널:', '```bash',f'cd {ROOT}','export DISPLAY=:1','export XAUTHORITY=/run/user/1000/gdm/Xauthority','```','',
        'Quest 전용 서버(별도 터미널, 기존 프로세스를 종료하지 않음; IP는 실제 PC 주소로 확인, 포트 점유 시 미사용 포트 사용):','```bash',f'cd {ROOT}',
        'python3 scripts/quest_diagnostic/server.py --host 192.168.10.116 --port 8766 --bridge-dir '+str(ROOT/'logs/quest_precollection_v20261109'),'```',
        'Quest에서 https://192.168.10.116:8766/ 접속 후 Pair. 이미 동일 bridge를 사용하는 시뮬레이션이 있으면 종료시키지 말고 별도 bridge를 지정한다. 아래 명령은 하나씩 실행한다.','']
    rel=str(Path(manifest).resolve().relative_to(ROOT))
    for e in sorted((e for e in entries if e['id'] in chosen),key=lambda e:(e['scenario_group'],e['group_index'])):
        reasons=chosen[e['id']];selected.append(dict(scenario_id=e['id'],group=e['scenario_group'],group_index=e['group_index'],reasons=reasons))
        selection=f"--scenario_manifest {rel} --scenario_group {e['scenario_group']} --group_index {e['group_index']}"
        lines += [f"## {e['id']} · {e['scenario_group']} #{e['group_index']}",'', '; '.join(reasons),'','```bash',
            f'bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py {selection}',
            f'bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 {selection} --enable-grippers --keep-open','```','',
            '- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록',
            '- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인',
            '- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인',
            '- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON',
            '- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료',
            '- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)',
            '- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인',
            '- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도',
            '- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지','']
    dump(out/'vr_selection.json',selected);(out/'VR_CHECKLIST.md').write_text('\n'.join(lines)+'\n')

# Runtime code deliberately imports Isaac only in isolated worker processes.
def worker(args,out):
    import traceback
    from toast_audit_lifecycle import atomic_json,close_safely,result_status
    app=env=None;failure=None;cleanup=[];contacts=None
    try:
        from isaaclab.app import AppLauncher
        app=AppLauncher(headless=args.headless,enable_cameras=True,device=args.device).app
        import torch
        import gymnasium as gym
        import cyclo_lab
        from isaaclab_tasks.utils.parse_cfg import parse_env_cfg
        with torch.inference_mode():
            cfg=parse_env_cfg('Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2',device=args.device,num_envs=1)
            cfg.scenario_id=args.scenario_id;cfg.scenario_manifest=str(Path(args.manifest).resolve())
            candidate=getattr(args,'initial_bread_poses',None)
            if candidate:
                from cyclo_lab.manager_based.manipulation.make_toast.config.ffw_bg2.scenarios import apply_scenario
                proposal=load(candidate)
                if proposal.get('review','').startswith('WITHHELD'):raise ValueError('Candidate withheld pending live collider/contact diagnosis')
                if proposal['scenario_id']!=args.scenario_id or proposal['manifest_sha256']!=sha(args.manifest):raise ValueError('Candidate scenario/manifest mismatch')
                if set(proposal['poses'])!={f'bread_{i}' for i in range(4)}:raise ValueError('Candidate must specify exactly four breads')
                apply_scenario(cfg,args.scenario_id)
                for name,pose in proposal['poses'].items():
                    values=[*pose['position_m'],*pose['quaternion_wxyz']]
                    if len(values)!=7 or not all(math.isfinite(x) for x in values):raise ValueError('Invalid candidate pose')
                    getattr(cfg.scene,name).init_state.pos=tuple(pose['position_m'])
                    getattr(cfg.scene,name).init_state.rot=tuple(pose['quaternion_wxyz'])
            if getattr(args,'diagnostics',False):
                from toast_rack_runtime_diagnostics import reporting_spawner
                for i in range(4):
                    spawn=getattr(cfg.scene,f'bread_{i}').spawn
                    spawn.func=reporting_spawner(spawn.func)
            env=gym.make('Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2',cfg=cfg).unwrapped
            if getattr(args,'diagnostics',False):
                from toast_rack_runtime_diagnostics import Contacts
                contacts=Contacts(env,out,args.scenario_id)
            result=runtime_audit(env,args,out)
            if contacts is not None:result['contact_report_errors']=contacts.errors
            result['initial_bread_pose_candidate']=None if not candidate else dict(path=str(candidate),sha256=sha(candidate),status='EXPERIMENTAL')
            atomic_json(out/(args.scenario_id+'.json'),result)
    except BaseException:
        failure=traceback.format_exc();print('WORKER_EXCEPTION_BEFORE_CLOSE\n'+failure,file=sys.stderr,flush=True)
        atomic_json(out/(args.scenario_id+'.exception.json'),dict(traceback=failure))
        if result_status(out/(args.scenario_id+'.json'))['status']=='MISSING':
            atomic_json(out/(args.scenario_id+'.json'),dict(scenario_id=args.scenario_id,stability='ERROR',reset='NOT_VERIFIED',full_task='NOT_VERIFIED',error=failure))
    finally:
        if contacts is not None:
            try:contacts.close()
            except Exception:cleanup.append(dict(stage='contact_report_close',traceback=traceback.format_exc()))
        try:
            import torch
            with torch.inference_mode():cleanup.extend(close_safely(env,app))
        except BaseException:cleanup=[dict(stage='cleanup_wrapper',traceback=traceback.format_exc())]
        atomic_json(out/(args.scenario_id+'.lifecycle.json'),dict(status='ERROR' if failure or cleanup else 'PASS',physics_exception=failure,cleanup_errors=cleanup))
    if failure or cleanup:raise SystemExit(1)

def runtime_audit(env,args,out):
    import numpy as np
    import torch
    from scipy.spatial.transform import Rotation
    def arr(t):return t.detach().cpu().numpy()
    def snap():
        result={}
        for n in NAMES:
            asset=env.scene[n]
            if n=='bread_shelf':
                p,q=asset.get_world_poses();vel=np.zeros(6)
            else:
                p,q=asset.data.root_pos_w,asset.data.root_quat_w;vel=arr(asset.data.root_state_w[0,7:13])
            result[n]=dict(position=(arr(p[0])-arr(env.scene.env_origins[0])).tolist(),quaternion=arr(q[0]).tolist(),velocity=vel.tolist())
        result['robot_joints']=arr(env.scene['robot'].data.joint_pos[0]).tolist()
        for n in NAMES:
            if not all(np.isfinite(result[n][k]).all() for k in ('position','quaternion','velocity')):
                raise ValueError('Nonfinite physics state: '+n)
        if not np.isfinite(result['robot_joints']).all():raise ValueError('Nonfinite robot state')
        return result
    def reset_check():
        actual=snap();errors=[]
        for n in NAMES:
            target=getattr(env.cfg.scene,n).init_state;a=actual[n]
            if np.max(np.abs(np.array(a['position'])-target.pos))>LIMITS['reset_position_m']:errors.append(n+'_position')
            q=np.array(a['quaternion']);t=np.array(target.rot)
            if 1-abs(np.dot(q,t))/(np.linalg.norm(q)*np.linalg.norm(t))>LIMITS['reset_quaternion_dot_error']:errors.append(n+'_rotation')
        cycle=env.toast_cycle
        state={n:arr(getattr(cycle,n)).tolist() for n in (*cycle.STATE_NAMES,*cycle.BREAD_STATE_NAMES)}
        if any(np.any(v) for v in state.values()):errors.append('cycle_state_nonzero')
        colors=[]
        for diffuse,emission in env.lever_indicators._colors:
            c=list(diffuse.Get());light=list(emission.Get());colors.append([c,light])
            if not np.allclose(c,[.025]*3,atol=1e-6) or not np.allclose(light,[0]*3,atol=1e-6):errors.append('LED_material_not_off')
        if any(env.lever_indicators._states):errors.append('LED_state_not_off')
        toaster=env.scene['toaster']
        if not torch.allclose(toaster.data.joint_pos,toaster.data.default_joint_pos,atol=5e-5,rtol=0):errors.append('toaster_joint_reset')
        return dict(status='FAIL' if errors else 'PASS',errors=errors,pose=actual,cycle=state,led_materials=colors)
    env.reset();first=reset_check()
    if getattr(args,'diagnostics',False):
        from toast_rack_runtime_diagnostics import capture
        capture(env,out,args.scenario_id,'initial')
    # Checked existing action semantics: zero relative wrist delta + native standby/nullspace;
    # +1 opens coupled grippers; .25*(+1)-.25=0 is lift position target.
    assert env.action_manager.total_action_dim==15
    assert env.cfg.actions.lift.scale==.25 and env.cfg.actions.lift.offset==-.25
    assert env.cfg.actions.left_arm.controller.use_relative_mode and env.cfg.actions.right_arm.controller.use_relative_mode
    action=torch.zeros((1,15),device=env.device);action[:,12:]=1
    runs=[]
    for repeat in range(2):
        initial=snap();frames=[];events=[];original=env.scene.update
        def observed_update(dt,*a,**kw):
            original(dt,*a,**kw)
            frames.append(snap()) # every physics substep, before the manager checks terminations
        env.scene.update=observed_update
        steps=math.ceil(max(5.,args.seconds)/env.step_dt)
        trace=out/f'{args.scenario_id}.run{repeat+1}.jsonl.gz'
        try:
            with torch.inference_mode():
                for step in range(steps):
                    _,_,terminated,truncated,_=env.step(action)
                    if bool((terminated|truncated).any()):
                        events.append(dict(step=step+1,terminated=bool(terminated.any()),truncated=bool(truncated.any())))
                        break
        finally:
            env.scene.update=original
            with gzip.open(trace,'wt') as f:
                for i,frame in enumerate(frames):f.write(json.dumps(dict(physics_sample=i+1,simulation_time_s=(i+1)*getattr(env,'physics_dt',env.step_dt),pose=frame))+'\n')
        final=snap();fail=[];objects={}
        if getattr(args,'diagnostics',False):
            from toast_rack_runtime_diagnostics import capture
            capture(env,out,args.scenario_id,f'final_run{repeat+1}')
        # Geometric fall threshold uses authored collision/visual hull min Z, not object root height.
        from generate_current_toast_scenarios import geometry,current_contract
        base,_=current_contract();verts,_=geometry(base)
        for n in NAMES:
            initial_p=np.array(initial[n]['position']);q0=initial[n]['quaternion']
            path=[initial,*frames,final];poses=[f[n] for f in path]
            move=max(float(np.linalg.norm(np.array(p['position'])-initial_p)) for p in poses)
            turn=max(angle(p['quaternion'],q0) for p in poses)
            lin=float(np.linalg.norm(final[n]['velocity'][:3]));ang=float(np.linalg.norm(final[n]['velocity'][3:]))
            thresholds=LIMITS['bread_rotation_deg'] if n.startswith('bread_') and n!='bread_shelf' else LIMITS['plate_rotation_deg'] if n=='plate' else LIMITS['toaster_rotation_deg']
            objfail=[]
            if move>LIMITS['object_translation_m']:objfail.append('displacement')
            if turn>thresholds:objfail.append('tipped_or_rotated')
            if lin>=LIMITS['final_linear_speed_m_s'] or ang>LIMITS['final_angular_speed_rad_s']:objfail.append('final_velocity')
            mesh=verts['bread' if n.startswith('bread_') and n!='bread_shelf' else n]
            scale=getattr(env.cfg.scene,n).spawn.scale or (1,1,1)
            bottom=min(float((Rotation.from_quat(np.array(p['quaternion'])[[1,2,3,0]]).apply(mesh*np.array(scale))+p['position'])[:,2].min()) for p in poses)
            if bottom<.994051338865205-LIMITS['below_table_m']:objfail.append('below_table')
            localerror=None
            if n.startswith('bread_') and n!='bread_shelf':
                def local(f):
                    s=f['bread_shelf'];return Rotation.from_quat(np.array(s['quaternion'])[[1,2,3,0]]).inv().apply(np.array(f[n]['position'])-s['position'])
                local0=local(initial);localerror=np.max(np.abs(np.array([local(f)-local0 for f in path])),axis=0)
                if np.any(localerror>LIMITS['bread_rack_local_error_m']):objfail.append('groove_departure')
            objects[n]=dict(initial=initial[n],final=final[n],max_translation_m=move,max_rotation_deg=turn,
                final_linear_speed_m_s=lin,final_angular_speed_rad_s=ang,min_geometry_z_m=bottom,
                max_rack_local_error_m=None if localerror is None else localerror.tolist(),failures=objfail)
            fail.extend(n+':'+s for s in objfail)
        drift=max(float(np.max(np.abs(np.array(f['robot_joints'])-initial['robot_joints']))) for f in [initial,*frames,final])
        if drift>LIMITS['robot_joint_drift_rad_or_m']:fail.append('robot_standby_drift')
        if events:fail.append('unexpected_termination_or_timeout')
        if env.toast_cycle.phase.any():fail.append('unexpected_cycle_started')
        runs.append(dict(status='FAIL' if fail else 'PASS',sim_seconds=(step+1)*env.step_dt,
            physics_samples=len(frames),objects=objects,robot_max_joint_drift=drift,events=events,failures=fail,trace=trace.name))
        from toast_audit_lifecycle import atomic_json
        atomic_json(out/(args.scenario_id+'.json'),dict(scenario_id=args.scenario_id,stability='INCOMPLETE',reset='INCOMPLETE',initial_reset=first,runs=runs,full_task='NOT_VERIFIED'))
        if repeat==0:
            # Explicit reset challenge ONLY after the physical trial; never step seeded state.
            for name in (*env.toast_cycle.STATE_NAMES,*env.toast_cycle.BREAD_STATE_NAMES):getattr(env.toast_cycle,name).fill_(1)
            env.toast_cycle.phase.fill_(2);env._update_lever_indicators(force=True)
            env.reset();second=reset_check()
    return dict(scenario_id=args.scenario_id,limits=LIMITS,initial_reset=first,challenged_reset=second,runs=runs,
        stability='PASS' if all(r['status']=='PASS' for r in runs) else 'FAIL',
        reset='PASS' if first['status']==second['status']=='PASS' else 'FAIL',full_task='NOT_VERIFIED')

def batch(args,out):
    data=load(args.manifest);entries=data['scenarios']
    if args.scenario_id:
        entries=[e for e in entries if e['id']==args.scenario_id]
        if not entries:raise ValueError('Unknown scenario ID')
    elif getattr(args,'initial_bread_poses',None):raise ValueError('Candidate requires a single --scenario-id; validate it before expanding')
    if not args.scenario_id:
        gate=getattr(args,'gate_result',None)
        if gate is None:raise ValueError('Full batch requires --gate-result from successful scenario 000 physics and process')
        from toast_audit_lifecycle import result_status
        checked=result_status(gate);g=checked.get('data',{})
        process=load(Path(gate).with_suffix('.process.json'))
        if (g.get('scenario_id')!='toast_v20261108_000' or g.get('stability')!='PASS' or g.get('reset')!='PASS'
                or len(g.get('runs',[]))!=2 or any(r.get('sim_seconds',0)<5 for r in g['runs'])
                or process.get('process_status')!='PASS' or g.get('initial_bread_pose_candidate')):
            raise ValueError('Pilot physics/reset/process not PASS, or candidate not promoted to versioned manifest')
        if load(Path(gate).parent/'run_config.json')['manifest_sha256']!=sha(args.manifest):raise ValueError('Gate manifest mismatch')
    cfg_path=ROOT/'source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2'
    paths=list(dict.fromkeys([*data['provenance']['source_sha256'],*data['provenance']['asset_sha256'],
                            *(str(p.relative_to(ROOT)) for p in cfg_path.glob('*.py'))]))
    fingerprints={p:sha(ROOT/p) for p in paths}
    dump(out/'run_config.json',dict(manifest_sha256=sha(args.manifest),source_asset_sha256=fingerprints,limits=LIMITS,seconds=args.seconds))
    for e in entries:
        command=[sys.executable,str(Path(__file__).resolve()),'--mode','worker','--manifest',str(Path(args.manifest).resolve()),
                 '--output',str(out),'--scenario-id',e['id'],'--seconds',str(args.seconds),'--device',args.device]
        if args.headless:command.append('--headless')
        if getattr(args,'diagnostics',False):command.append('--diagnostics')
        if getattr(args,'initial_bread_poses',None):command += ['--initial-bread-poses',str(Path(args.initial_bread_poses).resolve())]
        with (out/(e['id']+'.log')).open('w') as f:
            result=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
        from toast_audit_lifecycle import process_record,result_status
        process=process_record(out,e['id'],result.returncode)
        physics=result_status(out/(e['id']+'.json'))
        print(e['id'],'physics=',physics.get('data',{}).get('stability',physics['status']),'process=',process['process_status'],flush=True)
    assert sha(args.manifest)==load(out/'run_config.json')['manifest_sha256']
    assert all(sha(ROOT/p)==digest for p,digest in fingerprints.items()), 'Source/asset changed during audit'

def merge(args,out):
    rows=load(Path(args.static_dir)/'results.json');runtime=Path(args.runtime_dir)
    assert load(runtime/'run_config.json')['manifest_sha256']==load(Path(args.static_dir)/'audit.json')['manifest_sha256']==sha(args.manifest)
    prior=load(Path(args.static_dir)/'audit.json')
    runtime_hashes=load(runtime/'run_config.json')['source_asset_sha256']
    for key in ('asset_hashes','source_hashes'):
        for p,digest in prior[key].items():
            assert runtime_hashes.get(p)==digest, 'Static/runtime source mismatch: '+p
    for r in rows:
        p=runtime/(r['scenario_id']+'.json')
        if p.exists():
            from toast_audit_lifecycle import result_status
            checked=result_status(p)
            if checked['status']!='VALID':
                r['stability']='ERROR';r['result_json_status']=checked['status'];r['reasons'].append(checked['error']);continue
            d=checked['data'];r['stability']=d['stability'];r['reset']=d['reset'];r['runtime_detail']=str(p.resolve())
            process_file=runtime/(r['scenario_id']+'.process.json')
            r['process_result']=load(process_file) if process_file.exists() else {'process_status':'NOT_RECORDED'}
            r['process_status']=r['process_result']['process_status']
            if r['process_status']=='ERROR':r['reasons'].append('process_ERROR_separate_from_physics')
            if 'runs' in d:
                r['runtime_objects_by_run']=[t['objects'] for t in d['runs']]
                r['sim_seconds_by_run']=[t['sim_seconds'] for t in d['runs']]
                r['termination_events']=[t['events'] for t in d['runs']]
            r['reasons']=[x for x in r['reasons'] if x!='PhysX_NOT_RUN']
            r['reasons'] += [d['error']] if 'error' in d else [f'run{i+1}: '+','.join(t['failures']) for i,t in enumerate(d.get('runs',[])) if t['failures']]
            if d.get('initial_reset',{}).get('errors'):r['reasons'].append('initial_reset:'+','.join(d['initial_reset']['errors']))
            if d.get('challenged_reset',{}).get('errors'):r['reasons'].append('challenged_reset:'+','.join(d['challenged_reset']['errors']))
        else:
            r['result_json_status']='MISSING';r['reasons'].append('runtime_result_JSON_missing')
    write_report(out,rows)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=['static','physx','worker','report'],required=True)
    p.add_argument('--manifest',type=Path,default=DEFAULT);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--gate-result',type=Path);p.add_argument('--diagnostics',action='store_true');p.add_argument('--initial-bread-poses',type=Path)
    p.add_argument('--scenario-id');p.add_argument('--seconds',type=float,default=5.)
    p.add_argument('--headless',action='store_true');p.add_argument('--device',default='cuda:0')
    p.add_argument('--static-dir',type=Path);p.add_argument('--runtime-dir',type=Path)
    args=p.parse_args()
    if not math.isfinite(args.seconds) or args.seconds<5:p.error('--seconds must be at least 5 simulation seconds')
    if args.mode=='report' and (not args.static_dir or not args.runtime_dir):p.error('report requires --static-dir and --runtime-dir')
    if args.mode=='worker' and not args.scenario_id:p.error('worker requires --scenario-id')
    out=args.output.resolve()
    if args.mode=='worker' and (out/(args.scenario_id+'.json')).exists():p.error('Worker result already exists')
    out.mkdir(parents=True,exist_ok=args.mode=='worker')
    {'static':static,'worker':worker,'physx':batch,'report':merge}[args.mode](args,out)
if __name__=='__main__':main()
