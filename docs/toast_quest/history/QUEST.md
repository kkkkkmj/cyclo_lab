> **Historical development record**: Preserves the original descriptions, values, and execution results; this is not the current run guide. See [Changes](../../../CHANGES.md) for current settings and commands. In particular, gains of 2/0.5 were an intermediate comparison configuration, not the original v2 defaults. Claims about stable rack support and runtime validation must be read alongside the latest diagnostics. Host paths/logs below identify local evidence from that time.

> Current entry point: [Changes](../../../CHANGES.md). Historical values in the development and measurement records below describe their respective configurations. The current v2 rising target/upper limit is +35 mm and the lower limit is -45 mm. Adapt recorded PC IPs, absolute host paths, and container names to your environment. Use the variable-based commands in the current guide.

Current v2 left/right master joint1 velocity limits default to 6.5 rad/s; no separate velocity option is needed.
See the [configuration/validation report](GRIPPER_SPEED.md). Values of 2.2 in historical comparisons below apply to those runs.

Current v2 gripper settings: left/right master joint1 and slave joint2/3/4 all use stiffness=100.0,
damping=4.0. The old `--gripper-slave-gains-official` option (2/0.5 comparison) is now rejected.
See [README_GRIPPER_GAINS.md](GRIPPER_GAINS.md) for current execution/readback validation results.
The experiments below describe their historical results, not current defaults.

# Quest Touch Plus → Toast v2: bounded two-arm test

## Meta Web Casting Defaults and Persistence — casting-fit-3

**Actual casting-center alignment is unverified.** Default scale .50 was user-specified; horizontal center +.24 is
an estimate based on a measured matrix. The entire panel—status, four cameras, border, and crosshairs—moves together.

The latest pre-change `packet.xr_display` showed client build `preview-v3-643d85fe9ef3`, revision `casting-fit-2`,
scale .60, center (+.12,+.10), and framebuffer 3360×1760.
Left-eye viewport was (0,0,1680,1760), right-eye (1680,0,1680,1760); applied centers matched requests without clamping.
Left-eye projectionMatrix[8] = −0.2425125688. Projecting the eye-forward vector (0,0,−1,1)
gives NDC x = −P[8] = +0.2425125688, rounded to +.24.
From the current +.12, displacement is (.24−.12)×1680/2 = **100.8 eye-viewport pixels rightward**.
At the new .50 scale, the panel is 840×840 pixels, eye-local center (1041.6,968), with NDC bounds
[−.26,−.3772727,+.74,+.5772727], so it is not clipped (pixel y uses a bottom origin).
This estimate assumes Meta centers casting on the left-eye forward point; the actual crop transform is unknown.
The available attached capture alone cannot establish exact pixel correspondence between the current pink crosshair and video boundaries.

Per-eye viewport and framebuffer dimensions are not conflated; crosshairs are not moved independently.
Control, scenarios, source cameras, recording, replay, and input-protection code were unchanged.

### New Defaults and Persistence

| Setting | Casting fit (initial default mode) | Quest default mode |
|---|---|---|
| Scale | .50 | .65 |
| Horizontal center | +.24 (12% of eye-viewport width rightward) | 0 |
| Vertical center | +.10 (5% of height upward) | 0 |
| Inner video margin | .02 | .02 |
| Corner diagnostics | ON | OFF |

The entire panel (status + four cameras) moves right/up together; scale changed from .60 to the user-specified .50.
Video aspect ratio, original cameras, and UVs are unchanged; video is not cropped to fill the panel.
Browser localStorage `cyclo.quest.display.v2` (schema 2) stores mode and per-mode scale/center/margin/diagnostic settings.
If the v2 key is absent, new defaults are saved once immediately on page load. The old v1 key is retained but not read.
Subsequent loads restore user edits in v2 rather than overwriting defaults each time. Settings also save on changes or VR entry and restore on the same origin after reloads, VR re-entry, or normal browser restarts.
Changing IP/port, clearing site data, or closing a private window may change persistence scope.
Storage denial/quota errors are displayed; the current VR display remains usable.
`Restore defaults for this mode` restores and saves the defaults above. Switching modes retains the other mode's saved values.

### Minimal Application Procedure — Check Defaults Once

1. If possible, finish recording with A and proceed in WAITING. Do not restart the simulator or batch jobs.
2. The user stops **only the input-server terminal** with Ctrl+C and restarts it, because the server fixes its build at startup.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/server.py \
  --host 192.168.10.116 --port 8765 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab/logs/quest_teleop
```

3. Exit VR on Quest and reload `https://192.168.10.116:8765/`.
   Pair with the new PIN, then verify CLIENT BUILD matches the server's SERVER BUILD.
4. `casting-fit-3`, Casting fit / .50 / +.24 / +.10 appear automatically.
   **Do not adjust sliders; press Enter VR once.** If v2 settings are already saved,
   use `Restore defaults for this mode` once in Casting fit to establish the same baseline.
5. In Meta casting, check once that TL/TR/BL/BR, status text, and all three bottom images are visible.
   Settings then persist across reloads/VR re-entry. Do not report resolution before this check.

Applied XR diagnostics now update approximately every 1 second and are included in the existing input packet's `xr_display`.
Inspect revision/build in `packet.xr_display` within `logs/quest_teleop/input.json` and `server_status.json`,
along with requested settings, framebuffer, per-eye viewport/applied scale/center/bounds/projectionMatrix,
and `reported_client_ms`. Use input receipt time as well to assess diagnostic freshness.
These describe the last successful draw and may persist after VR exits. They do not automatically assess casting results.
This field is observational and is not used for control coordinates, buttons, or video-validity decisions.

CPU/mock checks passed: HUD geometry/render 16 + persistence 8 + version migration/measured viewport 6. Previously, 57 Python tests passed.
Actual Quest optics, Meta casting centering, and readability remain unverified.

## Current Status

- User runtime confirmation: both hands `meta-quest-touch-plus`, `valid:true`, position/rotation received, buttons `pressed:true`, both indicators green.
- **Thumbsticks remain unverified on the headset and are not used for robot actions.**
- This change implements strict input-source selection, separate invalidity/communication reasons, local IPC, bounded bimanual control, optional grippers,
  and an in-headset camera panel. Modified HUD, robot motion, and grippers remain unverified on GPU/Quest.
- 57 CPU tests PASS (Quest 43, metadata 6, scenario loader 8), 10 source-selection JS tests and 8 mocked preview-client tests PASS, JS syntax checks PASS.
- NVIDIA/NVML and Docker socket access were unavailable in this session. GPU idle status was not established.
  No simulator was started; running diagnostic-server/scenario jobs were not stopped.
- Existing recorder integration and first-B-scenario test recording/replay paths were implemented. Actual recording/replay remain unverified; 0 demonstrations collected in this work. No robot-hardware/Zenoh connection.

## Operator B First Scenario: Current Procedure

Use steps 1–4 below as the current procedure. Marker-file input remains only for compatibility; use X/A or n/s. Implementation is ready, but
**actual GPU recording/replay and Quest display/casting improvements remain unverified**. No actual demonstrations were saved in this work.
`operator_B`, `scenario_index=1` is resolved using the order in `scenario_delivery/assignments.csv`,
with a separate check for `batch02_toast_001`. It does not select item 51 of the full list.

### 1. Apply the Input Server

Running servers and simulators were not automatically stopped. After the user exits the current teleop terminal with Ctrl+C,
stop **only the diagnostic-server terminal** with Ctrl+C and restart with the following command.
Do not stop scenario batch jobs. Check existing GPU usage with `nvidia-smi` before a new GPU run.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/server.py \
  --host 192.168.10.116 --port 8765 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab/logs/quest_teleop
```

Wear Quest and reopen **https://192.168.10.116:8765/** in Browser.
Pair with the terminal's new 6-digit PIN. Verify `CLIENT BUILD` matches terminal `SERVER BUILD`
and `Secure context / WebXR / immersive-vr` are all true, then press **Enter VR diagnostic**.
Restarting the server invalidates cookies. On the same server, subsequent episodes, ordinary reloads, and VR re-entry do not
require another PIN while the 8-hour cookie is valid. Browser restart behavior depends on cookie retention.

### 2. Inspect Four Cameras Without Moving

Run once after the previous teleop has exited, without overlapping other GPU jobs.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --preview-only --keep-open
```

Startup logs should show `SCENARIO_SELECTED ... id=batch02_toast_001 seed=1`, manifest SHA256,
7 measured poses under `RESET_POSES_OK`, and `READY / WAITING`.
**Images update in WAITING without pressing X/n.** WAITING renders only; physics time does not advance.
Check FRONT OVERVIEW above and HEAD / LEFT WRIST / RIGHT WRIST below.
The VR panel preserves aspect ratio. If clipped, exit VR, lower the webpage's `Scale`, and re-enter.
`Inner margin` is padding inside the panel. Quest default mode uses scale=.65, margin=.02; Casting fit uses the persistent defaults above.
Actual PC-casting crop improvements require separate verification. This page does not provide a PC input mode.
After inspecting cameras, exit this teleop terminal with Ctrl+C. Keep the input server running.

### 3. Brief Teleoperation and Recording in the Same Scenario

The directory below must be a **new path**. If it exists, use another name such as `B001_test_002`.
Keep this test only under `datasets/quest_tests/`, separate from formal successful demonstrations.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open \
  --record-dir /workspace/cyclo_lab/datasets/quest_tests/B001_test_001 \
  --record-seconds 8
