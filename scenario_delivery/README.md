# Toast Task — 100 Scenarios

## Overview

Current delivery: **[v20261108_current_100](v20261108_current_100/README.md)**. Use its manifest explicitly.

100 fixed object layouts for the humanoid toast task, with final poses for the toaster, plate, bread rack, and four bread slices. These are placement data, not recorded demonstrations. Loading an ID selects a saved layout; reset restores it rather than sampling another one.

## Scenario Design

Coordinates use the environment frame: **+X is robot forward, +Y is robot left, and +Z is up**. Left-to-right order follows **+Y → −Y**. Positions are in **metres (m)** and quaternions use **wxyz** order.

All six object orders are included:

| Object Order (Robot Left → Right) | Scenarios | A_1 | A_2 | B_1 | B_2 |
|---|---:|---:|---:|---:|---:|---:|
| Toaster → Plate → Bread Rack | 17 | 5 | 4 | 4 | 4 |
| Toaster → Bread Rack → Plate | 17 | 4 | 4 | 5 | 4 |
| Plate → Toaster → Bread Rack | 17 | 4 | 5 | 4 | 4 |
| Plate → Bread Rack → Toaster | 17 | 4 | 4 | 4 | 5 |
| Bread Rack → Toaster → Plate | 16 | 4 | 4 | 4 | 4 |
| Bread Rack → Plate → Toaster | 16 | 4 | 4 | 4 | 4 |
| **Total** | **100** | **25** | **25** | **25** | **25** |

The nominal Y position, `Y_slot`, is **+0.40, 0, or −0.40 m**, according to the object's left, centre, or right slot.

| Object | Nominal position (X, Y, Z), m | X variation | Y variation | Reference yaw | Yaw variation |
|---|---|---|---|---|---|
| Toaster | (0.550, Y_slot, 1.081800) | ±0.015 m | ±0.015 m | 150° | ±5° |
| Plate | (0.490, Y_slot, 1.004223) | ±0.010 m | ±0.015 m | 0° | ±5° |
| Bread Rack | (0.460, Y_slot, 1.038200) | ±0.015 m | ±0.015 m | −90° | ±5° |

Yaw variations are offsets from each object's existing reference orientation, about the environment +Z axis. The table describes the generation ranges; use the final poses stored in `manifest.json`, not newly sampled offsets. Heights are rounded here for readability. The current reference heights/scales and four bread slices’ relative rack poses are preserved. The rack is the native 230 × 130 × 45 mm four-groove asset, at scale (1,1,1); plate scale is (1.5,1.5,0.22).


### Generation and exclusion criteria

The generator uses per-order Latin hypercube samples over the nine X/Y/yaw offsets, with rejection
sampling when a candidate fails. Generation seed is **20261108**; assignment seed is **20261109**.
The supplied 100 candidates were accepted without resampling. Do not regenerate or reassign them to select a scenario.

| Check | Applied condition |
|---|---|
| Table limits | Planning envelope X [0.318999970, 1.081000007], Y [−1.336823260, 1.136823257] m, with 20 mm edge margin; also containment within the extracted authored tabletop support polygon |
| Object footprint | Conservative convex XY bounds from current USD meshes, expanded by 1 mm for the main objects; rack and all four breads treated as a combined footprint |
| Object spacing | At least 60 mm between toaster/plate/rack-with-bread footprints. This approach margin is stricter than the 30 mm collision-gap setting |
| Bread placement | Four breads move rigidly with the rack; reject bread-to-bread XY overlap. Separate CPU/USD checks compare bread convex geometry with authored rack triangles |
| Plate | Environment-frame X >0.419 m |
| Model distance filter | Reject probe points outside both arms’ conservative chain-length bounds from the shoulder lift segment. This is not IK or collision-aware reachability validation |
| Duplicates | Reject matching pose signatures within this delivery or the previous two manifests |

The measured minimum inter-object gap in this delivery is about 138.99 mm. Initial geometric
non-intersection or contact within 1 mm does not establish stable PhysX support. Full robot reachability,
manipulation, collision-free paths and full-task success are not established by these filters.
Exact baseline coordinates, bread offsets, support polygon, units and reproducible generation commands
are in [Scenario Design](v20261108_current_100/SCENARIO_DESIGN.md) and
[generation_config.json](v20261108_current_100/generation_config.json).

## Download and Setup

Clone the full branch, not only `scenario_delivery`:

```bash
git clone --branch toast-quest --single-branch \
  https://github.com/kkkkkmj/cyclo_lab.git cyclo_lab_toast_quest
cd cyclo_lab_toast_quest
export REPO="$PWD"
git lfs install
git submodule update --init
git lfs pull
python3 scripts/tools/download_make_toast_assets.py
docker compose --project-name cyclo_lab_mj --env-file docker/.env.base \
  -f docker/docker-compose.yaml -f docker/compose.mj.yaml --profile base build cyclo_lab
```

