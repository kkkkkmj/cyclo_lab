> **Historical development record**: Preserves the original descriptions, values, and execution results; this is not the current run guide. See [Changes](../../../CHANGES.md) for current settings and commands. In particular, gains of 2/0.5 were an intermediate comparison configuration, not the original v2 defaults. Claims about stable rack support and runtime validation must be read alongside the latest diagnostics. Host paths/logs below identify local evidence from that time.

> Current entry point: [Changes](../../../CHANGES.md). Historical values in the development and measurement records below describe their respective configurations. The current v2 rising target/upper limit is +35 mm and the lower limit is -45 mm. Adapt recorded PC IPs, absolute host paths, and container names to your environment. Use the variable-based commands in the current guide.

# Toaster Eligibility for All Four Slices / 4-Second Heating / Automatic Cycle LED — 2026-11-08

This document describes the behavior at that time. The previous “LED ON when lever depression is at least 90%” rule was removed.
The modified repository is `/home/mj/nrf_humanoid/cyclo_lab_mj`; the lab original was unchanged.
Other running jobs were not interrupted. No commit/push was performed.

## Condition Changes

Latest change: only automatic activation's `pressed = ratio >= .95` was changed to `.90`.
Other uses of 0.95, phase-based LED behavior, 4-second heating, and overall task success criteria were unchanged.
This change touched toast_cycle.py, scripts/tools/test_toaster_led.py, and this report.
Validation log: `logs/toaster_start_90_validation/cpu_tests.log`.
Actual PhysX/GUI/Quest were not run for this change and remain unverified.

Previously, only bread_0 or bread_1 could activate the cycle.
Now the loading condition holds if **at least one** existing predicate across four slices × two slots is true.

- bread_0 correctly loaded in slot 0 or slot 1
- bread_1 correctly loaded in slot 0 or slot 1
- bread_2 correctly loaded in slot 0 or slot 1
- bread_3 correctly loaded in slot 0 or slot 1

The position/height/orientation conditions in `bread_in_slot` are unchanged. Only eligibility was expanded; the shared predicate was not modified.
Loading must coincide with the existing `phase==0`, measured normalized lever depression `>=0.90`, and previous pressed=false.
Loading bread while holding the lever down does not start the cycle until a new threshold crossing.
Two slices in separate slots also start normally.

No post-start transition requires two loaded slices, so no further relaxation was needed.
As before, the cycle proceeds if bread disappears after activation. No new cancellation condition was added.

## Actual Phase and LED State

| phase | Meaning | LED |
|---|---|---|
| 0 | Idle | OFF |
| 1 | Bread carriage lowering | ON |
| 2 | Heating | ON |
| 3 | Rising | OFF |
| 4 | Complete | OFF |

The LED reads `toast_cycle.phase` directly. Activation logic is not duplicated in the LED code.
ON is applied immediately after the update that starts phase 1; OFF is applied immediately after
heating ends and phase 3 begins. Updated materials appear in the next render, without changing already captured frames.
The LED remains OFF in phase=0 even above 90% lever depression. Small lever fluctuations during lowering/heating do not affect it.
Environments without an automatic cycle show OFF. There is no separate cancellation path; normal reset sets phase to 0
and turns the LED OFF. Recording restoration (reset_to) displays the actual restored phase.

## Retained Timing, Behavior, and Success Criteria

- As before, normalized lever depression uses the measured joint_1 position and runtime limits:
  `(q_actual-q_up)/(q_down-q_up)`. Asset limits are approximately −0.0138 to +0.0642 m.
- Heating starts after a 45 mm lowering stroke, at least 0.60 seconds, target-position error below 1.5 mm,
  and measured bread carriage speed below 0.01 m/s.
- elapsed=0 on phase=2 entry. Rising begins on the first update reaching **4 seconds of simulation time**
  (`elapsed >= 4.0`), accumulated through `env.step_dt`. To prevent rising before 4 seconds,
  the previous 1e−5 early tolerance was removed. Wall-clock time is not used.
- Rising interpolation lasts 0.80 seconds, with a v2 bread carriage target of +15 mm. The lever target is its fully raised lower limit.
- Rising completes after at least 0.92 seconds and bread carriage target error below 1.5 mm, as before.
- **Bread success criteria for the current v2 task:** At least one of the four slices must complete heating under the same ID
  and meet plate-center radius and existing height/orientation/speed conditions.
  Requirements for both bread_0/1 on the plate and bread_2/3 remaining on the rack were removed.
  Non-bread criteria and lever/LED/4-second heating behavior were retained.
  See [README_TOAST_SUCCESS.md](TOAST_SUCCESS.md) for criteria, heating history, and validation limits.