```

1. Wear Quest and look forward. Release both squeeze buttons (side grip buttons).
   Valid input from both hands and fresh video are required to start.
2. **Press and release left X once**, or enter `n`+Enter in the PC teleop terminal.
   After resetting the same scenario/seed, `EPISODE_STARTED` is printed. Recording begins then.
3. Establish a new reference with squeeze released, then **press only left squeeze again** and move the controller
   slowly forward about 2–4 cm, then release. Target displacement is 0.25× that motion. Use one arm for the first test.
4. **Press right A once or `s`+Enter** to finish the short recording. Otherwise it finishes
   approximately 8 wall seconds after starting. GPU delays shorten the recorded simulation duration.
   Check `RECORD_SAVED demo_0 ... success=False` and `EPISODE_WAITING`.
5. For another test, release both squeezes and explicitly start with X/n. demo_1, etc. are appended to the file.
   `--keep-open` keeps the application alive; it does not extend the original **240 simulation seconds timeout**.
6. Exit finally with Ctrl+C (or `q`+Enter). The active recording is finalized and HDF5 closed,
   followed by `RECORD_FINALIZED` and producer `stopped` status. If interrupted mid-step,
   only complete rows containing obs/actions/states are saved. Without any complete rows, no empty episode is saved.

X=reset/start and A=save/wait are edge-triggered. Holding a button does not start the next episode.
B/Y retain forward-reference reset; squeeze is the clutch. Position .25/rotation .5, initial-reference 5 cm/15° bounds,
fixed-open grippers, and fixed lift are retained. This is not the trigger/thumbstick object-grasping stage.
Holding targets on input/video loss and requiring squeeze release/re-engagement after recovery are also retained.
Failed/incomplete recordings are saved in the test file with `success=False`, `diagnostic=True`.
The original success result is recorded separately as `task_success_observed`. Exclude discarded tests from formal collection;
leave files intact or archive separately after shutdown. This launcher has no button to delete saved episodes.

### 4. After Shutdown: CPU File Checks → Action Replay → Reference Video

Inspect after the simulator exits and HDF5 closes. The input server may remain running.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/tools/toast_recording_metadata.py \
  /workspace/cyclo_lab/datasets/quest_tests/B001_test_001/dataset.hdf5
```

This command does not start the simulator. It checks actions [N,15], three RGB streams [N,244,244,3],
initial/subsequent states, toast_cycle, frame alignment, and manifest hash.

Next is **replay that recomputes actual physics from actions**. Do not run it concurrently with the teleop above.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_demos.py \
  --dataset_file /workspace/cyclo_lab/datasets/quest_tests/B001_test_001/dataset.hdf5 \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episodes 0 --headless --enable_cameras --validate_states
```

`SCENARIO_REPLAY batch02_toast_001`, `STATIC_RACK_POSE_OK`, `REPLAY_INITIAL_STATE_OK`,
Check the final `REPLAY_VALIDATION checked=... mismatched=0`.
Initial robot/object states and toast cycle are checked; the static rack is checked separately by world pose.
Subsequent-state comparisons use the existing replay absolute-error threshold .01. A mismatch terminates diagnostic replay with an error.
Replay's existing termination-disabling behavior is retained and does not change the original task definition.

Then produce an **MP4 rendering saved states** as a reference video. This is distinct from action-based physics replay validation.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_demos.py \
  --dataset_file /workspace/cyclo_lab/datasets/quest_tests/B001_test_001/dataset.hdf5 \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episodes 0 \
  --video_file /workspace/cyclo_lab/datasets/quest_tests/B001_test_001/replay.mp4
```

PC file location: `datasets/quest_tests/B001_test_001/replay.mp4`.
FRONT OVERVIEW renders saved scene states from a new camera; the three bottom images are the originally recorded RGB.
Live/replay use the same `toast_overview.py` camera (eye 3.1,0,2 / target .35,0,1).
The new overview is not added to training-policy observations or HDF5 RGB.

### Metadata and Validation Scope

The recording directory contains a byte-for-byte snapshot of the original manifest, metadata.json, and the existing Isaac Lab recorder's
`dataset.hdf5`. HDF5 and the sidecar store operator/index/ID/seed/hash/measured reset poses/
physics dt/decimation/control dt; episodes include termination reasons and verdicts.
Timing includes wall-monotonic, simulation elapsed time, and start/end Unix time.
Existing policy robot observations, three camera RGB streams, actions, processed_actions, initial/subsequent scene states,
and toast_cycle are reused. Raw Quest poses/buttons and the new overview RGB are not stored as training data.

Replay checks the adjacent manifest snapshot's hash and applies scenario/manifest/seed **before gym.make**.
Missing/tampered data or task/timing/static-rack metadata mismatches cause errors. The current project manifest is not
silently substituted. Actual reset/initial-state restoration agreement is additionally asserted during GPU execution.

CPU: 57 Python tests (Quest 43 + metadata 6 + existing scenario loader 8), 10 JS input tests,
8 mocked preview tests, Python/JS syntax checks, and synthetic-image aspect-ratio checks passed.
Mock recorder tests do not establish actual HDF5 writes. Without GPU access, actual HDF5 creation, static-rack
world pose, physics replay agreement, four Quest images, and casting remain unverified.


## Environment and Actual Action Contract

`docker/.env.base` specifies Isaac Sim 5.1.0, `/isaac-sim`, and `/workspace/cyclo_lab`.
The checkout's `third_party/IsaacLab/VERSION` is 2.3.0; existing scenario logs also record Sim 5.1.
The running container's patch version/driver could not be queried directly. No upgrade was performed.
No applicable AGENTS.md was found in the project or scripts paths.

Target: `Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2`, FFW-BG2,
`MakeToastFFWBG2BimanualEnv` + `MakeToastFFWBG2BimanualServeEnvCfg`.

| Action indices | Actual meaning |
|---|---|
| 0:6 | Left wrist arm_l_link7, base-frame position delta 3 + axis-angle rotation delta 3 |
| 6:12 | Right wrist arm_r_link7, same format |
| 12,13 | Left/right CoupledGripperPositionAction: +1 open, -1 close, continuous interpolation between |
| 14 | lift target = .25 × action − .25, joint range [-.5,0] |

Existing `StandbyPostureIKAction`/DLS/relative pose/scale=.3 is used unchanged.
Null-space standby correction and joint-limit avoidance in `arm_action.py` remain unchanged.
Gripper joint targets are open=0, closed=1.10, not simple Boolean actions.
The test launcher asserts action names/dimensions/IK settings and checks the existing
`action_to_target_eef_pose` ↔ `target_eef_pose_to_action` round trip with a nonzero sample.
This sample action is not applied to the robot.

## Input Selection and Status Display

`input.js` applies these rules:

1. Reject sources with `source.hand` or a profile name containing `hand`, including `meta-fixed-hand`.
2. **Require `meta-quest-touch-plus` in profiles**. Sources with only other controller fallbacks are currently rejected too.
3. Check tracked-pointer, xr-standard gamepad, an actual grip pose, !emulatedPosition, and a visible session.
4. Evaluate each same-handedness candidate as a fresh object. Prefer valid Touch Plus; break ties by stable source ID.
5. If none is valid, display only the selected invalid candidate's reason without mixing in previous poses/buttons.
   Candidate summaries `candidates` and selected `source_id` are available in logs.

The Python receiver and control adapter recheck profiles. Even if an old page sends a hand profile as valid=true,
the server changes it to valid=false and clears poses/buttons.

HUD left/right panels: green=valid input, bright green=button pressed, yellow=invalid input with reason.
COMM is separate: ACK OK / delayed response / HTTP error. A green input panel alone does not imply healthy communication or active robot control.
Hand exclusion, profile rejection, missing grip pose, emulated position, visibility, and other reasons are displayed as strings.

Server `communication=receiving` indicates recent packet arrival.
`live=true` means a packet within 250 ms plus visibility=visible, independently of both hands being valid.
Input/preview valid→invalid transitions and receipt gaps increment `safety_epoch`, requiring button release after recovery
 even if the simulator skips a brief loss frame. Actual input-source replacement also reanchors control.

## Control Method and Limits

- CPU-adapter poses are **wrist positions and xyzw quaternions relative to the robot root/base**.
  Isaac wxyz is converted at input/output boundaries. No new fingertip TCP offset is added.
- WebXR uses local-floor coordinates in metres: +X right, +Y up, -Z forward.
- Initial/reanchoring projects headset forward onto the floor plane to obtain user forward/right.
  User forward→robot +X, user left→robot +Y, up→robot +Z.
  With the headset facing the default direction: `(xr_x,xr_y,xr_z) → (-xr_z,-xr_x,xr_y)`.
- Release both squeezes and look in the direction to use as robot forward to establish the initial reference.
  Subsequent head rotation does not continuously rotate the control frame.
- A new squeeze press anchors that controller pose and the held robot target.
  There is no motion at anchoring. Subsequent anchor-relative translation is scaled by **0.25**, rotation by **0.5**.
  Rotation uses the shortest axis-angle of `q_current × inverse(q_anchor)`, transformed into the same basis and left-multiplied onto the robot anchor.
- Target bounds: radius **5 cm** from the initially settled wrist and **15°** from its initial orientation. Repeated clutch/rebase does not expand these bounds cumulatively.
- Each step computes IK action from the measured-pose error to the held target, divided by `.3`.
  Error correction is limited per step to the equivalent of **0.05 m/s**, **0.5 rad/s**.
  At 25 Hz, this is at most 2 mm / .02 rad per step. It is not a physical velocity limit guaranteeing actual wrist velocity.
- Button release/tracking loss/250 ms receipt gaps/video older than 1 second/simulation-loop delays **hold the last target**.
  Repeated zero actions do not let the target drift with the measured pose.
  Existing IK servo convergence toward the held target or null-space posture correction may still produce motion.
