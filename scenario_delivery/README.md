# Toast Task — 100 Scenarios

## Overview

Current delivery: **[manifest.json](manifest.json)** — 100 fixed scenarios.

100 fixed object layouts for the humanoid toast task, with final poses for the toaster, plate, bread rack, and four bread slices. These layouts support demonstration collection across object-placement variations. They are placement data, not recorded demonstrations. Loading an ID selects a saved layout; reset restores it rather than sampling another one.

## Scenario Design

Coordinates use the environment frame: **+X is robot forward, +Y is robot left, and +Z is up**. Left-to-right order follows **+Y → −Y**. Positions are in **metres (m)** and quaternions use **wxyz** order. Camera screen directions can differ; cloned environments add their environment origins to these poses.

All six object orders are included:

| Object Order (Robot Left → Right) | Scenarios | A_1 | A_2 | B_1 | B_2 |
|---|---:|---:|---:|---:|---:|
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

Yaw variations are offsets from each object's existing reference orientation, about the environment +Z axis. The table describes the generation ranges; use the final poses stored in `manifest.json`, not newly sampled offsets. Yaw offsets in degrees are converted to radians and left-multiplied as world-Z quaternions. Z and scale are fixed. Exact reference Z values are 1.081800, 1.004222776 and 1.038200021 m for toaster, plate and rack respectively. The current reference heights/scales and four bread slices’ relative rack poses are preserved. The rack is the native 230 × 130 × 45 mm four-groove asset, at scale (1,1,1); plate scale is (1.5,1.5,0.22).


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
| Duplicates | Reject matching pose signatures within this delivery or the preserved fingerprints of the previous generation inputs |

The measured minimum inter-object gap in this delivery is about 138.99 mm. Initial geometric
non-intersection or contact within 1 mm does not establish stable PhysX support. Full robot reachability,
manipulation, collision-free paths and full-task success are not established by these filters.
The authored tabletop bounds are approximately X [0.341857712, 1.058142302],
Y [−1.318215319, 1.118215316] m, with top Z = 0.994051339 m. The exact support polygons
are in the manifest; the test requires containment of footprints expanded by 20 mm.
Toaster bounds include the LED. Bread-to-bread contact (distance ≤0) is also rejected.
Model probes cover grasp, insertion, extraction, lever and serving positions. Duplicate signatures
use positions rounded to 6 decimals and normalized quaternions to 7 decimals before SHA256 hashing.
The supplied delivery has 0 rejections and 0 previous-pose duplicates.

### Reference poses and bread placement

Baseline displacement is measured from the original environment poses below, separately from jitter
around the generation anchors above.

| Object | Environment baseline XYZ (m) |
|---|---|
| Toaster | (0.550, 0.230, 1.081800) |
| Plate | (0.430, 0.035, 1.004222776) |
| Bread Rack | (approximately 0.450, −0.250, 1.038200021) |

The four bread roots have these rack-local positions. Their common relative quaternion is
(0.7071067812, 0, 0.7071067812, 0), with scale (1,1,1).

| ID | Local X (m) | Local Y (m) | Local Z (m) |
|---|---:|---:|---:|
| bread_0 | 0.084392445 | 0.000249905 | 0.044351338865 |
| bread_1 | 0.024392445 | 0.000249905 | 0.044351338865 |
| bread_2 | −0.035607555 | 0.000249905 | 0.044351338865 |
| bread_3 | −0.095607555 | 0.000249905 | 0.044351338865 |

The rack baseline-to-new-pose rigid transform moves all four breads together, without independently
sampling them. Separate CPU/USD checks confirm identical rack-local poses and compare authored rack
triangles with bread convex geometry. Initial non-intersection/contact within 1 mm does not prove
stable support; settling was observed in the first layout and remains under diagnosis.

### Reproduction

The [generator](../scripts/tools/generate_current_toast_scenarios.py) and
[generation_config.json](generation_config.json) define the settings above. Use generation seed
**20261108** and assignment seed **20261109** (generation seed + 1).
After installation below, run from the checkout root using Python with numpy/scipy/torch/pxr:

```bash
export TOAST_PYTHON=python3
MJ_SCENARIO_OUTPUT=$(mktemp -d /tmp/toast-scenarios-rebuild.XXXXXX)
"$TOAST_PYTHON" scripts/tools/generate_current_toast_scenarios.py \
  --seed 20261108 \
  --evidence scenario_delivery/inputs/geometry_evidence.json \
  --output "$MJ_SCENARIO_OUTPUT"
"$TOAST_PYTHON" scripts/tools/test_current_toast_delivery.py
```

Existing delivery outputs are refused. Generation checks the current baseline/assets and saved geometry,
using prior pose-signature hashes from `inputs/generation_history.json` for duplicate exclusion.
The test command checks the supplied delivery, not the temporary regenerated output.
The saved manifest records generation-time +15 mm sources; current +35 mm sources and output changes
produce different provenance hashes. Pose/assignment reproduction is distinct from byte-for-byte file
reproduction. Historical manifest hashes remain unchanged; reviewed current source hashes are recorded
in [the provenance/relocation record](../docs/toast_quest/SCENARIO_RELOCATION.json).

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

