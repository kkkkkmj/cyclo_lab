# Toast Task — 100 Fixed-Base Scenarios

## Overview

This separate [manifest](manifest.json) contains 100 initial object configurations for collecting
manipulation demonstrations around **one fixed reference configuration**. All scenarios use
**Toaster → Plate → Bread Rack** from robot left to right. The original
[100 six-order scenarios](../scenario_delivery/README.md) and default manifest are unchanged.
These are placement data, not recorded demonstrations. Select an existing ID; reset restores it.

## Scenario Design

Coordinates use the environment frame: **+X is robot forward, +Y is robot left, and +Z is up**.
Left-to-right order follows **+Y → −Y**. Positions are in **metres (m)**, quaternions use
**wxyz** order, and yaw is in degrees about +Z. Cloned environments add their environment origins.

The current environment defaults already have the requested order, so they are used unchanged as
one common reference, rather than using individual layouts from the six-order delivery.
The generator checks these defaults against the current environment configuration.

| Object | Reference position (X, Y, Z), m | Reference quaternion (w, x, y, z) | Yaw | Scale |
|---|---|---|---:|---|
| Toaster | (0.55, 0.23, 1.0818) | (0.2588190451, 0, 0, 0.9659258263) | 150° | (1, 1, 1) |
| Plate | (0.43, 0.035, 1.004222776) | (1, 0, 0, 0) | 0° | (1.5, 1.5, 0.22) |
| Bread Rack | (0.44999998807907104, −0.25, 1.0382000207901) | (0.7071067690849304, 0, 0, −0.7071067690849304) | −90° | (1, 1, 1) |

Exact reference poses, including the four bread slices, are stored in
[generation_config.json](generation_config.json). Quaternions are normalized when applying offsets.
The rack is the current native 230 × 130 × 45 mm four-groove asset.

| Object | ΔX | ΔY | Δyaw |
|---|---|---|---|
| Toaster | [−0.02, +0.02] m | [−0.02, +0.02] m | [−5, +5]° |
| Plate | [−0.02, +0.02] m | [−0.02, +0.02] m | [−5, +5]° |
| Bread Rack | [−0.02, +0.02] m | [−0.02, +0.02] m | [−5, +5]° |

Each candidate independently samples all nine offsets uniformly from these ranges. XY offsets apply
in the environment frame; the yaw-offset quaternion left-multiplies the reference quaternion.
Offsets always start from the reference, never from the previous scenario. Z, roll, pitch and scale
are fixed. Invalid full configurations are rejected and resampled, so **accepted samples follow a
conditional distribution**, not an unconstrained uniform distribution.

### Generation and exclusion criteria

| Check | Applied condition |
|---|---|
| Table limits | Full containment in the authored tabletop support polygon: approximately X [0.341857712, 1.058142302], Y [−1.318215319, 1.118215316] m, top Z = 0.994051339 m |
| Object footprint | Current USD mesh/collider convex XY bounds with actual orientation and scale; main-object bounds expanded by 1 mm; rack and four breads combined |
| Object spacing | Strictly positive gap between toaster, plate and rack-with-bread footprints; no bread-to-bread XY overlap/contact |
| Order | Toaster Y > plate Y > rack Y in every accepted configuration |
| Plate | Environment-frame X >0.419 m, as required by the unchanged success predicate |
| Duplicates | Reject repeated pose signatures within this delivery and matches to the existing 100 layouts; separate ID prefix |

This set checks full support and non-overlap, without the six-order delivery's additional 20 mm
edge and 60 mm approach buffers. No existing generator criteria, physics or task tolerance is changed.
The unperturbed default plate extends outside the conservative support boundary; the reference itself
is therefore **not** an accepted static layout. Accepted plate offsets are on the +X side
(minimum about +10.125 mm). This is a consequence of rejection, not a shifted reference.