- Recovery/new session/new source/reference reset/server replacement requires squeeze release and re-engagement for a new anchor.
  A single-sample jump >20 cm or rotation >60° also interrupts control and requires release.
- The launcher exits if target-to-measured wrist position error exceeds 8 cm.
- Lift is fixed using the action corresponding to its initial joint position. No thumbstick/base motion.
- Original termination/timeout remain. On occurrence, recording finalizes, the environment performs its original reset, then enters WAITING.
  WAITING renders only. With `--keep-open`, the app remains open until X/n starts another episode.

| Button | Function |
|---|---|
| Each hand's middle-finger squeeze, buttons[1] | That hand's clutch. Value >=.8 activates; <.2 fully releases/rearms |
| Each hand's index trigger, buttons[0] | Only with `--enable-grippers`: while squeezing, open/close via +1−2×trigger value |
| Right B / left Y, buttons[5] | Reset forward reference with both squeezes released; not a robot/environment reset |
| Left X, buttons[4] / terminal n+Enter | Reset the same scenario and start from WAITING. Ignored while RUNNING |
| Right A, buttons[4] / terminal s+Enter | Finalize recording from RUNNING and enter WAITING. Without recording options, wait without saving |
| thumbstick | No robot command. Unverified on the headset |

Button indices follow the [official WebXR input profile](https://github.com/immersive-web/webxr-input-profiles/blob/main/packages/registry/profiles/meta/meta-quest-touch-plus.json).
The user's A/X/trigger inputs were confirmed, but **verify squeeze and B/Y mappings in logs before a new test**.
For the first run, omit `--enable-grippers` to keep grippers open.

## Connection Architecture and Cameras

```text
Quest HTTPS → authenticated Python input server → local input.json → Isaac Sim test → existing 15D IK
                         ↑                     ↓
                   /preview.jpg ← composite JPEG of FRONT OVERVIEW + head/left wrist/right wrist
```

A server without `--bridge-dir` does not write robot IPC.
The IPC directory is user-only; input.json uses 0600 atomic replacement and Linux monotonic receipt timestamps.
Default host-network Docker shares the host monotonic clock. Separate time namespaces are unsupported.
Separate flock locks prevent duplicate input-server/simulator instances using the same directory.

The approximately 5 Hz composite displays observational FRONT OVERVIEW above the three existing 244×244 cameras.
The three existing cameras and training observations are retained. Overview is not stored as training RGB; replay video rerenders saved states.
This is a head-fixed panel, **not stereoscopic CloudXR streaming**. GPU→CPU JPEG conversion has a cost.
HTTP image age and request duration invalidate display/control when video is older than 1 second.
On server shutdown/video interruption, simulation retains the last wrist/gripper targets.
preview.jpg uses 0644 for sharing between the root Docker writer and host reader; the enclosing directory defaults to 0700.

## Check GPU Jobs Before Running

Use the execution commands and button sequence under **Operator B First Scenario: Current Procedure** above.
The older command using only `--headless --duration 180` does not select the B scenario, recording, or indefinite waiting and is unsuitable for this objective.

```bash
nvidia-smi
docker ps --format '{{.Names}} {{.Image}} {{.Status}}'
docker top cyclo_lab
```

Do not start a duplicate simulator while scenario batches/other Isaac Sim jobs are running.
NVIDIA/Docker access failure in this session does not imply a driver failure on the lab PC.
If server and page builds already match, document cleanup alone does not require a server restart.

## When PIN Re-entry Is Required

Code lifetime differs from authentication-session lifetime. PIN limits: 5 minutes/5 attempts/one use;
authentication cookies and server tokens last **8 hours from pairing**, without extension on activity.
Cookies use Secure, HttpOnly, SameSite=Strict, Max-Age=28800; tokens exist only in server memory.

| Situation | PIN re-entry |
|---|---|
| Next demonstration/simulation on the same connection | Normally unnecessary if the input server and 8-hour authentication remain valid. X/n can start the next recording |
| Quest page reload or VR exit/re-entry | Normally unnecessary with retained cookie/server token. VR reference and clutch must be re-established |
| Browser exit/restart | Unnecessary within 8 hours if a normal window retains the persistent cookie. Required if private-window behavior, cookie deletion, or browser policy removes it |
| PC **input server** restart | **Required**: the new server has no token even if the cookie remains. Independent of certificate reuse |
| Isaac Sim test launcher restart only | Unnecessary if the input server is unchanged. Robot reference/initial pose reset in the new run |

Also required after 8-hour expiry, a new browser profile, PC IP change, cookie deletion, or eviction of an old token under the 8-session limit.
Server-terminal `p` generates only a new PIN; it does not immediately revoke existing sessions.

## Validation and Remaining Work

```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 -m unittest discover -s scripts/quest_diagnostic -p 'test_*.py' -v
python3 -m py_compile scripts/quest_diagnostic/*.py
```

Current Python CPU tests: 57 (Quest 43 + metadata 6 + scenario loader 8), covering authentication/TLS/receiver, hand rejection, bridge timeout/loss epochs,
coordinate/head-yaw/rotation transforms, independent arms, clutch/reconnection/rebase, loop stalls/video loss,
workspace/rotation/action-correction bounds, optional grippers, and fixed lift.
The 10 source-selection tests in `test_input.js` ran in V8.
Eight mocked-API tests covered preview-client HTTP/decode failures, draw confirmation, and expiry.
Actual WebGL texture rendering and Quest display still require verification.
**The user's run confirmed environment initialization/READY and actual camera JPEG generation. New HUD display/video confirmation/bimanual behavior await validation.**

Existing user changes to README_TOAST.md, environment definitions, physics/rewards/success criteria, and scenario definitions were untouched.
Currently integrated files: `scripts/quest_diagnostic/teleop_toast.py`, `episode_control.py`, `diagnostic_recorder.py`,
`index.html`/`hud.js`, `scripts/tools/toast_overview.py`, `toast_recording_metadata.py`,
`replay_demos.py`, `replay_video.py`, and CPU tests.

The existing ActionStateRecorderManagerCfg is connected, recording initial_state, states, actions, processed_actions,
policy obs (including the three existing cameras), toast_cycle, and per-step wall/simulation times.
Raw Quest input is not recorded. Actual GPU recording/replay await validation.

## Historical Diagnostics: Missing Video and preview-v3 Fix (2026-11-02)

The following records evidence and troubleshooting at that time. For current cameras/commands/control, use the B-scenario procedure above.

### Confirmed Evidence and Limitations

- During inspection, `logs/quest_teleop/preview.jpg` was a 732×280 JPEG, 13,661 bytes, mode 0644,
  appearing as uid/gid 65534(nobody/nogroup) in the sandbox. Opening it confirmed toaster/robot imagery.
  Thus at least the final JPEG's RGB generation, encoding, and host read succeeded.
- `args.enable_cameras=True` is set before AppLauncher construction. The checked-out Lab app_launcher.py
  selects `isaaclab.python.headless.rendering.kit` for headless+enable_cameras.
  Headless does not itself disable cameras; the actual JPEG supports this.
- `input.json` had visibility=visible but lacked `preview_ok` and `head_quaternion_xyzw`.
  The immediately preceding page always included these fields in every XR-frame packet, indicating **an older diagnostic page remained active**.
  The user's “only green squares” observation also matched the previous scissor-only rendering.
- Existing make_handler read HTML once at server startup. `Cache-Control: no-store` does not replace JavaScript
  running in an already open tab or HTML retained in the old server's memory.
  Browser cache, an open tab, and an old server page could not be distinguished without access to the served HTML.
- No preview metadata/HTTP counters existed. A single remaining JPEG cannot establish continuous update rate, HTTP 200 at the time,
  image decoding, or successful VR display.
- Docker inspect and direct HTTPS queries failed in this session. Actual container mounts and server-process UID
  remain to be verified. However, live:true in user logs and a host JPEG support successful bidirectional file sharing.
- Returning to the shell may reflect --duration 180 expiry. Without a final exit code/shutdown log,
  the exact exit cause is unknown. A remaining JPEG does not prove the previous finally deletion executed.

### preview_not_live Decision and Strengthened Path

Previously, control.py reported `preview_not_live` when `live=true`, there was no loop gap,
and `packet.get('preview_ok',False)==false`. **A missing field also means false.** Input liveness and video liveness are distinct.
The previous page sent preview_ok based only on HTTP 200→successful createImageBitmap→1-second freshness plus viewer presence,
without checking draw success. Non-200/decode exceptions were also hidden offscreen.

Updated path:

1. Producer: `preview.jpg` + `preview.json` record run_id/frame_id, monotonic capture time,
   SHA-256/size, RGB shape/dtype/min/max/mean/std, step duration/frame interval.
   Metadata is written last as the commit record; readers verify hash/freshness.
2. Server: authenticated `/preview.jpg` returns JPEG with age/frame/run headers.
   Missing bridge configuration/file, permission errors, stale frames, producer shutdown, and publication races
   have distinct HTTP 503 JSON reasons. Requests returning 401 are counted too.
3. Browser: displays/transmits HTTP/decode status/errors, received/decoded/drawn counters, and frame/run IDs.
   Instead of silent catches, it records `fetch_or_decode_error`, `http_error`, and `draw_error`.
4. HUD: uploads new images immediately, checks WebGL context/errors, and sends preview_ok only **after**
   successful view-draw submission. Images older than 1 second still produce false.
5. Server: additionally checks client protocol/build, valid producer run/frame, and `draw_submitted` confirmation.
   Only passing preview_ok reaches local IPC. Old clients leave the robot holding even if input logs arrive.

`draw_submitted` means software submitted a WebGL draw, not proof that the user saw the image.
Therefore **direct Quest display inspection is required**. Video-protection conditions were not relaxed.
On producer exit, JPEG is preserved for diagnostics but invalidated with metadata=stopped.
Even without a stopped record after forced exit, the existing 1-second freshness limit rejects it.

### Application Procedure and Exact Preview-Only Command

1. The existing input server was not stopped during development. To apply the change, the user Ctrl+C's **only that input-server terminal**
   and restarts it with the above `server.py --host ... --port ... --bridge-dir ...` command.
2. Exit VR, close the old diagnostic tab, and reopen **`https://192.168.10.116:8765/`** in Quest Browser.
   PC `SERVER BUILD: preview-v3-…` must exactly match the page's **CLIENT BUILD**.
   `/version` also exposes server_build and disk_build. A mismatch disables VR entry.
   Re-enter the PIN for the new server. Version queries and no-store are used; HTML is read on every GET.
3. Check for other GPU/scenario jobs, then run the **preview-only** test below.
   This mode does not call controller.update, so user input does not change targets.
   Existing IK may still produce physical settling motion while holding the initial pose.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab \
  /isaac-sim/python.sh scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --headless --preview-only --duration 180
```

4. Enter VR on Quest. **Version text, COMM, left/right status, and actual images from 3 cameras** should be visible.
   Check PC CAMERA FIRST FRAME, increasing server preview_http.sent,
   and increasing client preview_status decoded/drawn counters with stage=draw_submitted.
   Also check final preview_ok=true and preview_guard_reason=ok in input.json.
5. If video is missing, do not bypass protection conditions. Run the read-only diagnostics below in another PC terminal while running.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/inspect_preview.py \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab/logs/quest_teleop

docker exec -w /workspace/cyclo_lab cyclo_lab \
  /isaac-sim/python.sh scripts/quest_diagnostic/inspect_preview.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop
```

Matching producer run_id/frame_id (or nearby frame IDs during updates), JPEG size, and metadata establish shared paths.
UID/gid/mode and read errors are reported for every file. The server records current diagnostics in server_status.json.

| Observation | Failure stage |
|---|---|
| No CAMERA FIRST FRAME / no preview metadata | Check simulator RGB/encoding/file writes |
| producer=ok, HTTP requests=0 | Check new page version, VR session/pairing/preview polling |
| HTTP last=file_missing/permission_denied | Server bridge path/permissions |
| HTTP last=frame_stale | Producer updates/performance. Check step_ms and frame_interval_ms; do not extend protection timeout |
| HTTP sent increases, decoded=0 | Check HTTP response receipt/image decoding errors |
| decoded increases, drawn=0 | Check viewer/WebGL texture upload/draw errors |
| drawn increases, preview_guard_reason error | Check client/server build, run/frame, metadata freshness |
| preview_ok=true but nothing visible | Investigate actual HUD/binocular display. Draw submission and visibility are distinct |

This change was validated only with CPU tests and mocked HTTP/JS. No duplicate GPU job or actual Quest connection was started.
Do not remove --preview-only for bimanual testing until preview-only verification is complete.


## Action Replay First-Frame Delay Investigation and demo_8 Selection

Actual B001_test_001 HDF5 name ordering is demo_0, demo_1, demo_10, demo_2, ….
**List index 8 is demo_7; demo_8 is at index 9.** Select by name.
Original demo_8/actions has shape [95,15]; the dataset was inspected read-only.

The previous comparison used a Python condition per GPU element and did not treat NaN as failure.
The new comparator transfers each tensor field to CPU and compares vectorwise with NumPy. Absolute tolerance .01 is retained,
with no relative tolerance. Shape/key mismatches and NaN/Inf fail. Detailed error output is length-limited.
get_state BEGIN/END, compare_states BEGIN/END, compare.cpu_transfer BEGIN/END,
compare.numpy BEGIN/END flush output and report elapsed_s. get_state timing ends at host return;
GPU completion waits may appear in cpu_transfer. The original stall location is not yet confirmed at runtime.

Docker access was denied and NVML queries failed here. Isolated ps could not identify the existing replay PID,
so no process was terminated and no new GPU replay was launched.
Six CPU unit tests and self-comparison/error injection on actual saved states across 95 frames/18 fields passed.
This is not evidence of physical action replay with checked=95/mismatched=0.

In the host's existing replay terminal, stop only that replay with Ctrl+C and confirm exit before running.
If process identification is needed, compare commands with `docker top cyclo_lab -eo pid,ppid,args`.
Do not terminate unidentified PIDs or other simulators.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_demos.py \
  --dataset_file /workspace/cyclo_lab/datasets/quest_tests/B001_test_001/dataset.hdf5 \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episode_names demo_8 --headless --enable_cameras --validate_states
```

Expected selection logs: `indices=[9] names=['demo_8']`, `EPISODE_LOADED ... frames=95`.
Completion requires `REPLAY_VALIDATION checked=95 mismatched=0 expected=95`, `APP_CLOSE END`,
and `REPLAY_EXIT status=completed code=0`. Comparison failures or insufficient frames exit with an error.
Interruptions/exceptions also report progress counts and attempt environment/file/app cleanup.

### Actual EpisodeData Environment-Axis Fix and Process-Exit Checks

`EpisodeData.get_state()` returns `states[state_index, None]`. After the actual loader,
saved joint_position is (1,25), root_pose (1,7), and root_velocity (1,6).
The previous comparator removed the environment axis only from runtime data, marking every frame as a shape mismatch.
Earlier CPU tests directly indexing HDF5 arrays did not reproduce this loader behavior.

Replay now explicitly passes `dataset_has_single_env_axis=True` and removes only the saved state's first axis with `[0]`
after checking: runtime environment count=1/index=0, saved first-axis size=1,
saved ndim=runtime sample ndim+1, and all remaining dimensions identical. No general squeeze/flatten/broadcast alignment is used.
Tolerance .01, key/shape checks, and NaN/Inf failure handling remain.
`REPLAY_FIELD_ERRORS` reports per-episode/field max_abs and first_mismatch_frame (zero-based).
max_abs is null when shape/nonfinite values prevent numerical comparison.

A regression test using the actual vendored HDF5DatasetFileHandler → EpisodeData.get_next_state() was added.
Ten CPU tests passed. Reading original demo_8 through this loader and reconstructing runtime shapes from saved arrays also
passed across 95 frames/18 fields. **This does not establish actual physics replay or numerical reproducibility.**
Docker/NVIDIA access restrictions prevented actual reruns and inspection of existing process PIDs/exit codes.

Returning to the shell after `APP_CLOSE BEGIN` alone does not prove normal close() return or exit code 0.
`replay_checked.py` launches one replay child and reports its OS-returned exit code.
Confirm the previous replay has ended on the host, then use the command below. Do not terminate other processes.

```bash
docker top cyclo_lab -eo pid,ppid,args
```

If the previous replay remains, confirm its exit with Ctrl+C in that terminal, then:

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_checked.py \
  --dataset_file /workspace/cyclo_lab/datasets/quest_tests/B001_test_001/dataset.hdf5 \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episode_names demo_8 --headless --enable_cameras --validate_states
replay_rc=$?
printf 'DOCKER_EXEC_EXIT=%s\n' "$replay_rc"
```

Check actual numerical validation through REPLAY_VALIDATION checked=95/mismatched=0/expected=95.
For mismatches, inspect REPLAY_FIELD_ERRORS. Separately confirm process exit using
REPLAY_PROCESS_EXIT returncode and DOCKER_EXEC_EXIT.
Process code 0 alone does not establish numerical validation. Even without APP_CLOSE END, a parent
REPLAY_PROCESS_EXIT means that child exited (not a guarantee of completed internal Kit cleanup).

### Plate-Velocity Checkpoints and Validation-Failure Exit Codes

User runtime result: robot/toaster/bread comparison fields had max_abs=0; plate pose error 8.28e-5 passed, but
plate velocity maximum error .06838538 failed full-state validation across 95 frames. Robot trajectory agreement is distinct from
full-state validation. Threshold .01 is retained; plate fields are not excluded.

root_velocity follows InteractiveScene.get_state → RigidObjectData.root_vel_w → root_com_vel_w:
world-frame COM velocity [vx,vy,vz,wx,wy,wz], units [m/s,m/s,m/s,rad/s,rad/s,rad/s].
Indices 3,4 are angular velocities x,y. Original demo_8 initial velocities are all 0.
The first recorded state's angular velocity is [0.112790756,-0.031493440,-0.012129337] rad/s.
These are recorded actual velocities, not errors.

Recorded initial_state is captured after reset; states[i] follows env.step with decimation=4.
Replay compares at the same endpoint. dt=.01, render_interval=4, control_dt=.04 are checked against recording metadata
through configure_replay. reset_to writes recorded root_velocity to PhysX and internal caches;
this task's additional restoration clears only articulation drive velocity targets, without overwriting plate velocity.

Current plate cfg: solver position/velocity iterations=16/4, mass=.35 kg,
contact_offset=.001 m, rest_offset=0, max_depenetration_velocity=1 m/s.
Spawn material: static/dynamic friction=.8/.6, restitution=0, friction combine=max.
**The recording lacks full physics cfg, contact forces, contact manifolds, and internal solver state.** It cannot establish whether current
and recorded settings were identical or contact-cache differences caused the mismatch. Contact jitter/nondeterminism is not a conclusion.

New replay prints PLATE_CONFIGURATION and these PLATE_CHECKPOINT entries:
- after_reset_to_before_physics: recorded initial velocity versus restored cached/PhysX velocity, pose, and sensor contact forces.
- after_first_physics_step: PhysX velocity immediately after the first .01-second physics step; no HDF5 substep reference exists here.
- after_first_control_step: cached/PhysX velocity after 4 substeps versus states[0], with componentwise absolute errors.

Sensor contact force immediately after reset may be stale and is not the solver contact state itself.
Diagnostics only observe existing sim.step calls in the first env.step; they add no physics steps or state writes.
Actual GPU checkpoints remain unverified due to access restrictions. Original files and physics/scenarios/actions were unchanged.

The previous wrapper passed through only child returncode. During Python exception propagation, finally's app close could
terminate the process with 0 and hide validation failure. User logs confirmed this failure-reporting problem.
The exact internal Kit native exit call could not be located with available access.
The new wrapper checks a separate verdict JSON using a per-run temporary directory/nonce.
The worker atomically saves its verdict before app cleanup. Even if the child's raw code is 0,
the parent exits 1 for failed verdict/mismatches/incomplete frames, or 2 for missing/corrupt/wrong-run verdicts.
REPLAY_PROCESS_EXIT reports raw code; REPLAY_SUPERVISOR.effective_exit_code is the code passed to Docker.

Use the existing replay_checked.py command. Do not duplicate runs before confirming the previous replay exited.
Expected result for a failure case:
```
REPLAY_PROCESS_EXIT ... returncode=0
REPLAY_SUPERVISOR {"verdict": {"status": "failed", ...}, "effective_exit_code": 1}
DOCKER_EXEC_EXIT=1
```
Fourteen CPU tests passed, including the actual loader, strict comparison, checkpoints without extra steps,
parent exit 1 after a failed verdict even if the real child calls os._exit(0), and exit 2 for missing verdicts.
This does not establish agreement of actual plate physics replay.

### Plate Control Experiment Without Quest: Reset/Render History and Actual Configuration Evidence

Additional runtime evidence: immediately restored recorded/PhysX/cached velocities are all 0; the first .01-second physics step has
vz=-.0981/angular velocity 0; divergence from recorded angular velocity starts at the first .04-second control step.
Thus there is no evidence for missing initial-velocity restoration/cache mismatch; investigation follows physics advancement.
Robot trajectories matched, but full-state validation still failed due to plate velocity.

Source inspection:
- teleop: construction → reset(seed) → render-only WAITING → X → reset(seed) → recording/physics steps.
- replay: construction → reset() → reset_to(initial state) → physics steps. After reset_to's _reset_idx,
  recorded states are rewritten, forward/render run, and articulation drive targets receive additional handling.
- Isaac Lab forward() updates articulation kinematics/fabric; render() uses app.update with playSimulations
  disabled. WAITING contains no sim.step. TimelineProbe additionally records actual times/call counts.
- Recorded states are taken in record_post_step after 4 substeps; replay samples after env.step returns.
  This task has only reset events. No subsequent command/observation update path was found writing plate physics state.
- Actual accumulated contact/internal solver history before demo_8 is not restored from HDF5. Whether this causes the difference is unknown.
- Recording adds 1 overview camera; replay has only the default 3. Rendering loads differ,
  but this alone does not identify the cause of plate physics differences.

New read-only diagnostics:
- Shared record/replay audit.jsonl logs pre/post reset, pre/post WAITING, public sim.step/forward/render call counts,
  current_time/current_time_step_index (when available), and plate PhysX velocities.
- Reads actual plate/table prims and collision descendants, applied physics-material bindings, and USD attributes.
  Records whether each attribute is authored/resolved. USD schema fallbacks are distinguished from actual PhysX queries.
- Reads available masses/inertias/COM/material properties/contact/rest offsets and other values
  from the existing plate PhysX tensor view. Unsupported getters are unavailable; errors are query_failed.
- If the static table lacks an existing rigid tensor view, only USD evidence is collected; engine values are not inferred.
- cfg null means unspecified configuration intent, not 0 or an actual PhysX default.

GPU experiments could not run in this session due to Docker permission/NVIDIA query restrictions.
The following is an implemented procedure, not successful experimental results. Check existing runs first; do not duplicate them.
Original B001_test_001 is not written to; execution is refused if the new output directory already exists.

1. Record without Quest/input server (existing teleop initial-wrist-target hold control, open grippers/fixed lift).
   Two runs of 95 frames each, with 30 renders before each explicit reset.
   There is no external manipulation, but gravity-compensation/target-hold IK actions remain. This is not an all-actions=0 test.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/record_toast_noinput.py \
  --output /workspace/cyclo_lab/datasets/quest_tests/plate_noinput_001 \
  --operator operator_B --scenario_index 1 --seed 1 \
  --episodes 2 --frames 95 --wait-renders 30 --headless
```

Confirm recording completion and process exit before proceeding. This does not exactly reproduce demo_8's preceding 8-demonstration history.
New metadata records experiment type/frames/episodes/render counts.

2. Action-replay only the new recording (comparison threshold remains .01 for both episodes).

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_checked.py \
  --dataset_file /workspace/cyclo_lab/datasets/quest_tests/plate_noinput_001/dataset.hdf5 \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episode_names demo_0 demo_1 \
  --audit-dir /workspace/cyclo_lab/datasets/quest_tests/plate_noinput_001/replay_audit \
  --headless --enable_cameras --validate_states
replay_rc=$?
printf 'DOCKER_EXEC_EXIT=%s\n' "$replay_rc"
```

3. Compare recording/replay configuration evidence and first substep/control step on CPU.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/compare_plate_audits.py \
  datasets/quest_tests/plate_noinput_001/record_audit/audit.jsonl \
  datasets/quest_tests/plate_noinput_001/replay_audit/audit.jsonl --episode demo_0
```

Change the command's final argument to `--episode demo_1` to compare the repeated-reset episode.
If divergence starts immediately, inspect reset/render/configuration history; if the first substep agrees but the control step differs,
investigate substeps 2–4 and contact formation. Empty property_differences does not imply equality of unavailable values
or solver caches. Reproduction without manipulation supports occurrence without Quest motion,
but does not itself prove contact nondeterminism.

CPU: 14 existing replay regressions + 3 evidence-comparison/call-count/None-distinction tests passed; Python syntax passed.
Actual USD/PhysX query APIs and GPU recording/replay without manipulation remain unverified at runtime.

### New VR Recording B001_test_002: Single-Episode Comparison with Shared Audit

In the user's runtime test, two no-manipulation episodes passed with checked=190/mismatched=0/expected=190
and effective_exit_code=0. This validates that path, not the cause of the old VR demo_8 plate difference.
Since teleop lacked auditing, the same TimelineProbe, plate_configuration, plate_checkpoint,
and first-physics-step hook were added only in recording mode (--record-dir).
Original data, physics, control, tolerances, and HTTPS/input/video protection paths were unchanged.
This change does not require restarting the display page or input server. If an older teleop is running,
the user exits only that teleop and starts the new launcher. Do not run alongside GPU replay.

Run in a new folder (refuse rather than overwrite an existing folder):

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open \
  --record-dir /workspace/cyclo_lab/datasets/quest_tests/B001_test_002 \
  --record-seconds 8
```

Retain the existing HTTPS server and Quest VR input connection. After both hands are valid and four images are visible,
look forward and release both squeezes. Press/release X once and confirm EPISODE_STARTED.
Re-engage one squeeze for a small motion, then release. Save with A or wait for automatic completion after 8 wall seconds.
After RECORD_SAVED demo_0 and WAITING, **exit with Ctrl+C without pressing X again**.
Confirm final metadata episode_count=1 and frames>0. The 8-second timer starts after initial diagnostic queries finish.
Actual frame count depends on execution speed and is not fixed at 95. Grippers remain fixed open.

Recording audit is stored in B001_test_002/record_audit/audit.jsonl. Filter each row by episode=demo_0
to align pre/post WAITING, pre/post reset, first physics/control steps, and actual configuration evidence with replay.
Names use the actual exported-episode count, so empty recording attempts do not shift saved names.

After teleop exits and HDF5 closes, replay by name:

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_checked.py \
  --dataset_file /workspace/cyclo_lab/datasets/quest_tests/B001_test_002/dataset.hdf5 \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episode_names demo_0 \
  --audit-dir /workspace/cyclo_lab/datasets/quest_tests/B001_test_002/replay_audit \
  --headless --enable_cameras --validate_states
replay_rc=$?
printf 'DOCKER_EXEC_EXIT=%s\n' "$replay_rc"
```

replay_audit must be a new directory. Use another audit directory for reruns.
Check checked=expected=N, mismatched=0, effective_exit_code=0, and DOCKER_EXEC_EXIT=0.
On failure, preserve REPLAY_FIELD_ERRORS and both audits. Comparison command:

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/compare_plate_audits.py \
  datasets/quest_tests/B001_test_002/record_audit/audit.jsonl \
  datasets/quest_tests/B001_test_002/replay_audit/audit.jsonl --episode demo_0
```

60 CPU regressions (Quest 43 + replay/audit 17) and syntax checks passed for this change.
The user performs actual new VR recording/replay; this work did not run it.

### Control-Status Panel Below the Central Image (control-status-1)

The central image, per-eye transform, and saved casting layout remain unchanged. The existing bottom guidance area
shows WAITING/RUNNING, left/right input validity, the simulator's actual control verdict, squeeze pressed/value,
and trigger value. `SQ ON` is only a button state. `Arm active` reflects the launcher's
`controller.states[side].reason == active`, not a measurement of joint displacement.
`Anchored` identifies the frame when a new squeeze press establishes the reference.
Top INPUT orange means invalid input; dark green means valid input; bright green means any button
is pressed with valid input. Top colors do not indicate active control.

Status arrives through each JPEG's metadata at approximately 5 Hz. When video expires,
status becomes unavailable instead of retaining the previous active indication. START_BLOCKED lists unmet
conditions. Missing video-display confirmation can also mean no display/version mismatch, not just stale video.
This information is display-only; it is not input to control decisions or HDF5 observations.

Apply by exiting the current teleop normally, restarting the input server with the same options,
and restarting teleop once with its existing options. Do not stop other jobs.
Exit VR, reload the same HTTPS address, and pair with the new PIN.
Check matching CLIENT BUILD/server BUILD and Applied XR display revision `control-status-1`.
Do not reset saved display preferences. After entering VR, inspect WAITING and both-hand status
before starting with X. GPU/Quest binocular readability and casting require runtime checks.

### overview-status-2: Status Panel and Bimanual Reproduction Diagnostics

During the 2026-11-03 investigation, the bridge reported server `preview-v3-4c75fc835c8d`, Quest page
`preview-v3-bb6990bfcc4c / casting-fit-3`, and `reload_required`.
An old page was therefore running, and version checks blocked video confirmation.
At that inspection instant, the left source was meta-fixed-hand and the right source absent. This snapshot does not
establish the cause during earlier two-controller operation. Evidence was preserved in
`logs/quest_diagnostics/status_investigation/*_before.json`.

The status panel now overlays the top of FRONT OVERVIEW. Image position/scale
remain unchanged. Missing/stale metadata is also displayed. C/S on the first line means
client/server build; Applied XR display status_panel records actual canvas coordinates,
rendered, metadata_received/fresh, and input_seq. The previous control-status-1 section describes an older version.

`--diagnostic-log NEW_PATH.jsonl` records display/control diagnostics separately from HDF5: approximately 5 Hz in WAITING,
every control step in RUNNING, and start/stop requests. Each decision row includes:
- Quest seq/session, source handedness/candidates/pose verdict/raw buttons, and server-normalized results
- Input age at read time and actual control-decision time, visibility, client/server builds
- Quest-reported frame age (not a synchronized absolute timestamp), server video guard, loop_gap/step_ms
- Lifecycle before/after start, requesting button, previous/current control reason, ready/anchor/basis, safety_epoch
- Pre-physics-step measured position, target position, home distance/rotation, and tracking error
These are recorded together. Raw diagnostic fields are not control inputs. Reaching home_distance 0.05 m
is distinct from target tracking error and alone does not establish IK failure.

Apply by normally exiting/restarting teleop and input server in their respective terminals,
then leaving Quest VR and **reloading** the same HTTPS address. VR re-entry alone does not
replace old JS. If needed, close the existing Quest tab and reopen the address (no site-data deletion needed).
After server restart, pair with the new PIN and verify matching builds first.

Short reproduction (no demonstration recording):
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
QUEST_RUN="arms_$(date +%Y%m%d_%H%M%S)"
mkdir -p "logs/quest_diagnostics/$QUEST_RUN"
set -o pipefail
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers \
  --diagnostic-log "/workspace/cyclo_lab/logs/quest_diagnostics/$QUEST_RUN/decisions.jsonl" \
  2>&1 | tee "logs/quest_diagnostics/$QUEST_RUN/teleop.log"
```
In WAITING, hold both controllers and press/release left then right squeeze/trigger to inspect raw values only.
Release both squeezes, look forward, and press X. Keep them released until RUNNING and both hands ready,
then hold left squeeze, move 2–3 cm, and release. Repeat for the right hand.
Hold each stage for 2–3 seconds. If control is active but motion absent, do not increase displacement;
wait 2 seconds, then release. A returns to WAITING; Ctrl+C exits normally. Fixed 5 cm/15° bounds
and the original 240-second episode timeout remain. No HDF5 is created and existing recordings are untouched.

### compact-status-3: Two Status Lines Without Video Overlap

The overview-status-2 in-video overlay was removed. The existing top diagnostic area uses a fixed 24 px font;
the first line shows WAITING/RUNNING, actual left/right control status, and raw SQ/TR values (one decimal place).
The second line shows only the main blocking reason. Missing metadata/stale video also use at most two lines.
Image size/position/aspect ratio and saved casting center/scale are retained. The central crosshair is omitted
to avoid obscuring video; selected corner/outer-border diagnostics remain.

Build/revision, latency, all blocking reasons, and raw status are in the page's collapsed **Detailed diagnostics**.
Expand after exiting VR to inspect the latest received VR status. No new controller-button mapping was added.
Changes are limited to hud.js/index.html, display tests, and documentation. Input/control/physics/recording code is unchanged.

Apply by releasing squeeze, exiting VR, and normally restarting only the input server with the existing command.
Reload the Quest page, pair with the new PIN, and re-enter VR. No teleop simulator restart
or display-preference reset is needed. Actual binocular readability/casting clipping must be checked on Quest.

### head-wrists-4: HEAD + Both Wrists and Controller Connectivity

The default Quest view has a large HEAD image above equal-width LEFT WRIST / RIGHT WRIST images.
Complete 300×300 camera tiles are extracted at display time from the existing 960×936 composite.
Since HEAD is square, the wide upper area has side margins. Images are neither cropped to fill
nor stretched. FRONT OVERVIEW is excluded only from VR display; sensors/recording/transmission sources remain.
Enlargement does not increase resolution beyond the existing stream.

The status bar above HEAD shows only left/right connectivity (green/gray plus text). Connected requires a current actual Touch Plus source,
an input packet accepted by the server with the same source_id, and both ACK and that packet's
client input timestamp within 250 ms. Hand input is excluded. Invalid pose,
WAITING, released squeeze, or missing video alone does not imply disconnection. This is not
an active-control indication. Control/safety decisions remain unchanged and appear in detailed diagnostics/logs.

Changes affect only HUD/page display, tests, and documentation. Teleop restart is unnecessary.
The input server fixes its build at startup and requires restart. Exit normally with Ctrl+C in its terminal,
then run below (retain existing options if using separate cert/key files).

```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/server.py \
  --host 192.168.10.116 --port 8765 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab/logs/quest_teleop
```

Release squeeze and exit Quest VR. After restarting the server, reload the default address
`https://192.168.10.116:8765/` and Pair with the new PIN. In detailed diagnostics, verify CLIENT BUILD,
server BUILD, and revision head-wrists-4, then re-enter VR. Re-entering VR in the old tab retains
in-memory JS, so reload the page. If needed, close the tab and reopen the default
address. Long URLs, manual queries, site-data deletion, and display-preference resets are unnecessary.

Socket-free CPU tests exercise the actual GET handler for `/`, the three build-query JS paths, `/version`, and Cache-Control:no-store.
A real HTTP/TLS communication test with a new server was not run because socket creation was restricted.
Actual Quest readability/casting bounds require runtime checks.

### head-wrists-5: Reduced Inner Margins and Inset Connectivity Bar

During inspection, packet.xr_display reported head-wrists-4 / status_panel.rendered=true, y=52.48.
Bar creation was confirmed, but actual casting crop bounds were not. The new bar moves down to
x=108,y=96,w=808,h=40 on the 1024×1024 canvas, leaving top clearance. Without receipt history,
it shows gray 'Checking'; afterward it uses the existing connectivity decision. Known expired input means disconnected.

HEAD is 480×480 at (272,144); left/right WRIST are each 328×328 at (108,648)/(588,648).
These increase from approximately 462×462 / 257×257 in the previous default layout. Labels occupy empty space beside HEAD
and the 24 px image gap, without overlapping images. Bottom clearance is 48 px.
Overall XR scale/center are retained. The three images use this fixed internal sizing/spacing;
stored Inner margin does not apply to this layout. Sensors/source images/control are unchanged.

Preview: open `logs/quest_diagnostics/layout_preview_v5/preview.html` in a PC browser.
This standalone HTML uses current HUD code directly, captured preview cameras, and example connectivity states.
It does not reproduce actual Quest optics/casting crop. Chrome screenshot execution failed under sandbox restrictions;
only CPU mocked rendering and HTML composition were validated.

The input server requires normal restart to refresh the build; teleop does not.
Apply by reloading the default HTTPS page, pairing with a new PIN, and re-entering VR.

### native-preview-rec-6: Native-Resolution Transmission and Actual REC State

Original HEAD/LEFT WRIST/RIGHT WRIST are 244×244 RGB in both runtime stats and B001_test_002 HDF5.
Previous path: 244→300 (Pillow RGB default BICUBIC)→960×936 composite JPEG Q75 (measured 4:2:0)→
Quest 300 tile→HEAD480/WRIST328→1024 HUD texture→per-eye viewport. Text is drawn directly on the HUD,
without JPEG encoding. At saved .5 scale and 1680×1760 viewport, the 1024 HUD
occupies approximately 840 px per eye, yielding HEAD approximately 394 px and wrists approximately 269 px. Meta re-encoding/crop is unmeasured.

The new path packs full 244 px tiles without resizing into a 768×256 atlas, transmitted as JPEG Q90/4:4:4.
Source tile origins are (6,6)/(262,6)/(518,6), all 244×244. Quest enlarges once to the same 480/328 px
as before. No sharpening. Sensors/FOV/training observations/HDF5 are unchanged. Overview sensor/acquisition
remain, but undisplayed overview pixels are omitted from the new preview. Clients can still read the old 960×936 preview,
but the clarity improvement and actual REC state require teleop restart.

REC reads only DiagnosticRecorder.active (true at start, false at export/finish).
It is not inferred from RUNNING or record-dir. Expired status frames or an older producer without recording
show 'Checking'. Three-image and connectivity-indicator positions/sizes remain unchanged.

Read-only comparison of the same 48 saved source frames is recorded in
`logs/quest_diagnostics/quality_native_v6/report.json` and `comparison.html`.
CPU-model mean PSNR with bilinear enlargement to display size: HEAD 42.12→47.96 dB,
LEFT 46.15→54.62 dB, RIGHT 46.21→54.57 dB. These are not actual Quest optical measurements.
Median CPU composition+encoding: previous 10.37 ms/new 0.45 ms; new median payload 21,139 bytes.
Previous overview pixels were replaced with black in this comparison, so previous total payload/time is not a live-equivalent comparison.
A pre-change actual bridge sample over 3 seconds showed 10 new frames, median frame interval 316 ms, step 150 ms,
and payload 65,506 bytes (live_before.json). Post-change actual GPU/Quest speed/latency remain unverified.
`preview.json.timings.encoding` records encode_ms/bytes/quality; Quest preview_status records
bytes/decode_ms/fetch_decode_ms/frame_age_ms for post-application comparison. Protection timeouts are unchanged.

The inherent detail limit of 244×244 remains. If higher source resolution is needed, a separate observation-only
high-resolution camera could be considered instead of changing training cameras, but GPU cost and FOV/pose matching require validation;
it was not added here.

Apply: exit current teleop normally → restart input server normally → run teleop below → reload Quest page,
pair with new PIN, enter VR. Quality-check command without recording:
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/server.py \
  --host 192.168.10.116 --port 8765 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab/logs/quest_teleop
```
In another terminal:
```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers
```
For actual REC verification, exit the above teleop normally, then run the following instead (no duplicate runs).
```bash
QUEST_REC="B001_rec_status_$(date +%Y%m%d_%H%M%S)"
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers \
  --record-dir "/workspace/cyclo_lab/datasets/quest_tests/$QUEST_REC" \
  --record-seconds 8
```
WAITING NO REC → release both squeezes and press X → red REC after actual recording starts → A or 8-second completion →
NO REC. Save only to a new test folder; preserve existing recordings. The user performs actual REC/Quest checks.

### practice-timing-7: Bounded Practice Workspace and Both-Gripper Test Recording

This feature prepares code for actual toast practice. Quest bimanual/gripper contact, expanded-workspace
IK reachability, and physics replay of new VR episodes remain unverified. CPU validation must not be
interpreted as GPU runtime validation. Existing scenarios, physics dt .01/decimation4/control dt .04/render_interval4,
training/recording camera resolution/FOV/observations, and 15D action format remain unchanged.

At inspection, the latest `B001_rec_status_20261103_194138/dataset.hdf5` held a writer lock.
Without bypassing the original lock or modifying the file, a separate snapshot whose size/mtime were stable across copying
was read. Per `logs/quest_diagnostics/practice_audit/latest_record_report.json`, demo_0..8 had
50/51/6/50/50/50/50/50/49 = 406 frames; only demo_2 was manual_stop, the rest short_test_duration.
No app exit_reason existed and the sidecar remained at initial values, so normal app exit/exit code were unconfirmed.
HDF5 episode export is separate from program exit. For final inspection of the original, read it after
normal shutdown in the user's terminal. Both gripper commands in existing recordings were always +1 (open).

The 8-second limit is time.monotonic wall time. In this run, an 8-second episode produced approximately 49–51 control
steps = 1.96–2.04 simulation seconds, about 0.24× real time. New --record-seconds 0 records until A/original
environment termination. Default 8 remains, as does the original 240 simulation-second timeout.

Performance samples distinguish WAITING and RUNNING. An 8-second live WAITING sample had 40 preview frames,
median production interval 200 ms, render-only step 17.3 ms, encode 0.91 ms, Quest fetch+decode 31.9 ms,
decode 2.7 ms, and frame age 206 ms. Do not confuse this with the previous RUNNING recording at 0.24× real time.
Existing logs alone cannot separate physics/render/observation costs or establish Quest photon latency.
The new PerformanceProbe delegates each original call once and measures wall time without extra physics/render/GPU synchronization.
Render/physics/observation timings are inclusive CPU times due to asynchronous GPU processing,
not an additive GPU profile. Receipt→process_action/first apply_action/first physics entry use
the same host monotonic clock. Quest→server one-way latency is unmeasured without clock synchronization.

Display improvements: producer cap changed to --preview-hz 15 (adjustable 1–25), browser polling to 100 ms.
Actual rate is limited by env.step/network; 15 FPS is not guaranteed with slower steps.
Undisplayed overview CPU reads/copies are skipped while retaining its sensor/configuration. WAITING renders
only when a preview is needed. RUNNING physics/render/observation computation is not skipped.
The input snapshot is reread immediately before control after reading poses, avoiding stale pre-reset input.
Existing 250 ms input/1 s video/250 ms loop-gap guards and release requirements on source changes remain.

Practice preset (`--control-profile practice`):
- Spherical translation range .55 m / rotation 120° from initial wrist; position scale .5 / rotation scale .75.
- Fixed workspace (robot-root frame): x=[.1,.85], y=[-.85,.85], z=[1.02,1.8] m.
- Additional target-lead limit: at most 4 cm/15° ahead of measured wrist. Existing 8 cm tracking-error termination remains.
- Action correction speed .10 m/simulation-second, .8 rad/simulation-second. Wall-clock speed scales with simulation rate.
- --max-translation(.01~.75), --max-rotation-deg(1~180), --position-scale(.05~1),
  Adjustable via --rotation-scale(.05–1.5), --linear-speed(.01–.15), --angular-speed(.05–1.5).
- Default diagnostic preset retains the existing 5 cm/15°/.25/.5 and speed settings. No unlimited option.

Recorded B001 observations place the initial right wrist at (.36094,-.39541,1.44191) m and bread centers
approximately (.45,-.46–-.31,1.0932) m. Wrist-to-center distances are .360–.369 m; mirrored left-wrist distances are .795–.929 m.
These values do not establish grasp offsets or collision-free IK solutions. The .55 m range supports right-hand approach and central
handover, not direct left-hand reach to rack bread. Practice right-hand approach/grasp,
central handover to the left, then toaster approach. WORKSPACE_RESET logs actual root-frame
wrist/bread-center coordinates and distances at every reset. Diagnostic logs distinguish target limits from IK tracking error.

The recording gripper prohibition was an initial diagnostic validate_recording_args restriction, not a physics/action constraint.
It was removed (--preview-only recording remains forbidden). Trigger 0..1 now maps to gripper
+1..-1, stored independently at action indices 12/13. CoupledGripperPositionAction uses continuous opening with +1→joint0,
-1→joint1.10. Targets change only while squeeze is active and remain held on release.
A 21-frame CPU test passed using the actual DiagnosticRecorder, vendored HDF5 writer/loader, get_next_action,
and actual task gripper splitting/processing methods. Results are in
`logs/quest_diagnostics/practice_audit/gripper_contract/` and use synthetic CPU fixtures.
These are not physics-replay data and must not be submitted as actual demonstrations. New actual recordings remain
quest_tests diagnostic data with success=False and separately preserved task_success_observed.

Apply by exiting existing teleop normally with Ctrl+C in its terminal and checking the exit code. Do not stop other jobs.
Exit the input server normally in its own terminal, then run below. Retain separate cert/key options if used.
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/server.py \
  --host 192.168.10.116 --port 8765 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab/logs/quest_teleop
```
Practice without recording (separate terminal, one run after the previous teleop exits):
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
QUEST_RUN="practice_$(date +%Y%m%d_%H%M%S)"
mkdir -p "logs/quest_diagnostics/$QUEST_RUN"
set -o pipefail
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers --control-profile practice --preview-hz 15 \
  --diagnostic-log "/workspace/cyclo_lab/logs/quest_diagnostics/$QUEST_RUN/decisions.jsonl" \
  2>&1 | tee "logs/quest_diagnostics/$QUEST_RUN/teleop.log"
QUEST_EXIT=${PIPESTATUS[0]}
echo "DOCKER_EXEC_EXIT=$QUEST_EXIT"
```
Actual bimanual/gripper test recording (run instead after practice exits; new directory):
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
QUEST_RECORD="B001_practice_$(date +%Y%m%d_%H%M%S)"
mkdir -p "logs/quest_diagnostics/$QUEST_RECORD"
set -o pipefail
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers --control-profile practice --preview-hz 15 \
  --record-dir "/workspace/cyclo_lab/datasets/quest_tests/$QUEST_RECORD" --record-seconds 0 \
  --diagnostic-log "/workspace/cyclo_lab/logs/quest_diagnostics/$QUEST_RECORD/decisions.jsonl" \
  2>&1 | tee "logs/quest_diagnostics/$QUEST_RECORD/teleop.log"
QUEST_EXIT=${PIPESTATUS[0]}
echo "DOCKER_EXEC_EXIT=$QUEST_EXIT"
```
Reload the default Quest HTTPS address→new PIN→VR. Release both squeezes, look forward, then press X.
Hold right squeeze and start with small movements. Trigger release=open, press=close (while squeeze is active).
After input/video loss, release both squeezes and re-engage. A stops physics advancement and enters WAITING (saving if recording).
X resets the same scenario for a new episode, not a resume. For the first new recording, act for 5–10 seconds, then use A
to finish and validate action replay first. Actual grasp/handover success requires separate runtime verification.

Read-only measurement from another PC terminal during RUNNING:
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/sample_performance.py \
  --bridge-dir logs/quest_teleop --seconds 15 \
  --output "logs/quest_diagnostics/performance_$(date +%Y%m%d_%H%M%S).json"
```
After recorded teleop exits normally, replay using QUEST_RECORD in the same terminal.
```bash
set -o pipefail
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_checked.py \
  --dataset_file "/workspace/cyclo_lab/datasets/quest_tests/$QUEST_RECORD/dataset.hdf5" \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episode_names demo_0 --validate_states --headless --enable_cameras \
  2>&1 | tee "logs/quest_diagnostics/$QUEST_RECORD/replay.log"
QUEST_REPLAY_EXIT=${PIPESTATUS[0]}
echo "DOCKER_EXEC_EXIT=$QUEST_REPLAY_EXIT"
```
EOF の代わりに終了コード0・checked=expected・mismatched=0を確認する。許容差0.01や
接皿フィールド除外は変更していない。実機GPUでこの新記録を再生する検証は未実施。

### practice-response-8: Selectable Limits and Target Cancellation on Release

This section supersedes the previous practice-preset description. HEAD/WRIST/connectivity/REC layout is unchanged.
Original scenarios, physics dt, joints/actuators/IK/cameras/training observations/HDF5 format were unchanged.
GPU access was blocked by Docker socket permissions in the current tools. Existing GPU logs were analyzed,
but new-code GPU response, contact-free opening, runtime recording/replay could not be tested. CPU validation is not
substitute evidence. Other project jobs and running servers/teleop were not stopped.

Analysis restricted to RUNNING in `logs/quest_diagnostics/practice_20261103_202046/decisions.jsonl`:
510 steps; valid adjacent intervals simulation 20.24 s/wall 85.23 s=0.23747× real time. Median step 164.22 ms,
physics_call61.47ms, apply_action30.62ms, render_call22.06ms, observations9.65ms,
scene_update 10.32 ms, process_action 4.83 ms. These are inclusive CPU wall timings where asynchronous GPU work
may appear in subsequent calls, not a GPU-only profile. Recording cost is unmeasured because this run did not record
(this version additionally instruments recorder pre/post/export hooks).

Receipt→process 27.71 ms/first apply 33.34 ms/first physics entry 43.81 ms. Preview 167.68 ms,
readback 0.72 ms, encode 0.87 ms, Quest fetch+decode 36.4 ms (including decode 2.7 ms), frame age 157.67 ms.
Quest/host clocks were not synchronized, so one-way network/input-to-photon latency is unknown.
This log contained 0 active-control samples. All valid-source squeeze values were 0; most remaining samples
were excluded hand sources or awaiting reference. Thus velocity saturation, active tracking error, and actual gripper response
cannot be computed. This does not imply the user never operated at other times.
Results are preserved in `logs/quest_diagnostics/response_v8/before.json`.

The old speed cap did not limit target-generation speed; action() instead `clipped error to speed*simulation_dt`.
Thus .10 m/sim-second × .237× real time ≈ .0237 m/wall-second.
Previous practice continued tracking the remaining target through action() after squeeze release.
New practice updates targets to the current measured pose on release/intermediate squeeze/invalid input/video expiry/loop gap/source change,
and sends arm Cartesian action 0. This does not instantaneously stop physical inertia or existing null-space posture
correction. The first re-clutch frame also anchors to measured pose rather than restoring old targets.
Diagnostic mode retains its existing target-hold behavior.

New options (new limit-disabling options are allowed only in practice; diagnostic mode raises an error):
- --no-home-limits: removes only initial-reference .55 m/120° limits; incompatible with --max-translation/--max-rotation-deg.
- --no-speed-limits: removes teleop linear/angular action-correction caps; incompatible with --linear-speed/--angular-speed.
- --workspace off: omits the arbitrary table box. Default table retains the previous box.
- --no-target-lead: removes translation/rotation lead caps. Not recommended for the first runtime comparison; incompatible with lead-value options.
- --max-target-lead .01–.5 m (default .12), --max-angular-lead-deg 1–120 (default 45).
- --position-scale .05–1 (default practice 1/diagnostic .25), --rotation-scale .05–1.5 (default practice 1/diagnostic .5).
- Finite home options .01–.75 m / 1–180°; finite speed options .01–.15 m/sim-second / .05–1.5 rad/sim-second.
- --tracking-stall-seconds .5–10 wall seconds, default 2.

Practice no longer exits immediately for tracking error >8 cm or >30°. If the target remains within approximately 2 cm/5°,
and combined error (distance + .1*angle) fails to decrease by at least 2 mm for the specified wall time
and at least 5 control samples, the episode ends and enters WAITING. This distinguishes stalls from ordinary lag
with continuing progress. Discontinuities >.6 m or >170° stop control before that target reaches IK.
A immediately enters WAITING; a new X resets. The 250 ms input/loop-gap guard, video freshness, Touch Plus check,
squeeze release after reconnection, joint/actuator limits, and IK remain. Valid targets are not necessarily indefinitely reachable.

Grippers retain continuous control through CoupledGripperPositionAction: trigger 0/.25/.5/.75/1 →
action +1/+.5/0/-.5/-1 → each linkage-joint target 0/.275/.55/.825/1.10 rad.
Master settings: velocity 2.2 rad/s, effort 30, stiffness 100, damping 4.
Slave settings: effort 20, task stiffness 100/damping 4. Slave velocity_limit_sim=None is not interpreted as
infinite or a specific PhysX velocity. Startup GRIPPER_CONFIGURATION distinguishes runtime
joint-velocity-limit buffers from configuration values. Physical velocity/contact settings are unchanged.
The last gripper target is held while squeeze is released. Practice re-clutch applies the current trigger on the first frame
(previously the frame after anchoring). Action semantics/training/replay indices are unchanged.

Diagnostics read actual/target angles and velocities for all 8 joints across both grippers together at at most 2 Hz, without
adding GPU synchronization every frame. This is joint-based opening, not finger-gap measurement in mm. Trace fields
for existing measured wrists plus measured_sample_monotonic, target_generated_monotonic, action, and limits_hit
support command/measurement timing comparison. Recorder-hook timings were also added. The CPU action/recording/loader
21-frame round trip in `logs/quest_diagnostics/response_v8/gripper_contract/` uses synthetic fixtures.
Do not submit it as a GPU demonstration.

To apply, normally stop existing teleop/server with Ctrl+C in their respective terminals. Do not run the GPU commands below
concurrently. Keep other projects running.

Input server:
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/server.py \
  --host 192.168.10.116 --port 8765 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab/logs/quest_teleop
```
Practice without recording:
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
QUEST_RUN="response_$(date +%Y%m%d_%H%M%S)"
mkdir -p "logs/quest_diagnostics/$QUEST_RUN"
set -o pipefail
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers --control-profile practice \
  --position-scale 1 --rotation-scale 1 --no-home-limits --no-speed-limits --workspace off \
  --max-target-lead 0.12 --max-angular-lead-deg 45 --tracking-stall-seconds 2 --preview-hz 15 \
  --diagnostic-log "/workspace/cyclo_lab/logs/quest_diagnostics/$QUEST_RUN/decisions.jsonl" \
  2>&1 | tee "logs/quest_diagnostics/$QUEST_RUN/teleop.log"
QUEST_EXIT=${PIPESTATUS[0]}
echo "DOCKER_EXEC_EXIT=$QUEST_EXIT"
```
Short test recording (new path after the above run exits):
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
QUEST_RECORD="B001_response_$(date +%Y%m%d_%H%M%S)"
mkdir -p "logs/quest_diagnostics/$QUEST_RECORD"
set -o pipefail
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers --control-profile practice \
  --position-scale 1 --rotation-scale 1 --no-home-limits --no-speed-limits --workspace off \
  --max-target-lead 0.12 --max-angular-lead-deg 45 --tracking-stall-seconds 2 --preview-hz 15 \
  --record-dir "/workspace/cyclo_lab/datasets/quest_tests/$QUEST_RECORD" --record-seconds 0 \
  --diagnostic-log "/workspace/cyclo_lab/logs/quest_diagnostics/$QUEST_RECORD/decisions.jsonl" \
  2>&1 | tee "logs/quest_diagnostics/$QUEST_RECORD/teleop.log"
QUEST_EXIT=${PIPESTATUS[0]}
echo "DOCKER_EXEC_EXIT=$QUEST_EXIT"
```
Reload Quest's default https://192.168.10.116:8765/→new PIN→VR. Release both grip(squeeze) buttons,
look forward, and press X. One hand at a time: squeeze and move 2–3 cm→release for 2 seconds→re-clutch elsewhere→repeat for both sides.
If no errors occur, expand to 10–20 cm. Away from object contact, press trigger incrementally,
hold intermediate values for 2 seconds, and test squeeze release/re-engagement. Exact 5-value raw-input tests passed only on CPU.
Briefly exit VR; verify release is required after input expiry/recovery. A finishes/saves; Ctrl+C exits the app.
These runtime results must establish whether residual targets cause delayed motion and confirm actual opening.

Analyze the completed trace (use QUEST_RUN instead of QUEST_RECORD without recording):
```bash
python3 scripts/quest_diagnostic/analyze_response.py \
  --log "logs/quest_diagnostics/$QUEST_RECORD/decisions.jsonl" \
  --output "logs/quest_diagnostics/$QUEST_RECORD/analysis.json"
```
Actual action replay after teleop/HDF5 shutdown:
```bash
set -o pipefail
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_checked.py \
  --dataset_file "/workspace/cyclo_lab/datasets/quest_tests/$QUEST_RECORD/dataset.hdf5" \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episode_names demo_0 --headless --enable_cameras --validate_states \
  2>&1 | tee "logs/quest_diagnostics/$QUEST_RECORD/replay.log"
QUEST_REPLAY_EXIT=${PIPESTATUS[0]}
echo "DOCKER_EXEC_EXIT=$QUEST_REPLAY_EXIT"
```
Measured before/after comparison and checked=expected/mismatched=0/exit code 0 have not yet been achieved.
