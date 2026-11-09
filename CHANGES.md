# Changes

## ① Branch Purpose

`toast-quest` is a shared branch for teleoperating the FFW BG2 bimanual toast environment through
Quest WebXR and collecting demonstrations across different object configurations. The task ID is
`Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2`. `toast-quest` is the Git branch name, distinct from
the task registration version `-v2`. The Quest launcher uses this fixed ID, registered with environment
class `MakeToastFFWBG2BimanualEnv` and configuration class `MakeToastFFWBG2BimanualServeEnvCfg`.
The branch includes a four-groove bread rack, the current behavior and task success criteria, the Quest
server/client, 100 new scenarios, and validation tools.

The comparison baseline is fixed at **`5f5086d11f664494119086de30a9e925b12022ad`** (`add readme of toast`, 2026-11-02) in `badajhong/cyclo_lab`. Both the parent of the first development commit, `761c8ac`, and the branch-creation reflog point to this commit.

File changes by category and the evidence for this baseline are documented in the
[baseline comparison](docs/toast_quest/BASELINE.md).

## ② Changes from the Baseline Environment

This description reflects the toast environment code on the current `toast-quest` branch.
The baseline column below refers to the fixed commit above.

| Feature | Baseline `5f5086d` | Current toast-quest |
|---|---|---|
| Control | Existing bimanual IK, gripper control, and recorder tools | Added Quest WebXR input from both controllers, clutch/trigger control, status/HUD, and previews from 4 cameras |
| Bread rack | RoboDojo bread_shelf, scaled to (2,1,1) in the bimanual environment | Native 230×130×45 mm four-groove bread rack at scale (1,1,1), with updated relative poses for all four bread slices |
| Automatic activation | bread_0 and bread_1 loaded in separate slots, with the toaster lever crossing the 95% activation threshold | At least one of the four slices correctly loaded, with normalized lever depression crossing the 90% activation threshold |
| Heating | 5 seconds after lowering completes | 4 seconds after lowering completes, measured in simulation time |
| LED | No cycle-status LED | ON during lowering/heating; OFF from the start of rising |
| Bread carriage | Lower limit/lowering target −45 mm; upper limit/rising target +15 mm; travel 60 mm | Lower limit/lowering target remains −45 mm; upper limit/rising target +35 mm; travel 80 mm |
| Bread-related success | Both bread_0/1 on the plate, with bread_2/3 remaining on the bread rack; no per-ID heating evidence | At least one fully heated slice must satisfy the plate-placement criteria under the same ID; remaining-slice retention requirement removed |
| Plate-local XY check | Entire bread outline within the plate radius minus 0.5 mm | Bread geometry center at a plate-local XY radius **less than 20 mm** |
| Left/right master/slave stiffness and damping gains | Already stiffness=100, damping=4 in this environment | Final values **unchanged**; explicitly specified in the environment configuration, with added Quest configuration/readback validation |
| Left/right master joint1 velocity limit | 2.2 rad/s | 6.5 rad/s |
| Scenarios | No fixed 100-scenario delivery or group selection | Added 100 new scenarios, A/B and four-subgroup selection, and layout diagrams while preserving the existing list |
| Recording/replay | Existing Isaac Lab recorder/replay | Added scenario provenance, per-slice heating state, diagnostic HDF5, and review tools |

## ③ Current Settings and Task Success Criteria

- **Toaster:** In phase 0, correct loading must coincide with a new crossing of the activation threshold,
  normalized lever depression ≥0.90. Loading bread while holding the toaster lever down does not
  activate the cycle until the threshold is crossed again. Heating runs for 4 seconds after lowering
  has lasted at least 0.60 seconds, measured position is within <1.5 mm of the −45 mm commanded
  target, and measured speed is <0.01 m/s. The LED is ON in phase 1/2 and OFF in phase 0/3/4.
- **Rising:** The commanded target is interpolated to +35 mm over 0.80 seconds. Completion requires
  at least 0.92 seconds and measured position error <1.5 mm. The bread carriage velocity limit remains
  0.12 m/s, distinct from the new command trajectory's peak velocity of 0.15 m/s. Actual completion
  may take longer.
