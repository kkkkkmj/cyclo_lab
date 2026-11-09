# Copyright (c) 2022-2025, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
"""Script to replay demonstrations with Isaac Lab environments."""

"""Launch Isaac Sim Simulator first."""


import argparse
import time
import json
from replay_validation import compare_states, resolve_episode_indices
from replay_outcome import record_outcome
from replay_scene_audit import TimelineProbe
from replay_plate_audit import plate_checkpoint, plate_configuration, step_with_first_physics_checkpoint

from isaaclab.app import AppLauncher

# add argparse arguments
parser = argparse.ArgumentParser(description="Replay demonstrations in Isaac Lab environments.")
parser.add_argument("--num_envs", type=int, default=1, help="Number of environments to replay episodes.")
parser.add_argument("--task", type=str, default=None, help="Force to use the specified task.")
selection = parser.add_mutually_exclusive_group()
selection.add_argument(
    "--select_episodes",
    type=int,
    nargs="+",
    default=[],
    help="A list of episode indices to be replayed. Keep empty to replay all in the dataset file.",
)
selection.add_argument("--select_episode_names", nargs="+", default=[], help="Exact HDF5 names, e.g. demo_8; mutually exclusive with list indices.")
parser.add_argument("--audit-dir", help="New directory for read-only timeline/plate/USD/PhysX evidence")
parser.add_argument('--contact-probe-dir', help='New per-physics contact evidence directory; action replay only, one environment/episode')
parser.add_argument('--bridge-dir', help='Acquire existing simulator lock for contact reproduction; no VR input')
parser.add_argument('--contact-solver-position-iterations',type=int,choices=[64],help='Experimental single-factor robot position-iteration candidate (baseline 32); never a default fix')
parser.add_argument('--contact-half-physics-dt',action='store_true',help='Experimental dt .01->.005; decimation/render interval doubled, action/control/render times unchanged')
parser.add_argument('--contact-free-gripper-check',action='store_true',help='Separate no-contact opening/closing diagnostic from recorded initial state; not a demonstration replay')
parser.add_argument("--dataset_file", type=str, default="datasets/dataset.hdf5", help="Dataset file to be replayed.")
parser.add_argument("--video_file", type=str, help="Export MP4: front overview above the three recorded RGB views.")
parser.add_argument("--video_max_frames", type=int, help="Limit exported frames for a quick video preview.")
parser.add_argument("--video_eye", type=float, nargs=3, default=(3.1, 0, 2.0),
                    help="Overview camera position, in metres relative to env_0.")
parser.add_argument("--video_target", type=float, nargs=3, default=(.35, 0, 1.0),
                    help="Overview camera look-at point, in metres relative to env_0.")
parser.add_argument(
    "--validate_states",
    action="store_true",
    default=False,
    help=(
        "Validate if the states, if available, match between loaded from datasets and replayed. Only valid if"
        " --num_envs is 1."
    ),
)
parser.add_argument(
    "--enable_pinocchio",
    action="store_true",
    default=False,
    help="Enable Pinocchio.",
)

