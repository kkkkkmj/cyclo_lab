> **Historical development record**: Preserves the original descriptions, values, and execution results; this is not the current run guide. See [Changes](../../../CHANGES.md) for current settings and commands. In particular, gains of 2/0.5 were an intermediate comparison configuration, not the original v2 defaults. Claims about stable rack support and runtime validation must be read alongside the latest diagnostics. Host paths/logs below identify local evidence from that time.

> Current entry point: [Changes](../../../CHANGES.md). Historical values in the development and measurement records below describe their respective configurations. The current v2 rising target/upper limit is +35 mm and the lower limit is -45 mm. Adapt recorded PC IPs, absolute host paths, and container names to your environment. Use the variable-based commands in the current guide.

The current v2 velocity limit is 6.5 rad/s for both left/right master joint1 (changed from 2.2).
Default slave velocity limits and gains of 100/4 are retained. Detailed evidence and validation:
[README_GRIPPER_SPEED.md](GRIPPER_SPEED.md).

# v2 Toast / Quest Gripper Gains 100/4

These are the current settings in `/home/mj/nrf_humanoid/cyclo_lab_mj`
for `Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2`.

| Joint | Role | stiffness | damping |
|---|---|---:|---:|
| gripper_l_joint1 | master, retained | 100.0 | 4.0 |
| gripper_l_joint2 | slave, changed | 100.0 | 4.0 |
| gripper_l_joint3 | slave, changed | 100.0 | 4.0 |
| gripper_l_joint4 | slave, changed | 100.0 | 4.0 |
| gripper_r_joint1 | master, retained | 100.0 | 4.0 |
| gripper_r_joint2 | slave, changed | 100.0 | 4.0 |
| gripper_r_joint3 | slave, changed | 100.0 | 4.0 |
| gripper_r_joint4 | slave, changed | 100.0 | 4.0 |

## Configuration Path and Override Checks

- The shared slave defaults of 2/0.5 in `assets/robots/FFW_BG2.py` were left unchanged to avoid
  affecting other tasks. Master joint1 was already 100/4 and was unchanged.
- `MakeToastFFWBG2BimanualEnvCfg` sets the slaves to 100/4.
- Previously, derived `MakeToastFFWBG2BimanualServeEnvCfg` lowered them to 2/0.5 at the end.
  This v2 override was changed to **100/4**. Both the current v2 viewer and Quest use this configuration.
- Quest `configure_slave_gains()` now validates the six slave mappings and gains of 100/4.
  Other values fail before execution. It does not silently rewrite settings.
- The previous comparison option `--gripper-slave-gains-official` reverted to 2/0.5,
  so it now raises an explicit error. Omit it from current execution commands.
- Optional J1/J3 velocity comparisons copy the final actuator while preserving gains of 100/4.
  Default speed/effort values and VR input mappings were unchanged.
- Existing PhysX readback hooks at startup reset and subsequent resets were retained.
  Expected gains are 100/4 for both master and slave. A cfg change to 2/0.5 is not accepted
  as a new expectation. Actual PhysX tensors are queried by joint name, with mismatches rejected.
- This change is not hot-reloaded into an already running simulator.

## Changed Files

- `source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/bimanual_env_cfg.py`:
  Only the final v2 slave-gain override was changed to 100/4.
- `scripts/quest_diagnostic/teleop_slave_gains.py`:
  Soft-gain override rejection, configuration validation, and strict 100/4 readback expectations.
- `scripts/quest_diagnostic/teleop_toast.py`: updated help for the retired option.
- `scripts/quest_diagnostic/test_teleop_slave_gains.py`:
  Updated final-gain/option/reset checks and rejection of incorrect per-joint readback.
- `scripts/quest_diagnostic/test_teleop_gripper_options.py`:
  Changed expected gains after J3 velocity comparison to 100/4.
- `README_QUEST.md`, `README_TOASTER_LED.md`, `README_BREAD_SLOT.md`:
  Distinguished current gains from historical 2/0.5 records.
- `README_GRIPPER_GAINS.md`: this report.

## Validation Results

**13 CPU tests passed**:
Actual robot configuration literals and task overrides were evaluated to check final left/right joint1–4 gains.
Checks covered unchanged values under the default Quest configuration, rejection of the old soft override, gain preservation
under J1/J3 velocity options, startup/reset readback call sites, and rejection of per-joint stiffness/damping mismatches.
The readback tests use **mocked** PhysX tensor APIs, not actual PhysX readback results.
Python syntax checks and git diff --check passed.

The actual GUI smoke attempt failed before startup because Docker socket access was denied.
**Actual PhysX joint-gain readback and GUI/Quest control response remain unverified.**
CPU configuration values are not reported as actual runtime readback.

Evidence:
- `logs/gripper_gains_100_4_validation/configured_gains.json` — final CPU configuration
- `logs/gripper_gains_100_4_validation/cpu_tests.log`
- `logs/gripper_gains_100_4_validation/gui_attempt.log`

The new rack/bread configuration, 90% lever activation, 4-second heating, phase-based LED, recent-heated-ID success criteria,
VR input, other joint settings, and scenarios were unchanged.
The original `/home/mj/nrf_humanoid/cyclo_lab` and running processes were untouched.
No commit/push was performed.

## Execution / Revalidation

Use the existing modified-checkout commands without `--gripper-slave-gains-official`.
See [README_TOASTER_LED.md](TOASTER_LED.md) for full GUI and Quest commands.
Changes apply in a new process.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
python3 -m unittest discover -s scripts/quest_diagnostic -p 'test_teleop*py'

DISPLAY=:1 XAUTHORITY=/run/user/1000/gdm/Xauthority \
./scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --operator operator_B --scenario_index 1
```

At Quest startup/reset, inspect joint_names/stiffness/damping in the `GRIPPER_RUNTIME_OK` log.
This log appears only when actual PhysX readback passes the expected values.