This branch includes its third-party sources as regular tracked directories. No additional submodule
checkout is required for those directories; the submodule command above is currently a no-op.
Do not replace them with newer upstream versions.

The repository targets **Isaac Sim 5.1.0, Isaac Lab 2.3.0, and Python 3.11**. Docker setup requires
Docker Compose v2, NVIDIA Container Toolkit, a supported NVIDIA GPU and drivers. GUI viewing requires
an active display and X11 authorization (`DISPLAY` and `XAUTHORITY`). The host Quest server needs Python 3
and OpenSSL. See [Changes](../CHANGES.md) for dependencies, certificates and the complete control procedure.

The [asset downloader](../scripts/tools/download_make_toast_assets.py) downloads checksum-pinned toast
objects and the plate. The new rack wrapper/USDZ are in LFS. The NVIDIA packing-table asset and its
materials must be accessible through Isaac Sim's cloud asset root or a configured local cache.
The helper `scripts/run_mj.sh` mounts **this checkout** at `/workspace/cyclo_lab` and runs a separate
`cyclo_lab_mj` Compose project. It does not enter or stop the original container.

## Operator Assignments

**operator_A and operator_B each have 50 scenarios.** A/B identify people responsible for collection,
not VR or automatic generation methods. Each operator has two groups of 25 scenarios.

| Operator | Group | Scenarios | Group index | Operator index | First scenario ID |
|---|---|---:|---|---|---|
| operator_A | operator_A_1 | 25 | 1–25 | 1–25 | toast_v20261108_097 |
| operator_A | operator_A_2 | 25 | 1–25 | 26–50 | toast_v20261108_087 |
| operator_B | operator_B_1 | 25 | 1–25 | 1–25 | toast_v20261108_041 |
| operator_B | operator_B_2 | 25 | 1–25 | 26–50 | toast_v20261108_011 |

Use the [assignment tables](v20261108_current_100/ASSIGNMENTS.md) or
[assignments.csv](v20261108_current_100/assignments.csv). Assignments are not inferred from odd/even
IDs or the first/last 50 IDs. IDs range from `toast_v20261108_000` to `toast_v20261108_099`.
`group_index` is 1-based within a group; `operator_index` is the same number for group 1 and that number
plus 25 for group 2. An ID suffix is not an assignment index.

Allocation keeps the six-order quotas in the design table. With the assignment seed fixed, up to
50,000 within-order group-label swaps balance standardized position/yaw offsets, their magnitudes,
reference/robot distances, second moments and quartile occupancy. Order types are interleaved within
each group's execution list. Distribution balance does **not** prove equal manipulation difficulty.
See [distribution.json](v20261108_current_100/distribution.json) for the actual statistics.

## Load a Scenario

Run these host commands after setup. In each new terminal, set `REPO` to the actual clone path.
Use your desktop session's `DISPLAY` and `XAUTHORITY`; `:0` and `$HOME/.Xauthority` are example defaults.
Change GROUP to any of the four names above and INDEX to 1–25.

```bash
export REPO=/path/to/cyclo_lab_toast_quest
cd "$REPO"
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
GROUP=operator_A_1
INDEX=1
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group "$GROUP" --group_index "$INDEX"
```

The program prints the selected operator, operator index and actual ID. Supply group/index together.
The compatible parent selection `--operator operator_A --scenario_index 26` selects the same ID as
`--scenario_group operator_A_2 --group_index 1`. Do not combine group, parent-operator or direct-ID modes.
For a direct ID, replace the group/index arguments with `--scenario_id toast_v20261108_087`.
Always retain the current `--scenario_manifest`: omitting it preserves the older default delivery.

Focus the simulation window and press **R** to restore the selected initial layout. Reset does not
advance to another scenario. Objects can settle under physics after reset. Close the window to exit;
start a new environment to select another scenario. The viewer holds the arms with open grippers
and lift at zero, without deliberately disturbing objects.

### Quest selection and operation

Use an unused HTTPS port and a PC address reachable from Quest. Set REPO/QUEST_HOST/QUEST_PORT to
your own values. Keep this server terminal running:

```bash
export REPO=/path/to/cyclo_lab_toast_quest
export QUEST_HOST=YOUR_PC_LAN_IP
export QUEST_PORT=8766
cd "$REPO"
python3 scripts/quest_diagnostic/server.py \
  --host "$QUEST_HOST" --port "$QUEST_PORT" \
  --bridge-dir "$REPO/logs/quest_toast_quest"
```

Open `https://<QUEST_HOST>:<QUEST_PORT>/` in Quest Browser, confirm the certificate and Pair using the
terminal PIN. Certificates are generated under `~/.local/state/cyclo-quest-tls`; to use your own,
append `--cert /path/to/certificate --key /path/to/private_key`. Keep private keys out of Git.
After closing the GUI viewer, run one simulator in a second terminal:

