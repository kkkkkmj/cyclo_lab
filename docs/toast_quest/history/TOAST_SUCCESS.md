> **Historical development record**: Preserves the original descriptions, values, and execution results; this is not the current run guide. See [Changes](../../../CHANGES.md) for current settings and commands. In particular, gains of 2/0.5 were an intermediate comparison configuration, not the original v2 defaults. Claims about stable rack support and runtime validation must be read alongside the latest diagnostics. Host paths/logs below identify local evidence from that time.

> Current entry point: [Changes](../../../CHANGES.md). Historical values in the development and measurement records below describe their respective configurations. The current v2 rising target/upper limit is +35 mm and the lower limit is -45 mm. Adapt recorded PC IPs, absolute host paths, and container names to your environment. Use the variable-based commands in the current guide.

# v2 Serving Success Criteria — At Least One Fully Heated Slice

The target is the current v2 serving task in `/home/mj/nrf_humanoid/cyclo_lab_mj`.
The lab original, running processes, rack/initial bread configuration, Quest input, joint gains, scenarios, and A/B
assignments were unchanged. No commit/push was performed. The previous non-serving task without a plate retains its criteria.

## Actual Asset Inspection and Center Tolerance Radius

The project's `robodojo_make_toast/bread/object.usdz` and `plate/object.usdz` were opened with pxr
and measured with internal transforms applied. Actual bread dimensions are approximately 116.948 × 116.062 × 11.799 mm.

The bread root is not its geometry center. The geometry center is the **AABB midpoint of the actual visual convex hull**.
Its root-local coordinates are `(0.0000864230, -0.0002499074, 0.0056075576) m`.
It is not assumed to be the center of mass. `bread_geometry_center()` computes it from actual asset vertices.

With plate scale `(1.5,1.5,.22)`, the XY outline's inscribed radius is `0.0967231746 m`.
The maximum bread radius about its geometry center is approximately `0.0750437343 m` in XY and `0.0750439491 m` in 3D.
Using the conservative 3D radius for arbitrary rotation/tilt,

`0.020 + 0.0750439491 = 0.0950439491 < 0.0967231746 - 0.0005`

the center tolerance radius was set to **20 mm** to satisfy this inequality. Even after the existing 0.5 mm edge margin,
approximately 1.18 mm remains. The previous all-vertex radius `0.0962231746 m` was not reused as a center radius.
This radius is the explicit setting `SERVING_BREAD_CENTER_RADIUS = .020` in `assets.py`.

Transform the bread root pose relative to the current plate pose, then add the geometry center rotated by the bread orientation:

```
center_plate_local = relative_bread_position + relative_bread_rotation @ geometry_center
sqrt(center_plate_local.x**2 + center_plate_local.y**2) < SERVING_BREAD_CENTER_RADIUS
```

Only XY changed to a center-point check. Height still uses all actual hull support vertices.

## Per-Slice Heating Completion History

Previously, `ToastCycle.state()` and the recorder contained only phase, elapsed, command, previous_pressed, and heating_time,
without per-slice heating history. Two bool `[num_envs,4]` records were added per environment.

- `heating_present`: marks correctly loaded IDs on heating-phase entry. Each control update during heating
  reuses the existing bread_in_slot check; an ID that leaves or violates position/orientation requirements even once
  remains invalid for that cycle. Reinsertion does not restore eligibility.
- `heated_bread`: records only IDs that remained valid when rising starts after 4 seconds of heating.

Thus bread loaded only at activation and removed before heating, removed/reinserted during heating, or inserted late
is not marked complete. Either slot is allowed, but correct loading must hold at every heating update.
This is not a heat-transfer model; it records **the existing correct-loading predicate plus 4 seconds in the heating state**.
Checks use the existing control period (approximately 40 ms by default). They do not rule out brief departures between samples.

Reset clears both records. They are saved/restored through the existing recorder state()/restore() path.
The new records use separate `[N,4]` keys without changing existing scalar-state shapes.
Restoring legacy recordings without these fields sets both records to false because evidence is absent.
Heated IDs are not inferred from legacy phase/timer values alone. Action/observation dimensions were unchanged.

## Complete Final Success Criteria

**All** conditions below must hold. For bread, **at least one identical slice** among the four must meet every bread criterion.