Of **364 candidates, 100 were accepted and 264 rejected**. All 264 rejected candidates failed plate
support containment; 70 also failed the plate X success condition (reason counts overlap).
No other rejection reason occurred. The minimum accepted inter-object gap is **8.301 mm**;
the minimum tabletop clearance beyond the 1 mm-expanded footprint is **0.0222 mm**.
These small clearances do not establish dynamic stability or sufficient manipulation clearance.
Exact checks and rejection counts are in `manifest.json` under `static_validation`.

### Reference poses and bread placement

The rack-to-world rigid transform moves all four bread slices together, with no independent bread
noise. Rack-local bread positions and orientations remain those of the current environment:

| ID | Local X (m) | Local Y (m) | Local Z (m) |
|---|---:|---:|---:|
| bread_0 | 0.084392445 | 0.000249905 | 0.044351338865 |
| bread_1 | 0.024392445 | 0.000249905 | 0.044351338865 |
| bread_2 | −0.035607555 | 0.000249905 | 0.044351338865 |
| bread_3 | −0.095607555 | 0.000249905 | 0.044351338865 |

Their common rack-relative quaternion is approximately (0.7071067812, 0, 0.7071067812, 0), with unit
scale. The toaster lever, bread carriage and LED retain their existing body-relative relationships;
only the toaster root pose changes. The rack's known settling issue remains unresolved.

### Reproduction

Generation seed: **20261109**. Assignment seed: **20261110**. The
[generator](../scripts/tools/generate_base_toast_scenarios.py) refuses a nonempty output directory.
Run from the checkout root with Python containing numpy, scipy, torch, pxr (USD), and Shapely 2.x:

```bash
export TOAST_PYTHON=python3
MJ_BASE_OUTPUT=$(mktemp -d /tmp/toast-base-rebuild.XXXXXX)
"$TOAST_PYTHON" scripts/tools/generate_base_toast_scenarios.py \
  --seed 20261109 --assignment-seed 20261110 --output "$MJ_BASE_OUTPUT"
"$TOAST_PYTHON" scripts/tools/test_base_toast_delivery.py
```

The CPU reproduction used Python 3.12.14, numpy 2.5.1, scipy 1.17.0, torch 2.11.0+cu128,
USD 0.25.5 and Shapely 2.1.2. All nine generated files matched byte-for-byte in a separate temporary
folder in that environment; other library versions may change geometry serialization or allocation
roundoff. This CPU environment is separate from the simulator environment below.
The test command checks the checked-in delivery, not the temporary output.

Generation reads the original delivery's baseline, geometry evidence and duplicate signatures,
all tracked in this branch. It uses current asset geometry and shared tools under `scripts/tools/`;
no personal directory or untracked file is required. Current source/asset hashes are recorded in the
manifest. The two files in `inputs/` retain the authored geometry evidence and table snapshot.

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

**operator_A and operator_B each have 50 scenarios**, split into two groups of 25.
All groups use the same fixed Toaster → Plate → Bread Rack order.

<table>
  <thead><tr><th>Operator</th><th>Group</th><th>Scenarios</th><th>Group index</th><th>Operator index</th><th>First scenario ID</th></tr></thead>
  <tbody>
    <tr><td rowspan="2">operator_A</td><td>operator_A_1</td><td>25</td><td>1–25</td><td>1–25</td><td>toast_base_20261109_022</td></tr>
    <tr><td>operator_A_2</td><td>25</td><td>1–25</td><td>26–50</td><td>toast_base_20261109_019</td></tr>
    <tr><td rowspan="2">operator_B</td><td>operator_B_1</td><td>25</td><td>1–25</td><td>1–25</td><td>toast_base_20261109_025</td></tr>
    <tr><td>operator_B_2</td><td>25</td><td>1–25</td><td>26–50</td><td>toast_base_20261109_002</td></tr>
  </tbody>
</table>