The new rack and bread configuration, Quest input, slave gains 100.0/4.0, master/arm settings,
100 scenarios and A/B assignments, and action/observation dimensions were unchanged.

## LED Geometry and Per-Environment Isolation — Retained

- prim: `/World/envs/env_N/Toaster/base/LeverPressLED/Lens`
- Base-local center `(0.1027,−0.045,0.050) m`, upper left on the +X lever face.
- Diameter 8 mm, thickness 1.2 mm, approximately 1.1 mm protrusion from the surface.
- OFF: dark gray `(0.025,0.025,0.025)`, emission=0.
- ON: green `(0.01,0.8,0.025)`, emission `(0.01,1.2,0.025)`.
- Independent Material/Shader per environment. No collider, mass, joint, or separate light.
- Existing common-environment creation/step/reset/reset_to/render update paths were retained.

## Files Changed in This Work

The configuration prefix below is
`source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/`.

| File | Reason |
|---|---|
| toast_cycle.py | OR combination of four-slice × two-slot predicates, 4-second heating, and strict boundary |
| bimanual_env_cfg.py | Description string only, updated for 4-second heating |
| scripts/tools/check_toast_cycle.py | Replaced the runtime check's hardcoded 5 seconds with cycle.HEATING_SECONDS |
| scripts/tools/test_toaster_led.py | One/two/no slices, actual cycle progression, and phase-based materials |
| README_TOASTER_LED.md | Updated rules and validation results |

## Validation

**11 CPU tests passed.** Actual ToastCycle functions used fake scene I/O; USD data came from actual
local assets. These tests did not run physics integration or rendering.

- No bread + 90%/95%/100% threshold crossing: no activation, OFF.
- Boundary checks: waiting/OFF at 89.9999%; activation/ON at 90%.
- Adjacent representable float32 measured positions immediately below/above the threshold were also tested. The initial test's
  inverse-conversion rounding issue was corrected in the fixture; no epsilon was added to runtime code.
- Eight combinations with only one of bread_0–bread_3 loaded in slot 0/1:
  waiting/OFF at 89%; activation/ON on crossing 90%.
- Both orderings of two slices in separate slots, and bread_2+3, also activate/turn ON.
- Eight combinations plus X/Y/Z deviations and incorrect orientation checked using the actual loading predicate and carriage-height wrapper.
- Changing loading while holding the lever does not activate; a new crossing is required.
- After one-slice activation, lever fluctuations/loading loss retain the existing lowering/heating progression and LED ON.
- Minimum lowering time/speed conditions, timer=0 at heating entry, still heating at 3.96 seconds,
  then rising/OFF after another 0.04 seconds; near 3.99999 seconds and the first update beyond 4 seconds were checked, along with existing rising target/completion.
- Reset OFF, then loading/pressing again activates/turns ON.
- Actual common-environment LED hook phase forwarding and OFF without a cycle were checked.
- Independent materials across clone-inherited environments, no duplicate prims, translation/rotation following,
  and no physics APIs under the LED were checked.
- Modified Python syntax checks and git diff --check passed.

A GUI smoke test in a separate container failed before startup because Docker socket access was denied.
**Actual PhysX/GUI/RGB/Quest validation and simulator screenshots remain unverified.**
Logs: `logs/toaster_four_bread_4s_validation/cpu_tests.log`, `gui_attempt.log`.

## Execution

Current desktop values: DISPLAY=:1, Xauthority=/run/user/1000/gdm/Xauthority.
Use your session's values for other logins. `--gui` passes DISPLAY, the X11 socket,
a read-only Xauthority mount, HEADLESS=0, and LIVESTREAM=0. Do not add `--headless`.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
DISPLAY=:1 XAUTHORITY=/run/user/1000/gdm/Xauthority \
./scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --operator operator_B --scenario_index 1
```

The viewer inspects the initial configuration. R resets; the LED is OFF before activation.
To manipulate bread and the lever, use the existing Quest input server/bridge and run:

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
DISPLAY=:1 XAUTHORITY=/run/user/1000/gdm/Xauthority \
./scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --keep-open --enable-grippers --control-profile practice \
  --position-scale 1 --rotation-scale 1 --no-home-limits --no-speed-limits --workspace off \
  --max-target-lead 0.12 --max-angular-lead-deg 45 --tracking-stall-seconds 2 --preview-hz 15
```

For the existing Quest RGB preview without a GUI, omit `--gui` and retain `--headless`.
There is no LED-specific option. Common code applies in a new environment process. This work did not
restart or hot-reload running processes.

```bash
# CPU revalidation
cd /home/mj/nrf_humanoid/cyclo_lab_mj
/home/mj/hand-sim-conda/bin/python scripts/tools/test_toaster_led.py
```