- **Heating evidence:** The system records IDs of slices correctly loaded at heating entry that
  continuously satisfy the loading check throughout heating. Removal/reinsertion or late insertion
  does not qualify for that cycle. Evidence is cleared on reset; restoring a legacy recording without
  per-slice evidence does not imply successful heating.
- **Bread-related success:** The same ID among `bread_0`–`bread_3` must satisfy both heating-completion
  and plate-placement criteria: geometry center at a plate-local XY radius <20 mm, the entire geometry
  at plate-local Z greater than −2 mm and less than 50 mm, orientation `abs(R[2,2])>0.94`, and linear
  speed <0.15 m/s. This is not a plate contact-force check.
- **Overall task success:** In addition to the bread criteria, the plate must be upright with
  `R[2,2]>0.985`, displaced by <25 mm from its initial XY position, and at environment-frame X>0.419 m.
  The cycle must be in phase 4 with the toaster lever returned, both wrists must have standby-position
  error <40 mm, and the existing gripper check <0.15 and absolute lift value <20 mm must hold.
  Bread-related success can hold without the remaining slices, but existing termination conditions,
  such as another slice falling, still apply separately.
- **Grippers:** Left/right master joint1 and slave joint2/3/4 all use stiffness and damping gains of
  100/4. The master joint velocity limit is 6.5 rad/s with effort 30; slave effort is 20, and slave
  velocity limits are inherited from the USD. The value 6.5 is a limit, not an achieved velocity.
  Do not use the retired `--gripper-slave-gains-official` option.
- **Quest:** The commands below use the practice profile with 1:1 translational/rotational target
  scaling. They retain the default home range of 0.55 m/120°, action correction limits of
  0.10 m per simulation second and 0.8 rad per simulation second, and target lead limits of
  0.12 m/45°. Actual robot tracking under VR control is distinct from input scaling and depends on
  IK, joint limits, contact, and simulation/render update periods.

Diagnostic JSON/JSONL, CSV, and RGB outputs are not training demonstrations. The optional `--record-dir`
HDF5 output stores `data/demo_*/{actions,obs,states,initial_state,processed_actions}` plus metadata and a
manifest snapshot, but is a diagnostic recording with **diagnostic=true, success=false**. Even though
it uses the existing recorder format, it must not be classified as validated successful demonstration
data for training. Action replay and saved-state video are also distinct; video playback alone does
not demonstrate successful physics replay. The examples below run teleoperation without recording.

## ④ System Requirements and Dependencies

A Linux desktop, NVIDIA GPU/drivers, NVIDIA Container Toolkit, Docker Compose v2, Git LFS, Python 3,
and host OpenSSL are required. GUI operation requires X11/Xauthority access. Quest and the PC must
be on a network that permits HTTPS connectivity.

| Dependency | Setup |
|---|---|
| Isaac Sim | The Docker build downloads `nvcr.io/nvidia/isaac-sim:5.1.0` |
| Isaac Lab and third_party | A v2.3.0-series source snapshot is tracked directly in Git. There are currently 0 gitlinks, so submodule update is a no-op |
| RoboDojo objects | Revision `63fcc045f2e974902eb7800d29de48004cf86016` is pinned in the manifest; the downloader verifies file size/SHA256 |
| New bread rack | Both `rack.usda` and its relative reference `bread_slot.usdz` are in LFS. The USDZ includes meshes; there are no separate textures |
| PackingTable and materials | `/Isaac/Props/PackingTable/packing_table.usd` and its references under the Isaac Sim asset cloud root. Cloud access or a user-configured asset root/cache is required |
| Python packages | Installed through the Dockerfile/constraints. Some optional packages have version ranges or unpinned versions, so full image reproducibility is not guaranteed |

No files need to be copied from other personal directories, but **this is not an offline package that
eliminates external asset downloads**. Detailed versions are listed in the
[dependency inventory](docs/toast_quest/DEPENDENCIES.md), and object sources are recorded in the
[asset manifest](source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/asset_manifest.json).

## ⑤ Clone, Submodules, LFS, and Installation