| Category | Exact condition |
|---|---|
| Eligible bread | At least one of bread_0, bread_1, bread_2, bread_3 |
| Slice heating | heated_bread=true for that ID: correct loading from heating entry through 4-second completion |
| Slice XY | Geometry-center distance d_xy < 0.020 m in the current plate frame |
| Slice height | All support vertices in plate-local coordinates: min Z > −0.002 m, max Z < 0.050 m (unchanged) |
| Slice tilt | abs(R[2,2]) > 0.94 for rotation relative to the plate (unchanged) |
| Slice linear speed | World linear-velocity norm < 0.15 m/s (unchanged) |
| Other slices | No position, velocity, or rack-retention requirement in the success predicate |
| Plate orientation | World rotation R[2,2] > 0.985 |
| Plate position | Environment-relative XY displacement norm from initial position < 0.025 m, environment-relative X > 0.419 m |
| Cycle complete | phase=4 in that environment |
| Lever returned | Existing lever_pressed=false, i.e. measured normalized lever depression < 0.85 (distinct from activation threshold 0.90) |
| Grippers | Left/right gripper joint1 each < 0.15 |
| Arms in standby | Each arm_link7 within < 0.04 m of reference standby. Left (0.3609426,0.3954084,1.4419125), right with reversed Y sign |
| lift | abs(lift_joint) < 0.02 m |

**Existing height-check limitation:** Contact force/support is not checked directly. A floating slice at plate-local center height
0.10 m fails, but one hovering at 0.025 m can pass if its support-vertex heights, tilt, and speed meet the criteria.
The existing height/tilt/speed checks were retained as requested, so no additional contact condition was
added to reject this case. This must not be interpreted as validation of actual contact support.

**Separate termination conditions:** Existing `bread_dropping` (episode ends if any of the four bread roots has Z<0.75 m)
and time limits remain separate from the success predicate. Other slices may be off the rack without violating success,
but dropping them can still terminate the actual episode through existing termination conditions.

## Preserved Toaster Behavior

Activation requires one correctly loaded slice among four, idle state, and measured lever depression crossing 90%.
Heating begins after at least 0.60 seconds of lowering and the 1.5 mm position/0.01 m/s speed checks; the 4-second timer starts then.
LED ON during lowering/heating; OFF at rising start, while idle/complete, and on reset.
Existing rising interpolation, bread carriage +15 mm target, lever-return target, and rising-completion conditions were unchanged.

## Changed Files

Common configuration path:
`source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/`

| File | Change |
|---|---|
| assets.py | Explicit SERVING_BREAD_CENTER_RADIUS=0.020 |
| bread_geometry.py | Geometry-center computation from the actual hull |
| toast_cycle.py | Per-slice heating eligibility/completion bool records with reset/save/restore integration |
| bimanual_mdp.py | XY center check, OR success for the same heated ID, and removal of remaining-slice constraints for serving |
| scripts/tools/test_toast_serving_success.py | CPU validation using actual predicates/cycle/assets |
| README_TOASTER_LED.md | Updated current success-criteria guidance |
| README_TOAST_SUCCESS.md | This report |

## Validation and Unverified Items

22 CPU tests passed (11 existing cycle/LED + 11 new serving/heating-history tests).

- Each of the four slices can individually complete heating and succeed on the plate.
- Mismatched heating/placement IDs and unheated bread fail.
- XY inside/exact boundary/outside, and local coordinates under plate translation/yaw and bread yaw.
- Actual root-to-center offset and radial clearance calculations.
- High floating/too-low positions, tilt, and speed fail. The existing low-hovering allowance is also explicitly tested.
- Removal before heating, removal/reinsertion during heating, and late insertion fail.
- 4-second timer/LED retained; heating and completed states saved/restored; legacy restoration without evidence rejected.
- Reset/partial-environment reset clears heating records while preserving other environments.
- Success remains possible for the selected heated slice regardless of remaining-slice positions/velocities.
- Failure cases checked for plate/arms/grippers/lift/lever/cycle-completion conditions.

Tests used actual USD assets and function bodies, but scene I/O and coordinate-operation fixtures were CPU mocks.
Actual PhysX integration, heat transfer, contact, and RTX were not run.
The GUI smoke attempt failed before startup because Docker socket access was denied.
**Actual PhysX/GUI/Quest and actual grasping/plate-placement success remain unverified.**
Logs: `logs/toast_serving_success_validation/{success_tests,cycle_led_tests,gui_attempt}.log`.

CPU revalidation:

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
/home/mj/hand-sim-conda/bin/python scripts/tools/test_toast_serving_success.py
/home/mj/hand-sim-conda/bin/python scripts/tools/test_toaster_led.py
```

GUI/Quest execution still uses `scripts/run_mj.sh --gui ...`.
See the execution section of [README_TOASTER_LED.md](TOASTER_LED.md) for complete commands.
