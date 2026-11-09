> **Historical development record**: Preserves the original descriptions, values, and execution results; this is not the current run guide. See [Changes](../../../CHANGES.md) for current settings and commands. In particular, gains of 2/0.5 were an intermediate comparison configuration, not the original v2 defaults. Claims about stable rack support and runtime validation must be read alongside the latest diagnostics. Host paths/logs below identify local evidence from that time.

> Current entry point: [Changes](../../../CHANGES.md). Historical values in the development and measurement records below describe their respective configurations. The current v2 rising target/upper limit is +35 mm and the lower limit is -45 mm. Adapt recorded PC IPs, absolute host paths, and container names to your environment. Use the variable-based commands in the current guide.

Subsequent changes set the current v2 left/right slave gains to 100.0/4.0.
The 2.0/0.5 values in this document were retained at the time of the bread rack replacement.
See [README_GRIPPER_GAINS.md](GRIPPER_GAINS.md) for the current settings.

# bread_slot Rack Replacement Record — 2026-11-08

Only `/home/mj/nrf_humanoid/cyclo_lab_mj` was modified. The separate original repository
`/home/mj/nrf_humanoid/cyclo_lab` was not written to. Running training/simulation processes
were neither stopped nor restarted, and no commit/push was performed.

## Replacement Target and Assets

- Target: `scene.bread_shelf`, holding four bread slices before toasting.
- Scene prim: `{ENV_REGEX_NS}/BreadShelf` (single environment: `/World/envs/env_0/BreadShelf`).
- Previous asset: `source/cyclo_lab/data/objects/robodojo_make_toast/bread_shelf/object.usdz`.
- New source asset: `source/cyclo_lab/data/objects/bread_slot/bread_slot.usdz`.
- Loaded asset: `source/cyclo_lab/data/objects/bread_slot/rack.usda`.
- New collision prim: `/World/envs/env_0/BreadShelf/Model/Body1`.
- Copied from `/home/mj/Downloads/bread_slot.usdz`, with an identical SHA256:
  `338eb23d759224c0686857b3e793070b2bf03f9c7fe25f872a3c598bd67330d8`.
- The previous asset file is preserved but is not referenced by the new scene. The new wrapper has
  exactly one collision Mesh. Toaster body, lever, bread carriage assets, and behavior code were unchanged.

## Units, Geometry, Placement, and Collision

The local file contains `bread_slot.usdc`, a single Mesh `/bread_slot/Body1` and materials,
with `metersPerUnit=0.001`, `upAxis=Y`, and no joint, rigid-body, or collision APIs.
Body1 has an **internal 10× transform**. Including that transform, its actual dimensions are
**230 × 130 × 45 mm**. The wrapper applies the mm→m factor of 0.001 once,
then rotates +90° about X to convert Y-up→Z-up. No additional scaling or nonuniform deformation is applied.
The bimanual environment's previous rack scale `(2,1,1)` was changed to `(1,1,1)`. Bread size is unchanged.

The default bimanual scene reference point `(0.45,-0.25,1.0382)` and yaw −90° were retained.
The wrapper translates Z by `−0.044148661134795 m` to align its bottom with the actual
extracted tabletop height `0.994051338865205 m` in the existing manifest. Its top is approximately `1.039051339 m`.
Per-scenario XY, yaw, and reference points are unchanged; the new bread poses follow the same transform.

Groove centers are at rack-local X `+90,+30,−30,−90 mm`. Groove width is approximately 25 mm;
the flat inner floor is 15 mm above the model bottom, and the top is 45 mm above it.
Rounded lips connect both ends. The fixed Mesh has `PhysicsCollisionAPI` and
`PhysicsMeshCollisionAPI(approximation="none")`. No rigid-body API is applied.
Collision therefore uses the original triangle surfaces rather than filling the grooves with a single convex hull.
The scene's existing contact_offset=1 mm and rest_offset=0 were retained.
Actual PhysX cooking results could not be checked because runtime access was restricted.

## Initial Bread Configuration and Success Criteria

`bread_0,1` are task slices; `bread_2,3` are reserve slices that must remain on the bread rack at success.
The existing bread convex collider and dimensions of approximately 116.95 × 116.06 × 11.80 mm were retained.
Bread width prevents it from reaching the flat groove floor; the configuration **rests on the rounded end lips**.
Triangle–convex-polyhedron clipping confirmed no initial penetration and contact within 1 mm below.
The initial gap targets approximately 0.3 mm contact clearance; the actual settled pose under gravity is unverified.