Run these commands only where the NVIDIA EULA is accepted (`ACCEPT_EULA=Y` in `docker/.env.base`).
Choose your clone location. `REPO` denotes the checkout root and must be set again in each new terminal.

```bash
git clone --branch toast-quest https://github.com/kkkkkmj/cyclo_lab.git cyclo_lab_toast_quest
cd cyclo_lab_toast_quest
export REPO="$PWD"
git lfs install
git submodule update --init
git lfs pull
python3 scripts/tools/download_make_toast_assets.py
docker compose --project-name cyclo_lab_mj --env-file docker/.env.base \
  -f docker/docker-compose.yaml -f docker/compose.mj.yaml --profile base build cyclo_lab
```

The original URL information in `.gitmodules` is preserved; do not replace the included sources with
upstream's latest main. `scripts/run_mj.sh` mounts this checkout at `/workspace/cyclo_lab` and prioritizes
its sources. It runs a separate transient container in the `cyclo_lab_mj` project rather than executing
inside the original container.

## ⑥ Inspect the Environment in the GUI

In a new terminal, replace the first line with your actual clone path. Set `DISPLAY` and `XAUTHORITY`
to match your desktop session. `:0`/`$HOME/.Xauthority` are example defaults and depend on your login
configuration.

```bash
export REPO=/path/to/cyclo_lab_toast_quest
cd "$REPO"
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery/manifest.json \
  --scenario_group operator_A_1 --group_index 1
```

Press R to reset the same initial object configuration. Check available GPU resources and run the
GUI and the Quest simulation below one at a time.

## ⑦ Quest Server and Robot Teleoperation

**Server terminal:** Set `REPO` to the clone path, `QUEST_HOST` to a PC LAN IP/hostname reachable from
Quest, and `QUEST_PORT` to an unused port. Allow this HTTPS connection through the PC firewall.

```bash
export REPO=/path/to/cyclo_lab_toast_quest
export QUEST_HOST=YOUR_PC_LAN_IP
export QUEST_PORT=8766
cd "$REPO"
python3 scripts/quest_diagnostic/server.py \
  --host "$QUEST_HOST" --port "$QUEST_PORT" \
  --bridge-dir "$REPO/logs/quest_toast_quest"
```

In Quest Browser, open the configured `https://<QUEST_HOST>:<QUEST_PORT>/`, confirm the certificate,
and Pair using the terminal PIN. The default certificate/private key is generated automatically under
`~/.local/state/cyclo-quest-tls`. To use your own certificate, append
`--cert /path/to/certificate --key /path/to/private_key` to the command above.
Keep private keys out of Git. Check the secure context, WebXR/immersive-vr, and client/server builds.

**Teleoperation terminal:** Close the GUI viewer before running the following commands. Keep the server
running. The server's host bridge and the container bridge below refer to the same directory.

```bash
export REPO=/path/to/cyclo_lab_toast_quest
cd "$REPO"
GROUP=operator_A_1
INDEX=1
bash scripts/run_mj.sh scripts/quest_diagnostic/teleop_toast.py \
  --headless --keep-open --enable-grippers --control-profile practice \
  --scenario_manifest scenario_delivery/manifest.json \
  --scenario_group "$GROUP" --group_index "$INDEX" \
  --bridge-dir /workspace/cyclo_lab/logs/quest_toast_quest \
  --position-scale 1 --rotation-scale 1
```

After entering VR, check status, fresh images, and input from both controllers, then release both squeeze
buttons to establish the reference. X (keyboard n) resets the same scenario and starts control; holding
squeeze controls that arm's target. The trigger controls the gripper (release to open, press to close),
and A (keyboard s) switches to WAITING. In the practice profile, releasing squeeze or receiving invalid
input/images aligns arm targets with measured poses, while grippers retain their last targets. This
does not imply an instantaneous stop of physical motion due to inertia. After input recovers, release
and re-engage squeeze. The preview provides four cameras—overview/head/left and right wrist—plus
status/HUD. Casting alignment and actual readability remain unverified.

See the [scenario guide](scenario_delivery/README.md) for group/index selection and layout diagrams.