<table>
  <thead>
    <tr><th>Operator</th><th>Group</th><th>Scenarios</th><th>Group index</th><th>Operator index</th><th>First scenario ID</th></tr>
  </thead>
  <tbody>
    <tr><td rowspan="2">operator_A</td><td>operator_A_1</td><td>25</td><td>1–25</td><td>1–25</td><td>toast_v20261108_097</td></tr>
    <tr><td>operator_A_2</td><td>25</td><td>1–25</td><td>26–50</td><td>toast_v20261108_087</td></tr>
    <tr><td rowspan="2">operator_B</td><td>operator_B_1</td><td>25</td><td>1–25</td><td>1–25</td><td>toast_v20261108_041</td></tr>
    <tr><td>operator_B_2</td><td>25</td><td>1–25</td><td>26–50</td><td>toast_v20261108_011</td></tr>
  </tbody>
</table>

Use the [assignment tables](ASSIGNMENTS.md) or
[assignments.csv](assignments.csv). Assignments are not inferred from odd/even
IDs or the first/last 50 IDs. IDs range from `toast_v20261108_000` to `toast_v20261108_099`.
`group_index` is 1-based within a group; `operator_index` is the same number for group 1 and that number
plus 25 for group 2. An ID suffix is not an assignment index.

Allocation keeps the six-order quotas in the design table. With the assignment seed fixed, up to
50,000 within-order group-label swaps balance standardized position/yaw offsets, their magnitudes,
reference/robot distances, second moments and quartile occupancy. Order types are interleaved within
each group's execution list. Distribution balance does **not** prove equal manipulation difficulty.
Features include signed ΔX/ΔY/Δyaw, absolute yaw, XY jitter magnitude, baseline displacement,
robot-origin 3D/XY distance, and the maximum probe-to-nearest-shoulder-lift-segment distance.
The centered feature matrix combines standardized values, squared values weighted 0.35, and
25/50/75% quartile exceedance indicators weighted 1.5. The objective is the sum of squared group
feature sums, with annealing temperature decreasing from 2 to a minimum of 0.01.
The stored score improves from 3655.088 to 670.205; shuffled order types are then interleaved.
See [distribution.json](distribution.json) for the actual statistics.

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
  --scenario_manifest scenario_delivery/manifest.json \
  --scenario_group "$GROUP" --group_index "$INDEX"
```

The program prints the selected operator, operator index and actual ID. Supply group/index together.
The compatible parent selection `--operator operator_A --scenario_index 26` selects the same ID as
`--scenario_group operator_A_2 --group_index 1`. Do not combine group, parent-operator or direct-ID modes.
For a direct ID, replace the group/index arguments with `--scenario_id toast_v20261108_087`.
The default manifest is now `scenario_delivery/manifest.json`; specifying it explicitly is also supported.

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
  --scenario_manifest scenario_delivery/manifest.json \
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
  --scenario_manifest scenario_delivery/manifest.json \
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
manifest = Path("scenario_delivery/manifest.json").resolve()
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
group/parent selections, 100 metadata round trips, 700 pose CSV rows, and 100 card entries.
These checks do not establish PhysX stability, robot reachability or full toast-task success.
The current rack's settling remains under diagnosis. Historical reports are linked from
[the reference index](../docs/toast_quest/DETAILS.md); they are not included in this scenario data folder.

## Files

| File | Purpose |
|---|---|
| [README.md](README.md) | Scenario design and loading instructions. |
| [manifest.json](manifest.json) | Fixed IDs and final poses, with generation/provenance information. |
| [assignments.csv](assignments.csv) | Operator/group assignments, both indices and object order. |
| [ASSIGNMENTS.md](ASSIGNMENTS.md) | Readable assignment table. |
| [poses.csv](poses.csv) | 700 object-pose rows; join to assignments by scenario_id. |
| [overview_cards.html](overview_cards.html) | Self-contained cards with all/A/B/four-group filters; default A_1. |

Download the card HTML and open it in a web browser. It is self-contained and does not need an internet
connection. GitHub's file view does not run it. Alternatively serve the checkout locally:

```bash
export REPO=/path/to/cyclo_lab_toast_quest
cd "$REPO"
python3 -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/scenario_delivery/overview_cards.html`.
These are static layout diagrams, not simulator images. Card rebuilding uses the compact
`inputs/table_frame.json` extracted from the original table snapshot; no private log path is required.
`inputs/geometry_evidence.json` supplies the generation geometry. `inputs/generation_history.json`
retains only prior pose-signature hashes and original input hashes needed for the same duplicate filter;
it is not an older scenario list. Reference generator source snapshots remain under `inputs/`.

The manifest's generation-time provenance is preserved verbatim. See [Reproduction](#reproduction)
for generation commands and [Scenario Design](#scenario-design) for ranges and constraints.
The card builder, `python3 scripts/tools/build_toast_overview_cards.py`, rebuilds the checked-in
card HTML from the supplied manifest and assets; it additionally requires Shapely 2.x.