parser.add_argument('--contact-slave-gains',action='store_true')
parser.add_argument('--contact-baseline-provenance')
# append AppLauncher cli args
AppLauncher.add_app_launcher_args(parser)
# parse the arguments
args_cli = parser.parse_args()
contact_lock=None
if args_cli.contact_slave_gains and (not args_cli.contact_probe_dir or args_cli.contact_half_physics_dt or args_cli.contact_solver_position_iterations):parser.error('slave gains require contact mode and cannot combine with solver/dt candidates')
if args_cli.contact_solver_position_iterations and not args_cli.contact_probe_dir:parser.error('candidate requires contact-probe-dir')
if (args_cli.contact_half_physics_dt or args_cli.contact_free_gripper_check) and not args_cli.contact_probe_dir:parser.error('contact options require contact-probe-dir')
if args_cli.contact_half_physics_dt and args_cli.contact_solver_position_iterations:parser.error('One physical factor per candidate')
if args_cli.contact_probe_dir:
    if args_cli.video_file or args_cli.num_envs!=1 or (not args_cli.validate_states and not args_cli.contact_free_gripper_check) or len(args_cli.select_episode_names)!=1 or not args_cli.bridge_dir:parser.error('contact replay requires one named episode, num_envs=1, validate_states (except free-gripper check), bridge-dir and no video export')
    from pathlib import Path
    import fcntl
    contact_lock=(Path(args_cli.bridge_dir)/'.simulation.lock').open('a')
    try:fcntl.flock(contact_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:parser.error('Existing simulator owns bridge; no process stopped')
    Path(args_cli.contact_probe_dir).mkdir(parents=True,exist_ok=False)
    args_cli.enable_cameras=True
if args_cli.audit_dir:
    from pathlib import Path
    Path(args_cli.audit_dir).mkdir(parents=True,exist_ok=False)
if args_cli.video_file:
    from pathlib import Path

    if args_cli.num_envs != 1:
        parser.error("--video_file requires --num_envs 1")
    if Path(args_cli.video_file).suffix.lower() != ".mp4":
        parser.error("--video_file must end in .mp4")
    if Path(args_cli.video_file).exists():
        parser.error("Video already exists; choose a new --video_file path")
    if args_cli.video_max_frames is not None and args_cli.video_max_frames < 1:
        parser.error("--video_max_frames must be positive")
    if args_cli.validate_states:
        parser.error("Video export displays saved states; use normal replay for --validate_states")
    args_cli.headless = True
    args_cli.enable_cameras = True

if args_cli.enable_pinocchio:
    # Import pinocchio before AppLauncher to force the use of the version installed by IsaacLab and not the one installed by Isaac Sim
    # pinocchio is required by the Pink IK controllers and the GR1T2 retargeter
    import pinocchio  # noqa: F401

# launch the simulator
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import gymnasium as gym
import os
import torch

from isaaclab.devices import Se3Keyboard, Se3KeyboardCfg
from isaaclab.utils.datasets import EpisodeData, HDF5DatasetFileHandler

if args_cli.enable_pinocchio:
    import isaaclab_tasks.manager_based.manipulation.pick_place  # noqa: F401
    import isaaclab_tasks.manager_based.locomanipulation.pick_place  # noqa: F401

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils.parse_cfg import parse_env_cfg

import cyclo_lab  # noqa: F401

is_paused = False


def play_cb():
    global is_paused
    is_paused = False


def pause_cb():
    global is_paused
    is_paused = True


def main():
    """Replay episodes loaded from a file."""
    global is_paused

    # Load dataset
    if not os.path.exists(args_cli.dataset_file):
        raise FileNotFoundError(f"The dataset file {args_cli.dataset_file} does not exist.")
    dataset_file_handler = HDF5DatasetFileHandler()
    dataset_file_handler.open(args_cli.dataset_file)
    env=None
    timeline=None
    contact_audit=None
    field_summary={}
    validation_episode_name=None
    state_validation_enabled=False
    validated_steps=mismatched_steps=expected_steps=0
    validation_started=time.perf_counter()
    try:
        env_name = dataset_file_handler.get_env_name()
        episode_count = dataset_file_handler.get_num_episodes()

        if episode_count == 0:
            print("No episodes found in the dataset.")
            exit()

        episode_names = list(dataset_file_handler.get_episode_names())
        episode_indices_to_replay = resolve_episode_indices(episode_names,args_cli.select_episodes,args_cli.select_episode_names)
        args_cli.select_episodes = list(episode_indices_to_replay)  # video exporter uses the same resolved order
        print(f'EPISODE_SELECTION indices={episode_indices_to_replay} names={[episode_names[i] for i in episode_indices_to_replay]}',flush=True)

        if args_cli.task is not None:
            env_name = args_cli.task.split(":")[-1]
        if env_name is None:
            raise ValueError("Task/env name was not specified nor found in the dataset.")

        num_envs = args_cli.num_envs

        env_cfg = parse_env_cfg(env_name, device=args_cli.device, num_envs=num_envs)

        # Restore fixed scenario BEFORE scene creation, including the static bread rack.
        # Legacy recordings without diagnostic metadata keep their existing behavior.
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
        from toast_recording_metadata import configure_replay, verify_static_rack, verify_initial_state
        scenario_metadata = configure_replay(args_cli.dataset_file, env_cfg, env_name)

        # Disable all recorders and terminations
        if args_cli.contact_probe_dir:
            # Same recorder read/render/observation order as teleop; never export a dataset.
            from isaaclab.envs.mdp.recorders.recorders_cfg import ActionStateRecorderManagerCfg
            from isaaclab.managers import DatasetExportMode
            from toast_overview import overview_cfg
            env_cfg.env_name=env_name
            env_cfg.recorders=ActionStateRecorderManagerCfg()
            env_cfg.recorders.dataset_export_mode=DatasetExportMode.EXPORT_NONE
            env_cfg.recorders.export_in_record_pre_reset=False
            env_cfg.scene.replay_overview=overview_cfg()
            if args_cli.contact_slave_gains:
                from slave_gain_experiment import override
                if not args_cli.contact_baseline_provenance:raise ValueError('Slave comparison requires verified baseline provenance')
                from slave_gain_experiment import verify_baseline
                verify_baseline(env_cfg,args_cli.contact_baseline_provenance)
                override(env_cfg)
            if args_cli.contact_half_physics_dt:
                if env_cfg.scene.robot.spawn.articulation_props.solver_position_iteration_count!=32:raise ValueError('half-dt experiment requires original position iterations=32')
                from replay_contact_audit import half_timestep
                half_timestep(env_cfg)
            if args_cli.contact_solver_position_iterations:
                if env_cfg.scene.robot.spawn.articulation_props.solver_position_iteration_count!=32:raise ValueError('Candidate expects baseline position iterations=32')
                env_cfg.scene.robot.spawn.articulation_props.solver_position_iteration_count=args_cli.contact_solver_position_iterations
        else:
            env_cfg.recorders = {}
            env_cfg.terminations = {}

        if args_cli.video_file:
            from replay_video import export_video

            export_video(env_name, env_cfg, args_cli, simulation_app)
            dataset_file_handler.close()
            return

        # create environment from loaded config
        env = gym.make(env_name, cfg=env_cfg).unwrapped
        if args_cli.contact_probe_dir:
            from replay_contact_audit import ReplayContactAudit
            contact_audit=ReplayContactAudit(env,args_cli.contact_probe_dir,args_cli.dataset_file,args_cli.contact_solver_position_iterations)
        if args_cli.audit_dir:
            env._replay_audit_dir=args_cli.audit_dir
            timeline=TimelineProbe(env)
        if scenario_metadata:
            verify_static_rack(env, scenario_metadata)
        if args_cli.contact_free_gripper_check:
            name=episode_names[episode_indices_to_replay[0]]
            ep=dataset_file_handler.load_episode(name,env.device)
            env.reset()
            env.reset_to(ep.get_initial_state(),torch.tensor([0],device=env.device),is_relative=True)
            verify_initial_state(env,ep.get_initial_state(),0)
            from replay_contact_audit import free_gripper_check
            free_gripper_check(contact_audit,ep,name)
            return

        teleop_interface = Se3Keyboard(Se3KeyboardCfg(pos_sensitivity=0.1, rot_sensitivity=0.1))
        teleop_interface.add_callback("N", play_cb)
        teleop_interface.add_callback("B", pause_cb)
        print('Press "B" to pause and "N" to resume the replayed actions.')

        # Determine if state validation should be conducted
        state_validation_enabled = False
        if args_cli.validate_states and num_envs == 1:
            state_validation_enabled = True
        elif args_cli.validate_states and num_envs > 1:
            print("Warning: State validation is only supported with a single environment. Skipping state validation.")

        audit_plate=state_validation_enabled and 'plate' in env.scene.rigid_objects

        # Get idle action (idle actions are applied to envs without next action)
        if hasattr(env_cfg, "idle_action"):
            idle_action = env_cfg.idle_action.repeat(num_envs, 1)
        else:
            idle_action = torch.zeros(env.action_space.shape)

        # reset before starting
        if timeline:timeline.mark('before_startup_reset')
        env.reset()
        if contact_audit:
            from toast_overview import position_overview
            position_overview(env)
        if timeline:timeline.mark('after_startup_reset')
        teleop_interface.reset()

        # simulate environment -- run everything in inference mode
        replayed_episode_count = 0
        validated_steps = mismatched_steps = expected_steps = 0
        validation_started=time.perf_counter()
        with torch.inference_mode():
            while simulation_app.is_running() and not simulation_app.is_exiting():
                env_episode_data_map = {index: EpisodeData() for index in range(num_envs)}
                first_loop = True
                has_next_action = True
                while has_next_action:
                    # initialize actions with idle action so those without next action will not move
                    actions = idle_action
                    has_next_action = False
                    for env_id in range(num_envs):
                        env_next_action = env_episode_data_map[env_id].get_next_action()
                        if env_next_action is None:
                            next_episode_index = None
                            while episode_indices_to_replay:
                                next_episode_index = episode_indices_to_replay.pop(0)
                                if next_episode_index < episode_count:
                                    break
                                next_episode_index = None

                            if next_episode_index is not None:
                                replayed_episode_count += 1
                                print(f"{replayed_episode_count :4}: Loading list_index={next_episode_index} name={episode_names[next_episode_index]} to env_{env_id}",flush=True)
                                validation_episode_name=episode_names[next_episode_index]
                                env._replay_audit_episode=validation_episode_name
                                episode_data = dataset_file_handler.load_episode(
                                    episode_names[next_episode_index], env.device
                                )
                                if state_validation_enabled:
                                    expected_steps += len(episode_data.data['actions'])
                                print(f'EPISODE_LOADED name={episode_names[next_episode_index]} frames={len(episode_data.data["actions"])}',flush=True)
                                env_episode_data_map[env_id] = episode_data
                                # Set initial state for the new episode
                                initial_state = episode_data.get_initial_state()
                                if timeline:timeline.mark('before_episode_reset_to')
                                env.reset_to(initial_state, torch.tensor([env_id], device=env.device), is_relative=True)
                                if timeline:timeline.mark('after_episode_reset_to')
                                if audit_plate:
                                    plate_configuration(env,scenario_metadata.get('timing') if scenario_metadata else None)
                                    plate_checkpoint(env,'after_reset_to_before_physics',initial_state)
                                if scenario_metadata:
                                    verify_static_rack(env, scenario_metadata)
                                    verify_initial_state(env, initial_state, env_id)
                                if contact_audit:contact_audit.start(episode_names[next_episode_index],episode_data)
                                # Get the first action for the new episode
                                env_next_action = env_episode_data_map[env_id].get_next_action()
                                has_next_action = True
                            else:
                                continue
                        else:
                            has_next_action = True
                        actions[env_id] = env_next_action
                    if not has_next_action:
                        break
                    if first_loop:
                        first_loop = False
                    else:
                        while is_paused:
                            env.sim.render()
                            continue
                    if contact_audit:contact_audit.begin(env_episode_data_map[0].next_action_index-1,actions)
                    try:
                        if audit_plate and env_episode_data_map[0].next_action_index==1:
                            step_result=step_with_first_physics_checkpoint(env,actions)
                        else:
                            step_result=env.step(actions)
                    finally:
                        if contact_audit:contact_audit.end()
                    if contact_audit and bool(step_result[2].any() or step_result[3].any()):raise RuntimeError('Original task termination during contact replay; no further actions')

                    if state_validation_enabled:
                        state_from_dataset = env_episode_data_map[0].get_next_state()
                        action_index=env_episode_data_map[0].next_action_index-1
                        if state_from_dataset is None:
                            raise RuntimeError(f'Missing recorded state at action-index={action_index}')
                        if audit_plate and action_index==0:
                            plate_checkpoint(env,'after_first_control_step',state_from_dataset)
                        phase='get_state';t=time.perf_counter()
                        print(f'VALIDATE action-index={action_index} get_state BEGIN',flush=True)
                        try:
                            current_runtime_state=env.scene.get_state(is_relative=True)
                            print(f'VALIDATE action-index={action_index} get_state END elapsed_s={time.perf_counter()-t:.6f}',flush=True)
                            phase='compare_states';t=time.perf_counter()
                            print(f'VALIDATE action-index={action_index} compare_states BEGIN',flush=True)
                            frame_metrics={}
                            states_matched,comparison_log=compare_states(state_from_dataset,current_runtime_state,0,
                                progress=lambda msg:print(f'VALIDATE action-index={action_index} {msg}',flush=True),
                                dataset_has_single_env_axis=True,metrics=frame_metrics)
                            if contact_audit:contact_audit.validation(action_index,frame_metrics)
                            for path,metric in frame_metrics.items():
                                key=f'{validation_episode_name}/{path}'
                                total=field_summary.setdefault(key,dict(max_abs=None,first_mismatch_frame=None))
                                if metric['max_abs'] is not None:
                                    total['max_abs']=max(total['max_abs'] or 0.,metric['max_abs'])
                                if not metric['matched'] and total['first_mismatch_frame'] is None:
                                    total['first_mismatch_frame']=action_index
                            print(f'VALIDATE action-index={action_index} compare_states END elapsed_s={time.perf_counter()-t:.6f}',flush=True)
                        except BaseException as error:
                            print(f'VALIDATE action-index={action_index} {phase} ERROR elapsed_s={time.perf_counter()-t:.6f} {type(error).__name__}: {error}',flush=True)
                            raise
                        validated_steps+=1;mismatched_steps+=int(not states_matched)
                        print(f'VALIDATE action-index={action_index} {"matched" if states_matched else "mismatched"} checked={validated_steps}',flush=True)
                        if comparison_log:print(comparison_log,flush=True)
                break
        # Close environment after replay in complete
        plural_trailing_s = "s" if replayed_episode_count > 1 else ""
        print(f"Finished replaying {replayed_episode_count} episode{plural_trailing_s}.")
        if state_validation_enabled:
            if not validated_steps or mismatched_steps or validated_steps != expected_steps:
                raise RuntimeError('Diagnostic action replay state validation failed; inspect mismatches above')
    finally:
        if state_validation_enabled:
            record_outcome('validated' if validated_steps>0 and validated_steps==expected_steps and mismatched_steps==0 else 'failed',
                           checked=validated_steps,mismatched=mismatched_steps,expected=expected_steps,fields=field_summary)
            print('REPLAY_FIELD_ERRORS '+json.dumps(field_summary,sort_keys=True),flush=True)
            print(f'REPLAY_VALIDATION checked={validated_steps} mismatched={mismatched_steps} expected={expected_steps} elapsed_s={time.perf_counter()-validation_started:.3f}',flush=True)
        try:
            try:
                if contact_audit:contact_audit.close(validated_steps,mismatched_steps,expected_steps)
            finally:
                try:
                    if timeline:timeline.close()
                finally:
                    if env is not None:env.close()
        finally:
            dataset_file_handler.close()


if __name__ == "__main__":
    # run the main function
    completed=False
    try:
        main()
        completed=True
        record_outcome('completed')
    except BaseException as error:
        record_outcome('failed',error=f'{type(error).__name__}: {error}')
        print(f'REPLAY_EXIT status={"interrupted" if isinstance(error,KeyboardInterrupt) else "failed"} error={type(error).__name__}: {error}',flush=True)
        raise
    finally:
        close_started=time.perf_counter()
        print('APP_CLOSE BEGIN',flush=True)
        simulation_app.close()
        print(f'APP_CLOSE END elapsed_s={time.perf_counter()-close_started:.3f}',flush=True)
    if completed:print('REPLAY_EXIT status=completed code=0',flush=True)
