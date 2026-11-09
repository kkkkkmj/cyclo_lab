> Archived guidance/generation record. For current shared instructions, see [Changes](../../../CHANGES.md) and the [current scenarios](../../../scenario_delivery/README.md). Personal paths and execution results below are historical records, not current settings.

# 100 New Scenarios for the Current Toast Environment — v20261108_current_100

The version name uses the generation start date. Existing `scenario_delivery` manifest/assignments were preserved, and an independent set of 100 was generated in this subfolder. The new list requires **explicit manifest selection**. The default list remains the existing one.

## Evidence and Previous Method

The requested GitHub branch/raw resources were inaccessible (cache miss), so remote/local identity could not be confirmed. Evidence came from local `scenario_delivery/{manifest.json,manifest_bread_slot.json,assignments.csv}` and the previous generator/geometry helpers under `/home/mj/nrf_humanoid/toast_minimal_c73kwi_y/files/scripts/tools/`. Those reference tools were preserved in `inputs/reference_*.py`.

The previous method used 6 permutations of toaster / plate / bread_shelf along +Y to −Y, with 17/17/17/17/16/16 scenarios, seed 20261102, and alternating A/B assignments within each type. There were no subgroups. X anchors: toaster .55 m, plate .49 m, rack .46 m; Y anchors +.4/0/−.4 m. X variation: toaster/rack ±15 mm, plate ±10 mm; all Y variations ±15 mm; yaw ±5° around toaster 150°/plate 0°/rack −90°. Z retains the current reference configuration.

Previous exclusion criteria: 20 mm table-edge margin, 1 mm geometry/metadata uncertainty margin, 30 mm collision gap, 60 mm approach gap, plate X>.419 m, duplicate exclusion, and a distance-bound filter based on robot link lengths. The link-length filter is not IK/robot-collision/grasp validation.

New generation uses seed **20261108**, assignment seed **20261109**, and per-type Latin hypercube sampling followed by validation and assignment. All 100 poses are new, with no duplicates in either previous manifest. Actual USD checks of the native 230×130×45 mm rack and four slices allowed the existing ranges/exclusion margins to be retained. For this seed, all 100 candidates passed, with 0 retries/rejections. Invalid candidates are rejected/resampled without relaxing criteria.

## Stored Files

