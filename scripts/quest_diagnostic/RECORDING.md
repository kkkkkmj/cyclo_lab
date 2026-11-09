# Quest demonstration and MP4 recording

This workflow selects **scenario_delivery_base / operator_B_1 / group_index 1**:
`toast_base_20261109_025`. It preserves the selected layout and records each accepted X-started
teleoperation episode as Isaac Lab HDF5 data plus a simulation-camera MP4. The diagnostic JSONL
trace is separate from the demonstration data. Results are observed task verdicts, not a guarantee
of training readiness or action-replay fidelity.

## Setup

Follow [installation](../../CHANGES.md) first. The recording
process needs h5py, NumPy, Pillow and `imageio-ffmpeg==0.6.0`; the last is declared in the Cyclo Lab
package dependencies and provides the FFmpeg binary. Rebuild the separate image after updating:

```bash
export REPO=/path/to/cyclo_lab_toast_quest
cd "$REPO"
docker compose --project-name cyclo_lab_mj --env-file docker/.env.base \
  -f docker/docker-compose.yaml -f docker/compose.mj.yaml --profile base build cyclo_lab
```

The commands below create a separate transient container with this checkout mounted at
`/workspace/cyclo_lab`. They do not enter or stop an existing container. Ensure resources and the
chosen bridge are available; do not launch another producer on an occupied bridge. This is a headless
simulation command, so DISPLAY is not needed. Do not restart an active server or simulation merely
to follow this example.

## Quest server — terminal 1

Replace the clone path and `YOUR_PC_LAN_IP`; use an unused HTTPS port reachable from Quest.
If an appropriate server already runs, use its bridge path consistently in both terminals.

```bash
export REPO=/path/to/cyclo_lab_toast_quest
export QUEST_HOST=YOUR_PC_LAN_IP
export QUEST_PORT=8766
cd "$REPO"
python3 scripts/quest_diagnostic/server.py \
  --host "$QUEST_HOST" --port "$QUEST_PORT" \
  --bridge-dir "$REPO/logs/quest_toast_base"
```

Open `https://<QUEST_HOST>:<QUEST_PORT>/` in Quest Browser, confirm the certificate and pair with the
terminal PIN. Certificates/private keys default to `~/.local/state/cyclo-quest-tls`; optional
`--cert /path/to/certificate --key /path/to/private_key` selects your own. Keep keys out of Git.
Reload the current page before entering VR when client/server builds differ.

## Record B_1, first scenario — terminal 2

Use your actual clone path. The parent directory is unique; `recording/` and `diagnostic.jsonl` must
not already exist. Do not create `recording/` yourself. MP4 recording starts automatically with HDF5;
there is no separate video-enable flag.

```bash
export REPO=/path/to/cyclo_lab_toast_quest
cd "$REPO"
mkdir -p "$REPO/recordings"
RUN_DIR=$(mktemp -d "$REPO/recordings/quest_base_B1_001.XXXXXX")
CONTAINER_RUN="/workspace/cyclo_lab/recordings/$(basename "$RUN_DIR")"
printf 'Output directory: %s\n' "$RUN_DIR"
set -o pipefail
bash scripts/run_mj.sh scripts/quest_diagnostic/teleop_toast.py \
  --headless --keep-open --enable-grippers --control-profile practice \
  --scenario_manifest scenario_delivery_base/manifest.json \
  --scenario_group operator_B_1 --group_index 1 \
  --bridge-dir /workspace/cyclo_lab/logs/quest_toast_base \
  --position-scale 1 --rotation-scale 1 \
  --record-dir "$CONTAINER_RUN/recording" --record-seconds 0 \
  --diagnostic-log "$CONTAINER_RUN/diagnostic.jsonl" \
  2>&1 | tee "$RUN_DIR/run.log"
RUN_EXIT=${PIPESTATUS[0]}
printf '%s\n' "$RUN_EXIT" > "$RUN_DIR/exit_code"
```

1. Confirm `SCENARIO_SELECTED` identifies `toast_base_20261109_025`, then inspect fresh camera previews.
2. Release both squeeze buttons. Press **X** to request reset/start; recording begins only when the
   start is accepted. `RECORD_STARTED` and **REC** identify the active recording. Waiting renders add
   neither HDF5 action rows nor MP4 frames.
3. Squeeze controls the corresponding arm target and trigger controls its gripper. The practice profile
   and 1:1 target scales do not imply instantaneous tracking or a measured robot velocity.
4. **A** ends the episode manually. Success, task failure, timeout or tracking stall also ends it.
   HDF5/MP4 finalize, then the environment waits. The result stays beside NO REC until the next
   accepted X resets/starts another episode. `--record-seconds 0` disables the optional wall-time
   recording cap; it does not disable the task's existing simulation timeout.
5. Ctrl+C or the console `q` command finalizes an active recording and exits. A forced kill or power
   loss cannot guarantee recovery of buffered data. Never delete or overwrite an existing run to restart.

[Episode results](EPISODE_RESULTS.md) documents the exact serving predicate and outcome priority:
explicit stop/stall is non-success; failure beats simultaneous success; success beats a simultaneous
time limit when no failure is present. The result display also works without `--record-dir`.

## Outputs and interpretation

| Path under RUN_DIR | Contents |
|---|---|
| `recording/dataset.hdf5` | Standard `data/demo_*/{actions,obs,states,initial_state,processed_actions,timing}` |
| `recording/manifest.json`, `metadata.json` | Selected manifest snapshot, assignment, code/source hashes and finalization metadata |
| `recording/episode_000001/video.mp4` | HEAD / LEFT WRIST / RIGHT WRIST simulation RGB atlas, 768×256; one directory per episode |
| `recording/episode_000001/episode.json` | Result, reason, raw termination terms, HDF5 group and video summary |
| `recording/episode_000001/frames.jsonl`, `video.json` | Frame-to-sample mapping, timing, dropped frames and encoder errors |
| `recording/record_audit/` | Diagnostic reset/timing evidence, not additional training demonstrations |
| `diagnostic.jsonl`, `run.log` | Control/input trace and terminal output, separate from HDF5/MP4 |

HDF5 `success`, `task_success_observed` and `episode.json` use the same pre-reset outcome policy.
`diagnostic=true` and `training_ready=false` remain: task success does not certify demonstration quality.
The MP4 uses recorded pre-action RGB, not desktop capture. It plays at 1/control_dt in simulation time;
wall-clock intervals, bounded-queue drops and encoder errors are reported separately. No frames means
no MP4 or HDF5 demo, but the episode sidecar is retained. Keep each complete run directory together.

Recording provenance uses `git -c safe.directory=<resolved checkout> ...` for each read-only query.
This permits the container's `/workspace/cyclo_lab` bind mount without changing global Git trust or
using `safe.directory=*`. The current commit, dirty status, tracked diff hash and recorder source hashes
are stored; private diff contents are not copied into metadata.

## Inspect the saved run

After the simulator exits, in the same terminal (or restore `CONTAINER_RUN` to its printed run path):

```bash
bash scripts/run_mj.sh scripts/tools/toast_recording_metadata.py \
  "$CONTAINER_RUN/recording/dataset.hdf5"
```

The inspector checks action/state/image time axes, selected scenario provenance, success-label agreement
and video frame-to-sample timing. It requires at least one nonempty episode. CPU integration tests use
the pinned HDF5 writer and real MP4 encoding/decoding with synthetic frames. Serving, lifecycle and
HUD tests cover pre-reset capture, simultaneous terminations, WAITING persistence and accepted starts.
**Actual PhysX/Quest recording, headset readability and casting crop remain unverified.**
