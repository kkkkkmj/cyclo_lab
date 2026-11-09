# One short Quest diagnostic recording

This workflow selects **operator_B, list position 1**, currently `batch02_toast_001`.
It records a short diagnostic, **not a successful toast demonstration**. The fixed
100 layouts, task success predicates, physics, and expert remain unchanged.

## Evidence and limits

The existing `logs/quest_teleop` snapshot contains three 244×244 uint8 RGB camera
summaries, successful HTTP responses, client decode/draw acknowledgements and
`preview_ok=true`. It is an old snapshot, not proof of a currently live connection
or a human-confirmed headset image. No diagnostic HDF5 or replay from this new
workflow has been verified yet. CPU tests do not establish that VR movement works.

## Before starting

Use the existing input server and current Quest page. Do not start a second server
or stop another simulation. If `.simulation.lock` is owned, this tool refuses to
start. The host and container must share `logs/quest_teleop`; the server must have
been started with that bridge directory. No browser/server changes are required
by this recording integration. If the disk/server/client builds differ, exit VR
and reload the current page; arrange a server restart with its operator only if
needed. Do not bypass `preview_ok` when the image is missing.

From the repository root, inspect the existing bridge without changing it:

```bash
python3 -B scripts/quest_diagnostic/inspect_preview.py --bridge-dir logs/quest_teleop
nvidia-smi
```

Check free GPU memory and existing work before launching. The following commands
assume the existing container `cyclo_lab` mounts this checkout at
`/workspace/cyclo_lab`; adjust paths only if its configuration differs.

## Launch and record

Terminal 1, from the repository root:

```bash
run_dir=$(mktemp -d "$PWD/logs/quest_B_first.XXXXXX")
printf 'Result directory: %s\n' "$run_dir"
container_run="/workspace/cyclo_lab/logs/$(basename "$run_dir")"
set -o pipefail
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 \
  --record-dir "$container_run/recording" --record-seconds 8 \
  --headless --duration 180 2>&1 | tee "$run_dir/run.log"
run_exit=${PIPESTATUS[0]}
printf '%s\n' "$run_exit" > "$run_dir/exit_code"
```

Start/stop request files are created through `docker exec` so container-owned
directories do not depend on host write permissions. The `recording` subdirectory must **not exist**. The program creates it exclusively,
using the existing Isaac Lab `ActionStateRecorderManagerCfg` and HDF5 writer.
An adjacent byte-identical `manifest.json` snapshot enables portable replay.

1. Wait for `SCENARIO_SELECTED ... batch02_toast_001`, `STATIC_RACK_POSE_OK`, and
   `RECORD_WAITING`. Put on Quest and confirm the actual three-camera preview.
2. Look forward and release **both squeeze/grip buttons** until both hands are
   `ready`. Recording requires fresh input and a valid preview.
3. In Terminal 2, set `run_dir` to the result directory printed above, then request
   recording:

   ```bash
   # Replace with the actual directory printed by Terminal 1.
   run_dir="$PWD/logs/quest_B_first.XXXXXX"
   container_run="/workspace/cyclo_lab/logs/$(basename "$run_dir")"
   docker exec cyclo_lab touch "$container_run/recording/start_recording"
   ```

4. Wait for `RECORD_STARTED` (the preview label changes to RECORDING). Squeeze one
   controller, move it about 2 cm, and release it. Repeat with the other hand.
   Do not touch objects during this first diagnostic.
5. After 8 **wall-clock seconds** of recording, the program saves and exits.
   To finish earlier, `docker exec cyclo_lab touch "$container_run/recording/stop_recording"`. Ctrl+C also
   runs the export/close path after recording has begun. Forced process kill or
   power loss is not guaranteed to preserve an in-memory episode.
6. Confirm `RECORD_FINALIZED` reports `SAVED` with nonzero frames. A launch that
   never receives a valid start request does not claim a completed recording.

Grippers stay open; lift stays at its reset height. Position/rotation gains are
0.25/0.5, with 5 cm/15° bounds around the initial wrists. Per-step corrections
retain the existing 0.05 m/s and 0.5 rad/s limits. Releasing squeeze or losing
input/preview stops **target updates**; position servos still converge to the
last target. This is not torque-off or a snap to the current measured pose.
After a loss, release the buttons and reacquire a valid reference before moving.
Reset/replay does not advance to another scenario.

## Inspect the actual saved file

Once Terminal 1 exits, run from the same shell (or restore `run_dir` and
`container_run` to the printed directory):

```bash
docker exec -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/tools/toast_recording_metadata.py \
  "$container_run/recording/dataset.hdf5" \
  > "$run_dir/hdf5_inspection.json"
```

The inspector checks frame counts, `(T,15)` actions, observation/state time axes,
three `(T,244,244,3)` uint8 RGB streams, initial state, toast-cycle state, and
scenario provenance. Nonzero actions alone do not prove a human moved the robot;
compare measured motion and your headset observation as well.

The dataset keeps standard `data/demo_*/{actions,obs,states,initial_state,
processed_actions}`. Recording begins from the current settled state; it does
not teleport the scene back to its spawn pose. Each episode is marked
`diagnostic=true, success=false`, with any task success observed stored separately.
The file stores operator, scenario ID, manifest SHA-256, static rack pose and
control timing. `metadata.json` records the finalization result. Keep the entire
`recording` directory together, including the manifest snapshot.

## Replay the same layout

Normal **action replay** uses the original replay tool with the saved scenario
applied before environment creation:

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_demos.py \
  --dataset_file "$container_run/recording/dataset.hdf5" \
  --num_envs 1 --enable_cameras --validate_states \
  2>&1 | tee "$run_dir/replay.log"
```

Expect `SCENARIO_REPLAY batch02_toast_001` and `STATIC_RACK_POSE_OK`.
The replay rejects missing/tampered scenario provenance and timing mismatches
rather than silently selecting the original layout. It restores initial dynamic
states and executes recorded actions. State comparisons are diagnostic messages;
an exit code alone does not establish matching trajectories. B pauses and N resumes.
This mode requires GUI access; append `--headless` for a non-GUI action check.

Optional **saved-state display** (no physics action rollout) uses the existing
video exporter and the same scenario configuration:

```bash
docker exec -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_demos.py \
  --dataset_file "$container_run/recording/dataset.hdf5" \
  --num_envs 1 --headless --enable_cameras \
  --video_file "$container_run/recording_review.mp4"
```

This displays recorded states and original RGB. It does not demonstrate that
physics reproduces the original movement. Choose a new video filename on repeat.
Neither replay mode establishes full toast-task success.