IDs run from `toast_base_20261109_000` through `toast_base_20261109_099` and do not overlap the original
set. An ID suffix is not an assignment index. `group_index` is 1–25; `operator_index` is that number
for group 1 and that number +25 for group 2. See [ASSIGNMENTS.md](ASSIGNMENTS.md) and
[assignments.csv](assignments.csv).

Allocation starts with seeded 25-per-group labels and attempts 50,000 quota-preserving label swaps.
It balances standardized signed ΔX/ΔY/Δyaw, second moments weighted 0.35, and 25/50/75% quartile
exceedance indicators weighted 1.5. The objective is the sum of squared centered group feature sums;
annealing temperature decreases from 2 to 0.01. The score improves from 1630.466 to 133.343.
This balances the accepted distribution across groups; it does not remove the support-induced plate
+X bias or guarantee equal manipulation difficulty. Poses are not modified during assignment.

Mean offsets below use **mm, mm, degrees** for each (ΔX, ΔY, Δyaw) triple.
[distribution.json](distribution.json) also records per-group minima, maxima, standard deviations and quartiles.

| Group | Count | Toaster mean offsets | Plate mean offsets | Bread Rack mean offsets |
|---|---:|---|---|---|
| operator_A_1 | 25 | (-0.945, -0.006, -0.004) | (14.928, 0.240, -0.115) | (0.403, 0.650, 0.034) |
| operator_A_2 | 25 | (-1.144, -0.132, -0.128) | (14.999, 0.012, -0.235) | (0.601, -0.237, -0.275) |
| operator_B_1 | 25 | (-0.833, -0.307, -0.083) | (14.857, 0.114, 0.054) | (0.426, -0.238, -0.353) |
| operator_B_2 | 25 | (-0.510, -0.540, 0.060) | (15.068, -0.454, -0.264) | (0.853, 0.073, -0.350) |

## Load a Scenario

After setup, set your clone path and desktop session's DISPLAY/XAUTHORITY in each new terminal.
Run one viewer at a time, closing it before selecting another group:

```bash
export REPO=/path/to/cyclo_lab_toast_quest
cd "$REPO"
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

# A_1, first scenario
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery_base/manifest.json \
  --scenario_group operator_A_1 --group_index 1

# A_2, first scenario
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery_base/manifest.json \
  --scenario_group operator_A_2 --group_index 1

# B_1, first scenario: toast_base_20261109_025
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery_base/manifest.json \
  --scenario_group operator_B_1 --group_index 1

# B_2, first scenario
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery_base/manifest.json \
  --scenario_group operator_B_2 --group_index 1
```

Use group indices 1–25. Parent selection remains compatible: `--operator operator_A --scenario_index 26`
selects A_2/index 1. Replace group/index with `--scenario_id toast_base_20261109_025` for direct selection;
do not combine selection modes. Always specify the new manifest: the default remains
`scenario_delivery/manifest.json`. IDs are resolved only within the selected manifest.
Press R to restore the same layout; physics can move objects after reset.

### Quest selection and operation

In the server terminal, replace the clone path and `YOUR_PC_LAN_IP`; use an available HTTPS port:

```bash
export REPO=/path/to/cyclo_lab_toast_quest
export QUEST_HOST=YOUR_PC_LAN_IP
export QUEST_PORT=8766
cd "$REPO"
python3 scripts/quest_diagnostic/server.py \
  --host "$QUEST_HOST" --port "$QUEST_PORT" \
  --bridge-dir "$REPO/logs/quest_toast_base"
```

Open `https://<QUEST_HOST>:<QUEST_PORT>/` in Quest Browser, confirm the certificate and Pair with the
terminal PIN. Certificates are generated under `~/.local/state/cyclo-quest-tls`; optional
`--cert /path/to/certificate --key /path/to/private_key` selects your own. Keep private keys out of Git.
After closing the GUI viewer, run the simulator in a second terminal:

