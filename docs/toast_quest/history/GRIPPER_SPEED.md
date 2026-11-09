> **Historical development record**: Preserves the original descriptions, values, and execution results; this is not the current run guide. See [Changes](../../../CHANGES.md) for current settings and commands. In particular, gains of 2/0.5 were an intermediate comparison configuration, not the original v2 defaults. Claims about stable rack support and runtime validation must be read alongside the latest diagnostics. Host paths/logs below identify local evidence from that time.

> Current entry point: [Changes](../../../CHANGES.md). Historical values in the development and measurement records below describe their respective configurations. The current v2 rising target/upper limit is +35 mm and the lower limit is -45 mm. Adapt recorded PC IPs, absolute host paths, and container names to your environment. Use the variable-based commands in the current guide.

# v2 Toast/Quest Master Joint Velocity Limit: 6.5 rad/s

Changes were made only in `/home/mj/nrf_humanoid/cyclo_lab_mj`. The original cyclo_lab and running
processes were untouched. No commit/push was performed.

## Sources Checked and Configuration Order

1. The current toast task inherits `FFW_BG2_WITHOUT_MIMIC_CFG`, using asset
   `source/cyclo_lab/data/robots/FFW/FFW_BG2_without_mimic.usd`.
2. All left/right joint1–4 in this USD have `physxJoint:maxJointVelocity=372.42254638671875 deg/s`,
   approximately 6.5 rad/s. Position limits for each prim were also queried and logged; the USD was unchanged.
3. Shared Python `assets/robots/FFW_BG2.py` sets `gripper_master.velocity_limit_sim=2.2`,
   overriding the USD default, so the final pre-change v2 master setting on both sides was **2.2 rad/s**.
4. To avoid changing other tasks, the shared robot was retained, and
   `MakeToastFFWBG2BimanualServeEnvCfg.__post_init__` received
   `self.scene.robot.actuators["gripper_master"].velocity_limit_sim = 6.5`.
   This group targets exactly left/right joint1.
5. IsaacLab articulation forwards the actuator's `velocity_limit_sim`
   through `write_joint_velocity_limit_to_sim` → PhysX `set_dof_max_velocities`.
   This does not change VR hand-motion scaling or commanded joint velocity.
6. Quest's existing `--right-gripper-j1-speed-6p5` option also sets the right master to 6.5,
   so it causes no per-joint numerical change with current defaults. Help text and tests were updated.
   No other master-velocity override/reset write path was found in the current v2/Quest path.

## Final Defaults

| Joint | Velocity limit (rad/s) | stiffness/damping | Effort setting |
|---|---:|---|---:|
| gripper_l_joint1 | 6.5 (changed from 2.2) | 100/4 | 30 |
| gripper_r_joint1 | 6.5 (changed from 2.2) | 100/4 | 30 |
| Left/right joint2/3/4 | approximately 6.5, existing USD retained | 100/4 | 20 |

Slave Python `velocity_limit_sim=None` is unchanged and inherits existing USD values.
The existing explicit `--right-gripper-j3-speed-2p2` comparison option was unchanged.
Only when this option is selected does right joint3 remain 2.2 as before, while both masters are 6.5.
The default run does not include this option.

**6.5 rad/s is a simulation velocity limit, not a claim that joints always move at that velocity.**
Actual velocity depends on position error, load, contact, effort, servo response, and other factors.

## Changed Files

- `source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/bimanual_env_cfg.py`:
  Set only v2 left/right master velocity_limit_sim to 6.5.
- `scripts/quest_diagnostic/teleop_slave_gains.py`: default PhysX velocity-readback expectations set to 6.5 for both masters.
- `scripts/quest_diagnostic/teleop_toast.py`: updated help for the existing right-master comparison option.
- `scripts/quest_diagnostic/test_teleop_gripper_options.py`: evaluated actual v2 overrides and updated velocity expectations.
- `scripts/quest_diagnostic/test_teleop_slave_gains.py`: updated mocked readback velocities and per-joint mismatch rejection.
- `README_QUEST.md`, `README_GRIPPER_GAINS.md`, `README_GRIPPER_SPEED.md`: current configuration guidance.

## Validation and Limitations

**13 CPU tests passed.** Actual configuration literals and v2 overrides were evaluated before and after the change.
The only final-actuator configuration differences were:

- gripper_l_joint1.velocity_limit_sim: 2.2 → 6.5
- gripper_r_joint1.velocity_limit_sim: 2.2 → 6.5

All gains, slave velocities, efforts, and arm/head/lift settings were identical in this comparison.
The USD defining joint position limits was unchanged.
Startup/reset readback checks the default velocity limit of 6.5 for every gripper joint,
and distinguishes 2.2 under the explicit J3 comparison option. Mock tests rejecting incorrect per-joint velocity/gain values passed.

The actual GUI smoke attempt failed before startup because Docker socket access was denied.
**Actual PhysX readback, actual velocity/contact response, and GUI/Quest runtime behavior remain unverified.**
The new rack, 90% activation, 4-second heating, LED, success criteria, and VR input were unchanged.

Evidence in `logs/gripper_master_speed_validation/`: `before.json`, `config_delta.json`,
`usd_limits.json`, `tests.log`, `gui_attempt.log`.

New v2 viewer/Quest runs use this by default; no additional option is needed.
Existing processes were not restarted and do not automatically adopt new values.
See [README_TOASTER_LED.md](TOASTER_LED.md) for GUI/Quest execution commands.