Bread root positions (m) in the default bimanual environment, ordered bread_0 through bread_3:

| Item | Before | After |
|---|---|---|
| Common X | 0.443000 | 0.450250 |
| Y | −0.320, −0.270, −0.220, −0.172 | −0.334392, −0.274392, −0.214392, −0.154392 |
| Common Z | 1.093200 | 1.082551 |
| quaternion wxyz | approximately (0.5,0.5,0.5,−0.5) | unchanged |

The new shelf-local bread root offsets are
`(groove center X −0.005607555, +0.000249905, +0.044351338865205)` m.
These compensate for the asymmetric bread root and actual thickness center. Bread extends approximately 102 mm above the rack,
with a nominal thickness gap of approximately 48 mm between adjacent slices. These are geometric dimensions, not grasp validation.

The reserve-slice check previously used shelf-local `|X|<170 mm, |Y|<60 mm, 15<Z<160 mm`
and upright orientation. It now requires **X±5 mm, Y±3 mm, Z±6 mm relative to each new groove's initial root**,
plus the existing upright check and alignment of the bread thickness axis with the groove direction (`|R[0,2]|>.94`).
No condition was removed or tolerance widened. Success criteria unrelated to the rack, including
heating completion, plate placement, arms, and grippers, were unchanged. Whether these tolerances
suit dynamic settling requires further PhysX smoke testing.

## 100 Scenarios and Reset

The existing `scenario_delivery/manifest.json` and `assignments.csv` were unchanged.
A derived `manifest_bread_slot.json` was generated and selected as the new default manifest.
All 100 IDs, ordering, A/B assignments of 50 each, and toaster/plate/rack positions and quaternions are identical.
Changes are limited to rack scale, the four bread positions/orientations, and associated recording metadata.
Previous rack validation fields are separated as `legacy_rack_evidence`, not presented as new validation.
Legacy recordings must be replayed with their original asset geometry; identical replay with the new geometry is not guaranteed.

Bimanual reset retains the existing default_root_state restoration. The single-arm base task's ±8 mm bread Y
jitter could penetrate the new groove end walls, so it was removed in favor of restoring configured initial poses.
CPU tests with fake scene I/O executed the actual reset/predicate bodies across 100 scenarios,
repeated resets, environment-origin transforms, valid reserve-slice acceptance, and lifted/out-of-groove/lying-slice rejection.

## Changed Files

The shared prefix for the configuration paths below is
`source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/`.

| File | Reason |
|---|---|
| assets.py | New asset path and BREAD_OFFSETS matched to the actual grooves |
| env_cfg.py | Removed unnecessary rigid_props from the fixed triangle collider |
| bimanual_env_cfg.py | Removed the previous 2× scale and applied the new bread offsets directly |
| bimanual_mdp.py | Reserve-slice check relative to the new grooves |
| mdp.py | Shared rack check and removal of unsafe bread-reset Y jitter |
| scenarios.py | New derived manifest as the default |
| source/cyclo_lab/data/objects/bread_slot/{bread_slot.usdz,rack.usda} | Preserved source asset and physics wrapper |
| scenario_delivery/manifest_bread_slot.json | New initial bread poses while preserving the existing list |
| scripts/tools/{toast_recording_metadata,view_make_toast_scenario}.py | Default manifest selection for recording/loading and guidance |
| scripts/tools/test_toast_scenario_runtime.py | Included the new manifest in the repository-rename test |
| scripts/tools/{build_bread_slot_asset,update_bread_slot_manifest}.py | Conversion and derived-manifest regeneration tools |
| scripts/tools/{check_bread_slot_geometry,test_bread_slot_logic}.py | Geometry/predicate/reset validation |
| docker/compose.mj.yaml, scripts/run_mj.sh, scripts/tools/mj_python.py | Dedicated modified-checkout launcher and import-path checks |
| README_BREAD_SLOT.md | Results and execution instructions for this work |

Pre-existing README_TOAST/replay script changes and Quest files were not overwritten.
Quest input mapping/server/teleop code was unchanged. The v2 left/right slave joint2/3/4
stiffness=2.0, damping=0.5 and master joint1/arm settings were retained.