- `manifest.json`: 100 IDs, parent operator/group/both indices, poses/scales for all 7 objects (toaster, plate, bread_shelf, bread_0–3), geometry checks, and source/asset SHA256.
- `poses.csv`: all 700 initial object poses; quaternion wxyz, distances in m.
- `assignments.csv`, [ASSIGNMENTS.md](https://github.com/kkkkkmj/cyclo_lab/blob/a18eb900aea6d6110dedb45f3f616411f7750c42/scenario_delivery/v20261108_current_100/ASSIGNMENTS.md): full assignments. Group 1 uses parent indices 1–25; group 2 uses 26–50. Matching indices in the old list do not imply matching layouts.
- [Current card layouts](../../../scenario_delivery/overview_cards.html): 100 static layout diagrams, not simulator screenshots.
- `generation_config.json`: seeds, ranges, per-type quotas, and distribution-balancing method.
- `distribution.json`: min/max/mean/std/p25/median/p75 for all position/rotation/distance metrics per group and A/B.
- `validation.json`, `cpu_tests.log`, `reproducibility.json`: static checks, CPU tests, and byte-for-byte reproduction of 8 generated outputs.
- `inputs/geometry_evidence.json`: previously extracted table-support polygons/robot-link model. Current robot USD SHA256 was matched. Historical FK-validation flags were reused, not treated as FK/PhysX validation in this run.

## Assignments by Type

Order is +Y → −Y, with S=bread_shelf, T=toaster, P=plate.

| Type | A_1 | A_2 | B_1 | B_2 | A | B | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| T > P > S | 5 | 4 | 4 | 4 | 9 | 8 | 17 |
| T > S > P | 4 | 4 | 5 | 4 | 8 | 9 | 17 |
| P > T > S | 4 | 5 | 4 | 4 | 9 | 8 | 17 |
| P > S > T | 4 | 4 | 4 | 5 | 8 | 9 | 17 |
| S > T > P | 4 | 4 | 4 | 4 | 8 | 8 | 16 |
| S > P > T | 4 | 4 | 4 | 4 | 8 | 8 | 16 |
| Total | 25 | 25 | 25 | 25 | 50 | 50 | 100 |

Per-type A/B differences ≤1 and A_1/A_2 and B_1/B_2 differences ≤1 are fixed. With 50,000 seeded within-type swaps, standardized mean/second-moment/quartile-occupancy deviations were reduced jointly for signed XY offsets, magnitudes, yaw/absolute yaw, reference displacement, robot-origin distance, and task-probe–shoulder distance. Group execution lists interleave types. This is **layout-distribution balance**, not verified equivalence of manipulation difficulty.

| Group | Mean XY jitter T/P/S (mm) | Mean absolute yaw offset T/P/S (°) | Mean maximum probe–shoulder distance (m) |
|---|---|---|---:|
| operator_A_1 | 11.45/9.55/11.40 | 2.46/2.46/2.63 | 0.6229 |
| operator_A_2 | 11.73/9.14/11.21 | 2.57/2.54/2.46 | 0.6191 |
| operator_B_1 | 11.60/9.66/11.55 | 2.47/2.45/2.49 | 0.6234 |
| operator_B_2 | 11.16/9.75/11.24 | 2.45/2.58/2.45 | 0.6215 |

See `distribution.json` for full distance/displacement distributions. Robot origin is scene-local (0,0,0); the shoulder metric is minimum distance to the lift-axis segment. Probe filtering expanded from bread 0/1 to all four slices without forcing a particular task-target slice. Insertion probes alternately sample slots for an upper-bound check, not proof of feasibility for every path.

## Current Environment and Placement/Reset Validation Scope

Source inspection matched the requested settings: rack.usda 230×130×45 mm and current four-groove bread offsets, any correctly loaded slice + 90% lever crossing, 4 seconds after lowering, phase1/2 LED ON, at least one fully heated same-ID slice on the plate, center radius 20 mm, master/slave 100/4, master 6.5 rad/s. Task/assets/VR input/joint settings were unchanged. This is configuration validation, not PhysX readback.

The rack rigid transform moves all four bread poses together. The loader validates relative poses for all 100 and applies them to scene.init_state. `reset_objects` adds env origin to default_root_state. Actual reset function bodies run with CPU tensors and mocked write APIs to test full/partial environment resets. The static rack retains its spawn pose. Plate success checks use default_root_state generated from the scenario plate pose, keeping the reference position consistent.

Conservative XY hulls of current USD visuals/colliders and rack+four-bread outlines were checked for 20 mm table clearance and 60 mm inter-object clearance. Minimum gap among 100 scenarios: **138.99 mm**. Actual fixed-rack collision triangles and bread convex colliders verify no initial penetration and contact within 1 mm descent. Identical rack-local bread poses across scenarios preserve this relation. Settling/contact stability under gravity remain unverified in actual simulation.

Docker API socket permission denied and `nvidia-smi` driver communication failure prevented PhysX/GUI/Quest execution, rendering, actual reset/grasp/full-task-success validation in this session. Existing processes were not stopped/restarted. Compose resolution confirmed host cyclo_lab_mj → `/workspace/cyclo_lab` mounting and modified-source-first PYTHONPATH. The container path cyclo_lab is the modified checkout's mount destination, not the original repository.

CPU results: **6** new-delivery tests, **8** existing scenario-selection/loader tests, **6** existing recording-metadata tests; **20 passed** total. New tests iterate over all 100 scenarios. Detailed runtime environment/check distinctions are stored in `verification_report.json`.

## Regeneration and CPU Tests

The generator refuses existing output files to avoid overwriting saved artifacts. The following generates into a new temporary folder. Byte identity of 8 generated files was confirmed with the same sources/assets/inputs and Python/numpy/scipy/USD environment (`reproducibility.json`).

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
MJ_SCENARIO_OUTPUT=$(mktemp -d /tmp/toast-scenarios-rebuild.XXXXXX)
/home/mj/hand-sim-conda/bin/python scripts/tools/generate_current_toast_scenarios.py --output "$MJ_SCENARIO_OUTPUT"
/home/mj/hand-sim-conda/bin/python -m unittest discover -s scripts/tools -p 'test_current_toast_delivery.py' -v
python3 -m unittest discover -s scripts/tools -p 'test_toast_scenario_runtime.py'
python3 -m unittest discover -s scripts/tools -p 'test_toast_recording_metadata.py'
```

## GUI: First Configuration in Each Group

Existing-list selection still uses e.g. `--operator operator_A --scenario_index 1`. The new list requires the manifest below. Within it, `--operator operator_A --scenario_index 26` equals `--scenario_group operator_A_2 --group_index 1`. Do not combine group/parent-operator/direct-ID selection modes. Group indices are 1–25; parent indices 1–50.

Run the following commands **one at a time** on the actual desktop. DISPLAY/XAUTHORITY were verified for this session; use your session's values after login changes. `run_mj.sh --gui` forwards DISPLAY, X11 socket, Xauthority, HEADLESS=0, LIVESTREAM=0. R resets the same configuration; close the window to exit. Do not run all eight commands concurrently.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
export DISPLAY=:1
export XAUTHORITY=/run/user/1000/gdm/Xauthority
```

operator_A_1 first item: `toast_v20261108_097` (parent index 1).

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_A_1 --group_index 1
```

operator_A_2 first item: `toast_v20261108_087` (parent index 26).

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_A_2 --group_index 1
```

operator_B_1 first item: `toast_v20261108_041` (parent index 1).

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_B_1 --group_index 1
```

operator_B_2 first item: `toast_v20261108_011` (parent index 26).

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_B_2 --group_index 1
```

For a finite smoke/reset run, append `--steps 120 --reset_every 60` to the viewer command. This could not be run in this session.

## Quest: Dedicated Bridge and First Configuration in Each Group

Use a new bridge and separate port to avoid affecting running servers/simulations. Input mappings are unchanged. Start the server in a separate terminal, then open/Pair at its HTTPS address on Quest. `192.168.10.116` is the host address from previous documentation; change `--host` if your PC's Quest-reachable address differs. If port 8766 is occupied, choose an unused port rather than stopping its process. The server was not run during this work.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
python3 scripts/quest_diagnostic/server.py \
  --host 192.168.10.116 --port 8766 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab_mj/logs/quest_scenarios_v20261108
```

Quest Browser address: `https://192.168.10.116:8766/`. The simulation below reads the server's input.json. The new bridge is not automatically attached to an existing browser/server session; Pair at this address. GUI variables are as above. Run **only one** required group command below. `--keep-open` remains open between episodes. Recording is not enabled by default.

operator_A_1:

```bash
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_scenarios_v20261108 \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_A_1 --group_index 1 \
  --enable-grippers --keep-open
```

operator_A_2:

```bash
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_scenarios_v20261108 \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_A_2 --group_index 1 \
  --enable-grippers --keep-open
```

operator_B_1:

```bash
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_scenarios_v20261108 \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_B_1 --group_index 1 \
  --enable-grippers --keep-open
```

operator_B_2:

```bash
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_scenarios_v20261108 \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_B_2 --group_index 1 \
  --enable-grippers --keep-open
```

Select the next item in a new run with e.g. `--group_index 2`. Switching scenarios within one process was not added. For existing recording functionality, use a new `--record-dir` and existing recording options; metadata stores parent operator/index and group/group index together. Existing diagnostic recordings are not automatically labeled successful demonstrations.

## Files Changed in This Work

- `scripts/tools/generate_current_toast_scenarios.py`: current source-contract/asset checks, new samples, layout validation, balanced allocation, and outputs.
- `scripts/tools/toast_scenario_geometry.py`: reused local geometry/distance checks; extended task probes to four slices.
- `scripts/tools/test_current_toast_delivery.py`: uniqueness/balance/group-selection/recording/loader/reset/actual-USD static checks.
- `scripts/tools/view_make_toast_scenario.py`: group selection, assignments.csv beside the version manifest, and existing A/B compatibility.
- `scripts/quest_diagnostic/teleop_toast.py`: shared selector with group mapped to existing recorder operator/index. Existing first-B-ID guard applies only to the old manifest.
- `scripts/tools/toast_recording_metadata.py`: group/both-index metadata for new recordings.
- This version folder: new scenarios/assignments/poses/distributions/validation/reference inputs/documentation.

Original cyclo_lab and existing scenario files were unchanged; no commit/push was performed.