```bash
export REPO=/path/to/cyclo_lab_toast_quest
cd "$REPO"
bash scripts/run_mj.sh scripts/quest_diagnostic/teleop_toast.py \
  --headless --keep-open --enable-grippers --control-profile practice \
  --scenario_manifest scenario_delivery_base/manifest.json \
  --scenario_group operator_B_1 --group_index 1 \
  --bridge-dir /workspace/cyclo_lab/logs/quest_toast_base \
  --position-scale 1 --rotation-scale 1
```

This selects `toast_base_20261109_025`. Change the group to any of the four names and index to 1–25.
The server and container bridge directories refer to the same checkout mount. Enter VR, check fresh
camera images and both controller states, release both squeeze buttons, then press X (keyboard n)
to reset/start. Squeeze controls that arm's target; trigger controls the gripper. A (keyboard s)
returns to WAITING. Position/rotation scales of 1 describe target scaling, not actual robot tracking.

## Using the Scenarios for Data Collection

The task remains `Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2`. These commands do not record
demonstrations. Optional Quest `--record-dir` writes diagnostic HDF5 with **diagnostic=true,
success=false**, group/parent indices, selected ID, manifest hash and snapshot. This is not validated
successful imitation-learning demonstration data. See [Changes](../CHANGES.md) for the control and
recording distinctions. No physical settings or task success criteria are changed by this delivery.

## Validation

CPU checks cover 100 unique IDs, all nine offset bounds and fixed object order, four groups of 25,
A/B totals of 50, 700 pose CSV rows, rigid rack-relative bread poses, and all group/parent selections.
Current asset bounds pass static support/non-overlap checks. At every plate pose, a constructed
terminal-state fixture can satisfy the existing success predicate's placement checks; this does not
establish a feasible robot trajectory or a successful task execution.

Cards are generated through the shared current USD/configuration projection path. Their IDs,
assignments, poses and asset hashes are checked against the manifest and current files; projected
outer hulls are checked against transformed current mesh vertices, accounting only for display
simplification/rounding. The historical cards were also audited: their asset hashes match current assets and their outer
hulls agree with current mesh projections within 1.58 micrometres. This audit does not establish
identical internal SVG paths or explain every previously observed visual difference. Historical cards
remain unchanged; the new cards are generated afresh from current assets.
These diagrams are not simulator renders or collision meshes. A headless Chrome check could not
start because the sandbox denied an operation; browser rendering and interaction remain unverified
for this generated file.

**PhysX, GUI and VR runtime validation has not been performed for this set.** Rack settling remains
unresolved. Robot reachability, collision-free manipulation, dynamic support and full-task success
are unverified. Rejection filters and balanced assignments must not be interpreted as such validation.

## Files

| File | Purpose |
|---|---|
| [README.md](README.md) | Design, reproduction and selection instructions |
| [manifest.json](manifest.json) | 100 saved layouts, checks and source/asset provenance |
| [assignments.csv](assignments.csv) / [ASSIGNMENTS.md](ASSIGNMENTS.md) | Four-group and parent assignments with both indices |
| [poses.csv](poses.csv) | 700 object poses, keyed by scenario_id and object |
| [generation_config.json](generation_config.json) | One reference configuration, ranges, seeds and allocation settings |
| [distribution.json](distribution.json) | Group variation statistics |
| [overview_cards.html](overview_cards.html) | Self-contained layout cards with all/A/B/four-group filters |
| [inputs/geometry_evidence.json](inputs/geometry_evidence.json) | Authored support geometry used for generation |
| [inputs/table_frame.json](inputs/table_frame.json) | Authored table snapshot used for cards |

Download and open the card HTML directly, or serve the checkout:

```bash
export REPO=/path/to/cyclo_lab_toast_quest
cd "$REPO"
python3 -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/scenario_delivery_base/overview_cards.html`.
To rebuild only these cards from the saved manifest and current assets:

```bash
python3 scripts/tools/build_toast_overview_cards.py \
  --delivery scenario_delivery_base \
  --table-source scenario_delivery_base/inputs/table_frame.json
```