## Execution Path Checks

Several existing README_QUEST commands refer to the host path `/home/mj/nrf_humanoid/cyclo_lab`
before the rename. Use the commands below for this modified checkout; historical documents were not globally replaced.
The existing Docker container's actual mounts and editable installation could not be inspected because
Docker socket access was denied. A separate Compose project `cyclo_lab_mj` was created without modifying shared installations.

`docker compose config` confirmed the host mount `/home/mj/nrf_humanoid/cyclo_lab_mj`
and container target `/workspace/cyclo_lab`. The container target name
cyclo_lab does not imply use of the original host repository. Cache/log/data volumes are also
isolated under `cyclo_lab_mj_*`. Existing containers are not stopped/recreated.
PYTHONPATH and mj_python.py prioritize the modified source and bundled IsaacLab,
and check the `cyclo_lab` spec path. Host-side modified code/asset path reporting passed.
Actual container imports/asset loading remain unverified.
The sole shallow symlink `third_party/IsaacLab/_isaac_sim -> /isaac-sim` is for the container and was retained.
Host `/home/mj/IsaacLab/.venv/bin/python` was unusable because its old `/home/rllab/...` target was missing.
USD checks used the working `/home/mj/hand-sim-conda/bin/python`. No installation was changed.

## Validation Results and Evidence

- 39 CPU tests passed: scenario/recording 14, slave gains 6, Quest control 14,
  binary trigger 4, and one new integration test for reset/predicates across 100 scenarios.
- Verified new USD size/axes/units/collision APIs, zero initial bread/rack intersections, and support surfaces within 1 mm.
- Rack+bread footprints across 100 scenarios: minimum extracted-tabletop boundary clearance 31.70 mm.
  Minimum separating-axis gap from the existing conservative toaster/plate footprints: 133.13 mm.
  This is a planar layout check, not arm/hand swept-collision or IK validation.
- Syntax checks for 21 Python files, shell syntax checks, and git diff --check passed.
- The binary-trigger tests initially failed under system Python due to missing torch;
  all 4 passed under conda Python. py_compile failed due to existing cache-directory permissions,
  so all 21 files were checked using compilation without cache writes.
- The Docker smoke attempt **failed before simulator startup** because socket access was denied.
  NVIDIA-SMI also failed to connect to the driver. GPU usage by running jobs could not be determined.
- Consequently, **stability under gravity, actual PhysX collision cooking, actual scene reset,
  simulator rendering, Quest runtime behavior, and robot grasping remain unverified**.

Evidence: `logs/bread_slot_validation/geometry_results.json`, `compose_resolved.yaml`,
`smoke_attempt.log`, `front.png`, `top.png`, `oblique.png`.
The PNG is a CPU geometry plot of actual USD surfaces/bread convex colliders, not an Isaac Sim screenshot.

## Exact Execution Commands

Short viewer/reset smoke test in a separate container (does not stop existing jobs):

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
./scripts/run_mj.sh scripts/tools/view_make_toast_scenario.py \
  --operator operator_B --scenario_index 1 --headless --steps 100 --reset_every 50
```

Connect a Quest server on new port 8766 to the modified checkout's dedicated bridge:

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
python3 scripts/quest_diagnostic/server.py --host 0.0.0.0 --port 8766 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab_mj/logs/quest_teleop
```

On Quest, open the PC's HTTPS address on port 8766. Run with the existing practice input settings:

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
./scripts/run_mj.sh scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers --control-profile practice \
  --position-scale 1 --rotation-scale 1 --no-home-limits --no-speed-limits --workspace off \
  --max-target-lead 0.12 --max-angular-lead-deg 45 --tracking-stall-seconds 2 --preview-hz 15
```

These commands require Docker/GPU access on the host. They use the existing shared image
`robotis/cyclo-lab:latest` without reinstalling editable packages.
The `MJ_CHECKOUT`, `MJ_CODE`, and `MJ_RACK` outputs identify the selected paths.

CPU revalidation:

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
/home/mj/hand-sim-conda/bin/python scripts/tools/check_bread_slot_geometry.py
/home/mj/hand-sim-conda/bin/python scripts/tools/test_bread_slot_logic.py
python3 -m unittest discover -s scripts/tools -p 'test_toast*py'
```