```bash
export REPO=/path/to/cyclo_lab_toast_quest
cd "$REPO"
GROUP=operator_B_2
INDEX=1
bash scripts/run_mj.sh scripts/quest_diagnostic/teleop_toast.py \
  --headless --keep-open --enable-grippers --control-profile practice \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group "$GROUP" --group_index "$INDEX" \
  --bridge-dir /workspace/cyclo_lab/logs/quest_toast_quest \
  --position-scale 1 --rotation-scale 1
```

This example selects `toast_v20261108_011`. The server and simulator share the same bridge through
the checkout mount. Enter VR, check fresh camera images and both controller states, release both
squeeze buttons, then press X (keyboard n) to reset/start. Squeeze controls that arm's target;
trigger controls its gripper. A (keyboard s) returns to WAITING. These commands do not enable recording.
The 1:1 position/rotation settings are target scales, not measured tracking speed.

### Optional Headless Check

After checking GPU availability, a finite check can exercise initial placement and two resets:

```bash
export REPO=/path/to/cyclo_lab_toast_quest
cd "$REPO"
bash scripts/run_mj.sh scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_A_1 --group_index 1 \
  --headless --steps 150 --reset_every 50
```

Successful pose checks print `RESET_POSES_OK`; a completed finite run prints `VIEW_COMPLETE`.
This is not a full-task test.

## Using the Scenarios for Data Collection

This package provides fixed layouts and code to apply them. The viewer is for scene inspection and
does not save demonstrations. Selecting an operator or group does not start data collection.
The Quest task ID is `Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2`; `toast-quest` is the Git branch name.

For custom collection code, set the selected ID and manifest **before `gym.make()`**, after initializing
Isaac Sim and registering the task:

```python
from pathlib import Path
import gymnasium as gym
from isaaclab_tasks.utils.parse_cfg import parse_env_cfg

# Run from the repository root. Use the ID from the assignment table.
scenario_id = "toast_v20261108_097"
manifest = Path("scenario_delivery/v20261108_current_100/manifest.json").resolve()
task = "Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2"
cfg = parse_env_cfg(task, device="cuda:0", num_envs=1)
cfg.scenario_id = scenario_id
cfg.scenario_manifest = str(manifest)
env = gym.make(task, cfg=cfg)
```

This is an integration example, not a claim that every recorder accepts these CLI options.
Existing group selection resolves operator/scenario_index for the Quest recorder and stores the group,
group index, parent index, actual ID and manifest SHA256. Optional Quest `--record-dir` produces
**diagnostic=true, success=false** HDF5 with metadata and a manifest snapshot; it is not a verified
successful training demonstration. Saved-state video also does not establish action-replay fidelity.

## Validation

The supplied 100 IDs are unique, with 25 per group and 50 per operator. CPU checks matched all 200
group/parent selections, 100 metadata round trips, 700 pose CSV rows, and 100 card/SVG entries.
These checks do not establish PhysX stability, robot reachability or full toast-task success.
The current rack's settling remains under diagnosis. Detailed reports and original results remain in
[the reference index](../docs/toast_quest/DETAILS.md) and the version folder; they are not rerun by opening a layout.

## Files

| File | Purpose |
|---|---|
| [README.md](README.md) | Scenario design and loading instructions. |
| [manifest.json](v20261108_current_100/manifest.json) | Fixed IDs and final poses, with generation/provenance information. |
| [assignments.csv](v20261108_current_100/assignments.csv) | Operator/group assignments, both indices and object order. |
| [ASSIGNMENTS.md](v20261108_current_100/ASSIGNMENTS.md) | Readable assignment table. |
| [poses.csv](v20261108_current_100/poses.csv) | 700 object-pose rows; join to assignments by scenario_id. |
| [overview_cards.html](v20261108_current_100/overview_cards.html) | Self-contained cards with all/A/B/four-group filters; default A_1. |
| [overview.svg](v20261108_current_100/overview.svg) | All 100 layouts, ordered by group/index. |
| [SCENARIO_DESIGN.md](v20261108_current_100/SCENARIO_DESIGN.md) | Exact ranges, criteria, seeds and generation instructions. |

Download the card HTML and open it in a web browser. It is self-contained and does not need an internet
connection. GitHub's file view does not run it. Alternatively serve the checkout locally:

```bash
export REPO=/path/to/cyclo_lab_toast_quest
cd "$REPO"
python3 -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/scenario_delivery/v20261108_current_100/overview_cards.html`.
These are static layout diagrams, not simulator images. Rebuilding the card HTML with its separate
builder requires a historical `collision_geometry.json` snapshot excluded from Git; viewing the supplied
HTML does not. This is separate from regenerating scenario poses.

Previous [manifest.json](manifest.json), [rack-adjusted manifest](manifest_bread_slot.json),
[A/B assignments](assignments.csv), [assignment table](ASSIGNMENTS.md) and [preview](preview.html)
remain available as the historical `batch02_toast_*` delivery. Their A/B assignments have not been
renamed into current subgroups. [Original delivery notes](../docs/toast_quest/history/SCENARIOS_BATCH02.md)
retain the earlier execution records.
