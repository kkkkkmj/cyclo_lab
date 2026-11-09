"""PhysX bread_0 exposure diagnostic. No task config or post-fixture pose edits."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TASK = 'Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2'


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(args):
    import gymnasium as gym
    import numpy as np
    import torch
    from PIL import Image, ImageDraw
    from pxr import UsdGeom
    from isaaclab.sensors import CameraCfg
    from isaaclab.sim import PinholeCameraCfg
    import isaaclab.utils.math as math_utils
    from isaaclab_tasks.utils.parse_cfg import parse_env_cfg
    import cyclo_lab
    from cyclo_lab.manager_based.manipulation.make_toast.config.ffw_bg2 import bimanual_mdp
    from exposure_geometry import bake_bread, bake_rim, world, measure, rotation

    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    status = {'status': 'RUNNING', 'task': TASK, 'slots': []}
    dump(out/'status.json', status)
    env = None
    try:
        if not Path(cyclo_lab.__file__).resolve().is_relative_to(ROOT/'source/cyclo_lab'):
            raise RuntimeError('Wrong checkout imported: ' + cyclo_lab.__file__)
        cfg = parse_env_cfg(TASK, device=args.device, num_envs=1)
        # Camera only. Keep timing, solver, termination, contacts, gains and targets intact.
        cfg.scene.exposure_side = CameraCfg(
            prim_path='{ENV_REGEX_NS}/ExposureSide', update_period=0.,
            width=960, height=720, data_types=['rgb'], update_latest_camera_pose=True,
            spawn=PinholeCameraCfg(focal_length=35., horizontal_aperture=20.955,
                                   clipping_range=(.01, 10.)))
        env = gym.make(TASK, cfg=cfg).unwrapped
        if abs(.5/env.physics_dt - round(.5/env.physics_dt)) > 1e-6:
            raise RuntimeError('Physics dt cannot sample exactly +0.5 s; review sampling without changing dt')
        (out/'resolved_config.txt').write_text(repr(cfg.to_dict()))
        files = list((ROOT/'source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast').rglob('*.py'))
        files += list((ROOT/'source/cyclo_lab/data/objects/robodojo_make_toast').rglob('*'))
        files += list((ROOT/'source/cyclo_lab/data/objects/bread_slot').glob('*'))
        files += list(HERE.glob('*.py'))
        scene_assets = {}
        for name, asset_cfg in vars(cfg.scene).items():
            locator = getattr(getattr(asset_cfg, 'spawn', None), 'usd_path', None)
            if locator:
                path = Path(locator)
                scene_assets[name] = dict(usd_path=str(locator), sha256=sha(path) if path.is_file() else None)
        dump(out/'provenance.json', dict(task=TASK, checkout=str(ROOT), module=cyclo_lab.__file__,
            scenario='Unmodified v2 default layout; no scenario manifest; bread_0 fixture only',
            scene_assets=scene_assets,
            hashes={str(p.relative_to(ROOT)): sha(p) for p in files if p.is_file()},
            setup='One bread_0 root-state write above selected slot, 1.2 s free settling, one lever-only joint-state write to upper limit. Other breads remain in default rack positions. Zero relative IK actions, open grippers. Not robot grasp validation.',
            measurement='All composed visible polygon mesh vertices baked in rigid-body coordinates (including scale); current PhysX link/root pose applied to every vertex. Vertical height ratio, not area or volume.',
            sampling='After every existing physics scene.update; phase transitions immediately after original ToastCycle.update, before next physics step. No extra physics steps for RGB.',
            camera='Dedicated level side RGB camera; render-only refresh at capture; separate projected annotations. Hidden bottom is a geometry annotation, not a visible RGB edge.'))
        action = torch.zeros((1, env.action_manager.total_action_dim), device=env.device)
        if action.shape[1] != 15:
            raise RuntimeError('Unexpected action layout')
        action[:, 12:] = 1

        for slot in (0, 1):
            folder = out/f'bread_0_slot_{slot}'
            folder.mkdir()
            env.reset()
            cycle, toaster, bread = env.toast_cycle, env.scene['toaster'], env.scene['bread_0']
            stage = env.scene.stage
            env.sim.render()
            bread_path = bread.root_physx_view.prim_paths[0]
            bread_vertices, bread_evidence = bake_bread(stage.GetPrimAtPath(bread_path))
            base_id = toaster.body_names.index('base')
            base_path = env.scene.env_prim_paths[0] + '/Toaster/base'
            rim_vertices, rim_evidence = bake_rim(stage.GetPrimAtPath(base_path))
            dump(folder/'geometry.json', dict(bread=bread_evidence, rim=rim_evidence))
            np.savez_compressed(folder/'body_vertices.npz', bread=bread_vertices, rim=rim_vertices)
            camera = env.scene['exposure_side']
            camera_prim = stage.GetPrimAtPath(env.scene.env_prim_paths[0]+'/ExposureSide')
            y = (-.026455, .0253585)[slot]
            toaster_pos = toaster.data.root_pos_w[0].cpu().numpy()
            toaster_quat = toaster.data.root_quat_w[0].cpu().numpy()
            target = world(np.array([[-.003, y, .105]]), toaster_pos, toaster_quat)[0]
            # Horizontal camera sightline, facing bread broad side from selected slot's side.
            side = rotation(toaster_quat) @ np.array([0., -1. if slot == 0 else 1., 0.])
            side[2] = 0
            side /= np.linalg.norm(side)
            eye = target + side * .65
            camera.set_world_poses_from_view(
                torch.tensor(eye[None], device=env.device, dtype=torch.float32),
                torch.tensor(target[None], device=env.device, dtype=torch.float32))

            clock = {'t': 0., 'armed': False, 'rise': None, 'complete': None}
            rows, events = [], {}
            fields = ['bread_id', 'slot', 'sim_time_s', 'phase', 'carriage_m',
                      'z_top', 'z_bottom', 'z_rim', 'height_mm', 'exposed_mm', 'exposed_pct',
                      'in_slot', 'other_bread_in_slot', 'heating_time_s', 'cycle_elapsed_s',
                      'carriage_velocity_m_s', 'carriage_world_z_m', 'command_m', 'sample_kind',
                      'bread_x', 'bread_y', 'bread_z', 'bread_qw', 'bread_qx', 'bread_qy', 'bread_qz',
                      'rim_a', 'rim_b', 'rim_c', 'rim_d']
            trace = (folder/'trace.csv').open('w', newline='')
            writer = csv.DictWriter(trace, fieldnames=fields)
            writer.writeheader()

            def cpu(t):
                return t.detach().cpu().numpy().copy()

            def read(kind):
                bp, bq = cpu(bread.data.root_pos_w[0]), cpu(bread.data.root_quat_w[0])
                rp, rq = cpu(toaster.data.body_link_pos_w[0, base_id]), cpu(toaster.data.body_link_quat_w[0, base_id])
                bw, rw = world(bread_vertices, bp, bq), world(rim_vertices, rp, rq)
                values, center, plane = measure(bw, rw)
                row = dict(bread_id='bread_0', slot=slot, sim_time_s=round(clock['t'], 9),
                    phase=int(cycle.phase[0]), carriage_m=float(toaster.data.joint_pos[0, cycle.carriage_id]),
                    in_slot=bool(bimanual_mdp.bread_in_slot(env, 'bread_0', slot)[0]),
                    other_bread_in_slot=any(bool(bimanual_mdp.bread_in_slot(env, f'bread_{i}', s)[0])
                                            for i in (1, 2, 3) for s in (0, 1)),
                    heating_time_s=float(cycle.heating_time[0]), cycle_elapsed_s=float(cycle.elapsed[0]),
                    carriage_velocity_m_s=float(toaster.data.joint_vel[0, cycle.carriage_id]),
                    carriage_world_z_m=float(toaster.data.body_link_pos_w[0, toaster.body_names.index('bread_carriage'), 2]),
                    command_m=float(cycle.command[0]), sample_kind=kind, **values)
                row.update(zip(('bread_x','bread_y','bread_z','bread_qw','bread_qx','bread_qy','bread_qz'), np.r_[bp,bq].tolist()))
                row.update(zip(('rim_a','rim_b','rim_c','rim_d'), plane.tolist()))
                rows.append(row)
                writer.writerow(row)
                trace.flush()
                return row, center, plane, bw, rw

            def capture(label, measurement):
                row, center, plane, bw, rw = measurement
                before = cpu(bread.data.root_state_w)
                # Refresh Hydra at the same physical timestamp; do not advance PhysX.
                for _ in range(4):
                    env.sim.render()
                camera.update(0., force_recompute=True)
                rgb = cpu(camera.data.output['rgb'][0])[:, :, :3]
                if rgb.dtype != np.uint8:
                    rgb = (np.clip(rgb, 0, 1)*255).astype(np.uint8)
                if rgb.shape != (720, 960, 3) or rgb.std() < 1:
                    raise RuntimeError('No usable actual side RGB frame')
                if not np.array_equal(before, cpu(bread.data.root_state_w)):
                    raise RuntimeError('Physics changed during RGB capture')
                Image.fromarray(rgb).save(folder/(label+'.rgb.png'))
                annotated = Image.fromarray(rgb)
                draw = ImageDraw.Draw(annotated)
                cm = np.asarray(UsdGeom.Xformable(camera_prim).ComputeLocalToWorldTransform(0.))
                inv = np.linalg.inv(cm)
                cam = UsdGeom.Camera(camera_prim)
                fx = 960*cam.GetFocalLengthAttr().Get()/cam.GetHorizontalApertureAttr().Get()
                fy = 720*cam.GetFocalLengthAttr().Get()/cam.GetVerticalApertureAttr().Get()

                def project(points):
                    points = np.asarray(points) @ inv[:3, :3] + inv[3, :3]
                    return np.c_[480+fx*points[:,0]/(-points[:,2]), 360-fy*points[:,1]/(-points[:,2])]

                right = cm[0, :3].copy()
                right[2] = 0
                right /= np.linalg.norm(right)
                line_evidence = {}
                for name, color in [('z_top', '#ff6868'), ('z_rim', '#36e6ff'), ('z_bottom', '#8fff73')]:
                    endpoints = np.array([center-right*.13, center+right*.13])
                    endpoints[:,2] = row[name]
                    if name == 'z_rim':
                        endpoints[:,2] = -(endpoints[:,:2] @ plane[:2]+plane[3])/plane[2]
                    pixels = project(endpoints)
                    draw.line([tuple(x) for x in pixels], fill=color, width=2)
                    draw.text(tuple(pixels[0]+[0,-14]), f'{name} = {row[name]:.6f} m', fill=color, stroke_width=1, stroke_fill='black')
                    line_evidence[name] = dict(world=endpoints.tolist(), pixels=pixels.tolist())
                draw.rectangle((0,0,960,42), fill='black')
                draw.text((10,6), f'bread_0 slot {slot} | {label} | t={row["sim_time_s"]:.3f}s phase={row["phase"]}', fill='white')
                draw.text((10,23), f'Vertical exposure {row["exposed_pct"]:.3f}% | E={row["exposed_mm"]:.3f} mm H={row["height_mm"]:.3f} mm | in_slot={row["in_slot"]}', fill='white')
                annotated.save(folder/(label+'.annotated.png'))
                np.savez_compressed(folder/(label+'.world_vertices.npz'), bread=bw, rim=rw)
                dump(folder/(label+'.camera.json'), dict(sample=row, camera_world_matrix=cm.tolist(),
                     focal_pixels=[fx,fy], lines=line_evidence, note='Projected geometry height markers; bottom can be occluded by housing.'))

            def event(name, measurement, rgb=False):
                events[name] = dict(event=name, **measurement[0])
                if rgb:
                    capture(name, measurement)

            original_update = env.scene.update
            original_cycle = cycle.update

            def scene_update(dt):
                original_update(dt)
                clock['t'] += dt
                sample = read('physics')
                if clock['armed'] and clock['complete'] is not None:
                    delay = clock['t'] - clock['complete']
                    for offset, label in ((.5, '04_complete_plus_0p5s'), (1., '05_complete_plus_1p0s')):
                        if label not in events and delay >= offset-1e-8:
                            event(label, sample, rgb=(offset == 1.))

            def cycle_update(dt):
                previous = int(cycle.phase[0])
                before = read('pre_cycle_update') if clock['armed'] and previous == 2 else None
                original_cycle(dt)  # exactly once, with the original dt
                phase = int(cycle.phase[0])
                if clock['armed'] and phase != previous:
                    sample = read('phase_transition_before_physics')
                    if previous == 0 and phase == 1:
                        event('cycle_started', sample)
                    if previous == 2 and phase == 3:
                        event('01_before_heating_end', before)
                        clock['rise'] = clock['t']
                        event('02_rise_start', sample)
                    if previous == 3 and phase == 4:
                        clock['complete'] = clock['t']
                        event('03_first_phase4', sample, rgb=True)

            env.scene.update = scene_update
            cycle.update = cycle_update
            try:
                state = bread.data.default_root_state.clone()
                local = torch.tensor([[-.003, y+.0056, .14]], device=env.device)
                quat = torch.tensor([[.7071067811865476, .7071067811865476, 0., 0.]], device=env.device)
                pos, quat = math_utils.combine_frame_transforms(toaster.data.root_pos_w, toaster.data.root_quat_w, local, quat)
                state[:, :3], state[:, 3:7], state[:, 7:] = pos, quat, 0.
                bread.write_root_state_to_sim(state)  # only bread fixture write in this slot run
                dump(folder/'fixture.json', dict(bread_root_state=cpu(state).tolist(), slot=slot,
                     local_position=cpu(local).tolist(), settle_s=1.2, robot_grasp_validated=False))

                def step():
                    result = env.step(action)
                    if bool(result[2].any()) or bool(result[3].any()):
                        raise RuntimeError('Existing termination fired; run invalid (termination unchanged)')

                for _ in range(round(1.2/env.step_dt)):
                    step()
                settled = read('loaded_check')
                event('loaded_check', settled, rgb=True)
                # Require sustained existing slot predicate and a resting slice before input.
                recent = [r for r in rows if r['sim_time_s'] >= clock['t']-.2]
                if (not recent or not all(r['in_slot'] and not r['other_bread_in_slot'] for r in recent)
                    or float(torch.linalg.vector_norm(bread.data.root_lin_vel_w[0])) >= .15
                    or int(cycle.phase[0]) != 0):
                    raise RuntimeError('bread_0 did not settle alone in selected slot; no cycle result')
                clock['armed'] = True
                lever = toaster.data.joint_pos_limits[:, cycle.lever_id, 1:2].clone()
                dump(folder/'lever_input.json', dict(time_s=clock['t'], joint_name='joint_1',
                     position_m=cpu(lever).tolist(), velocity_m_s=0., method='One joint-state write only to lever; no carriage target/state override'))
                toaster.write_joint_state_to_sim(lever, torch.zeros_like(lever), joint_ids=[cycle.lever_id])
                while clock['t'] < 15.:
                    step()
                    if '05_complete_plus_1p0s' in events:
                        break
                required = ['01_before_heating_end','02_rise_start','03_first_phase4',
                            '04_complete_plus_0p5s','05_complete_plus_1p0s']
                if any(k not in events for k in required) or 'cycle_started' not in events:
                    raise RuntimeError('Original cycle did not reach all requested timestamps')
                cycle_rows = [r for r in rows if r['sim_time_s'] >= events['cycle_started']['sim_time_s']]
                valid = (all(r['in_slot'] and not r['other_bread_in_slot'] for r in cycle_rows)
                         and bool(cycle.heated_bread[0,0]))
                if not valid:
                    raise RuntimeError('Slice absent/misaligned during cycle or not heated; raw diagnostics only, not normal exposure')
                window = [r for r in rows if r['phase'] >= 3 and clock['rise'] <= r['sim_time_s'] <= clock['complete']+1.+1e-8]
                maximum = max(window, key=lambda r:r['exposed_pct'])
                dump(folder/'summary.json', dict(status='VALID', events=events, sampled_maximum=maximum,
                     physics_dt_s=env.physics_dt, control_dt_s=env.step_dt,
                     maximum_scope='Discrete physics samples plus exact phase transitions; not an analytic continuous maximum'))
                with (folder/'summary.csv').open('w', newline='') as f:
                    w = csv.DictWriter(f, fieldnames=['event']+fields)
                    w.writeheader()
                    w.writerows(events[k] for k in required)
                with (folder/'rise_trace.csv').open('w', newline='') as f:
                    w = csv.DictWriter(f, fieldnames=fields)
                    w.writeheader()
                    w.writerows(window)
                table = ['event | time_s | phase | carriage_m | z_top | z_bottom | z_rim | H_mm | E_mm | exposure_pct']
                for k in required:
                    r = events[k]
                    table.append(f'{k} | '+ ' | '.join(f'{r[n]:.6f}' for n in ('sim_time_s','phase','carriage_m','z_top','z_bottom','z_rim','height_mm','exposed_mm','exposed_pct')))
                table.append(f'Sampled maximum: {maximum["exposed_pct"]:.6f}% at t={maximum["sim_time_s"]:.6f}s')
                (folder/'summary.txt').write_text('\n'.join(table)+'\n')
                status['slots'].append(dict(slot=slot, status='VALID', main_results=[events[required[2]], events[required[4]]], maximum=maximum))
                dump(out/'status.json', status)
            finally:
                env.scene.update = original_update
                cycle.update = original_cycle
                trace.close()
                dump(folder/'events.json', events)
        status['status'] = 'VALID_BOTH_SLOTS_BREAD_0_ONLY'
        dump(out/'status.json', status)
        print(json.dumps(status, indent=2), flush=True)
    except BaseException:
        status.update(status='FAILED_NOT_A_MEASUREMENT_RESULT', error=traceback.format_exc())
        dump(out/'status.json', status)
        raise
    finally:
        if env is not None:
            env.close()


if __name__ == '__main__':
    from isaaclab.app import AppLauncher
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    AppLauncher.add_app_launcher_args(parser)
    args = parser.parse_args()
    args.enable_cameras = True
    app = AppLauncher(args).app
    try:
        main(args)
    finally:
        app.close()
