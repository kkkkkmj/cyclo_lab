> 현재 실행 진입점: [README_TOAST_QUEST.md](README_TOAST_QUEST.md). 아래 단계별 작업·측정 기록의 과거 값은 당시 설정입니다. 현재 v2 상승 목표/상한은 +35 mm이며 하한은 -45 mm입니다. 기록 속 PC IP·호스트 절대 경로·컨테이너 이름은 실행 환경에 맞게 설정해야 합니다. 최신 문서의 변수 기반 명령을 사용하세요.

# cyclo_lab

[![IsaacSim](https://img.shields.io/badge/IsaacSim-5.1.0-silver.svg)](https://docs.isaacsim.omniverse.nvidia.com/latest/index.html)
[![Isaac Lab](https://img.shields.io/badge/IsaacLab-2.3.0-silver)](https://isaac-sim.github.io/IsaacLab/main/index.html)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://docs.python.org/3/whatsnew/3.11.html)
[![Linux platform](https://img.shields.io/badge/platform-linux--64-orange.svg)](https://releases.ubuntu.com/22.04/)
[![License](https://img.shields.io/badge/license-Apache2.0-yellow.svg)](https://opensource.org/license/apache-2-0)

https://github.com/user-attachments/assets/28347b4b-f90c-4a4f-8916-621f917d86cb

## Overview

**cyclo_lab** is a research-oriented repository based on [Isaac Lab](https://isaac-sim.github.io/IsaacLab), designed to enable reinforcement learning (RL) and imitation learning (IL) experiments using Robotis robots in simulation.
This project provides simulation environments, configuration tools, and task definitions tailored for Robotis hardware, leveraging NVIDIA Isaac Sim’s powerful GPU-accelerated physics engine and Isaac Lab’s modular RL pipeline.

> [!IMPORTANT]
> This repository currently depends on **IsaacLab v2.2.0** or higher.
>

## Installation (Docker)

Docker installation provides a consistent environment with all dependencies pre-installed.

**Prerequisites:**
- Docker and Docker Compose installed
- NVIDIA Container Toolkit installed
- NVIDIA GPU with appropriate drivers
- On ARM64, an NVIDIA DGX Spark with DGX OS 7 for Isaac Sim 5.1.0

**Steps:**

1. Clone cyclo_lab and initialize its direct submodules:

   ```bash
   git clone https://github.com/ROBOTIS-GIT/cyclo_lab.git
   cd cyclo_lab
   git submodule update --init
   ```

2. Build and start the Docker container:

   ```bash
   ./docker/container.sh start
   ```

   On ARM64, this creates `cyclo_lab-arm64` from the native ARM64 Isaac Sim 5.1.0 image. The image and cache volumes are separate from the x86-64 container. The first build downloads the ARM64 base image and installs Cyclo Lab dependencies.

   The original x86-64 image (`robotis/cyclo-lab:latest`) and container (`cyclo_lab`) remain available. On an ARM64 host, select them explicitly with `CYCLOLAB_DOCKER_ARCH=amd64 ./docker/container.sh logs` or another container command. The x86-64 container cannot run natively on an ARM64 host.

3. Enter the container:

   ```bash
   ./docker/container.sh enter
   ```

**Docker Commands:**
- `./docker/container.sh start` - Build and start the container
- `./docker/container.sh recreate` - Recreate the container from the current image
- `./docker/container.sh enter` - Enter the running container
- `./docker/container.sh stop` - Stop the container
- `./docker/container.sh logs` - View container logs
- `./docker/container.sh clean` - Remove container and image

**What's included in the Docker image:**
- Isaac Sim 5.1.0
- Isaac Lab v2.3.0 (from third_party submodule)
- zenoh_ros2_sdk 0.1.8 (from third_party submodule)
- IsaacLab-Arena integration (from third_party submodule)
- LeRobot 0.3.3 (in separate virtual environment at `~/lerobot_env`)
- All required dependencies and configurations

## Try examples

<details>
<summary>Imitation learning</summary>

>
> To control the robot while **recording demonstrations**, use `--teleop_device keyboard` in the `record_demos.py` command. Do not add `--keyboard`; that script does not accept it. Click the Isaac Sim window so it receives key presses. For the FFW-BG2 IK task, these keys control the right arm and gripper, not the mobile base.
>
> ```
> Key bindings:
> =========================== =========================
> Command                     Key
> =========================== =========================
> Toggle gripper (open/close) K      
> Reset recording             R
> Move arm along x-axis       W / S   
> Move arm along y-axis       A / D
> Move arm along z-axis       Q / E
> Rotate arm along x-axis     Z / X
> Rotate arm along y-axis     T / G
> Rotate arm along z-axis     C / V
> =========================== =========================
> ```

### FFW-BG2 Make Toast: keyboard demonstrations

Click the Isaac Sim viewport and use the key bindings above to control the right arm and gripper.
This command uses the seven-action `v0` task. Its recordings are separate from the
15-action bimanual `v2` datasets below; the default keyboard interface does not control both arms and the lift.

### FFW-BG2 Make Toast: automatic demonstrations with both arms and body lift

```bash
# Check the automatic expert without writing a training dataset
python scripts/imitation_learning/isaaclab_recorder/generate_make_toast_demos.py \
  --check_only --max_attempts 1 --snapshots --headless

# Check physical loading depth, full lowering, five-second heating, pop-up, and timer restoration
python scripts/tools/check_toast_cycle.py --headless

# Check action/pose conversions, cameras, lift, and one image BC update
python scripts/tools/check_make_toast_bimanual.py --headless --num_envs 2 --check_bc --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2

# Automatically collect successful demonstrations; choose a fresh output path
python scripts/imitation_learning/isaaclab_recorder/generate_make_toast_demos.py \
  --dataset_file ./datasets/make_toast_bimanual/dataset_v4.hdf5 \
  --motion_speed 2.0 --num_demos 10 --max_attempts 30 --headless

# Watch the collected 15-action demonstrations in Isaac Sim (B: pause, N: resume)
python scripts/imitation_learning/isaaclab_recorder/replay_demos.py \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --dataset_file ./datasets/make_toast_bimanual/dataset_v4.hdf5 \
  --num_envs 1 --enable_cameras

# Save an MP4 without opening a GUI: front overview above Head / Left wrist / Right wrist
python scripts/imitation_learning/isaaclab_recorder/replay_demos.py \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --dataset_file ./datasets/make_toast_bimanual/dataset_v4.hdf5 \
  --num_envs 1 --headless --enable_cameras \
  --video_file ./logs/make_toast_expert/replay_v4_front_center.mp4

# Teleop and record 
# TODO: add teleoperation code
# TODO: add domain randomization
python scripts/imitation_learning/isaaclab_recorder/record_demos.py \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 --teleop_device handtracking \
  --dataset_file ./datasets/make_toast_manual/dataset.hdf5 \
  --num_demos 10 --enable_cameras

# Annotate
python scripts/imitation_learning/isaaclab_mimic/annotate_make_toast_serving.py \
  --input_file ./datasets/make_toast_bimanual/dataset_v4.hdf5 \
  --output_file ./datasets/make_toast_bimanual/annotated_dataset_v4.hdf5

# Mimic data
python scripts/imitation_learning/isaaclab_mimic/generate_dataset.py \
  --device cuda --task Cyclo-Make-Toast-FFW-BG2-Bimanual-Mimic-v2 \
  --num_envs 20 --generation_num_trials 300 \
  --input_file ./datasets/make_toast_bimanual/annotated_dataset_v4.hdf5 \
  --output_file ./datasets/make_toast_bimanual/generated_dataset_v4.hdf5 --enable_cameras --headless

# Train
python scripts/imitation_learning/robomimic/train.py \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 --algo bc \
  --dataset ./datasets/make_toast_bimanual/dataset_v4.hdf5

# Play
python scripts/imitation_learning/robomimic/play.py \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 --num_rollouts 50 \
  --checkpoint /PATH/TO/desired_model_checkpoint.pth --horizon 6000 --enable_cameras
```

## Fixed v2 pilot scenarios (layout/reset only)

Three fixed IDs are defined in
`source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/scenario_pilots.json`:

| ID | Change from the original v2 calibration |
| --- | --- |
| `baseline` | Exact no-op on initial poses |
| `small_offset` | Shelf Y -15 mm, yaw -2 degrees; toaster Y +35 mm, yaw +2 degrees; plate X +15 mm |
| `swapped_candidate` | Shelf Y becomes +0.32 m, toaster Y becomes -0.30 m; plate stays between them |

Y order is in the environment frame, not the camera view. These are three
individual pilot layouts, not approved randomization ranges. Their geometry
evidence is the measured USD world AABBs in `logs/toast_recheck.P10wCH/report.json`
(SHA-256 recorded in the manifest). Measured XY sizes were approximately:
toaster 257.2 x 238.2 mm, shelf 83.5 x 316.6 mm, plate 194.3 x 194.3 mm.
The measured table-frame envelope is X [0.319, 1.081], Y [-1.33682, 1.13682] m.
This is NOT a verified usable tabletop polygon or collision-hull measurement.

The two changed candidates have separated conservative transformed object AABBs
inside that table envelope. The minimum object AABB gaps are 9.0 mm and 29.6 mm,
respectively; these are not gripper approach clearances. The baseline toaster
and plate AABBs overlap, which alone does not prove their actual shapes collide.
Reachability, supporting contact, collision-free motion and task success remain
**NOT TESTED**. Original expert completion is not a prerequisite for layout/reset
validation.

Set `cfg.scenario_id` after `parse_env_cfg()` and before `gym.make()`.
`MakeToastFFWBG2BimanualEnv.__init__` applies the layout before constructing the
scene. All four bread poses receive the same rigid transform about the original
shelf pivot, preserving the already scaled groove offsets. Existing default-state
reset restores the selected poses. The static shelf stays at its spawn pose.
Use a fresh cfg/environment to switch IDs; one ID is shared by all clones.
With `scenario_id=None`, existing behavior is unchanged.

Static checks (no Isaac Sim, installation, GPU or expert required):

```bash
python3 scripts/tools/test_make_toast_scenarios.py
python3 scripts/tools/check_make_toast_scenarios.py --scenario_id small_offset --static
```

Runtime check, inside the existing container after checking GPU availability:

```bash
cd /workspace/cyclo_lab
pilot_run=$(mktemp -d /workspace/cyclo_lab/logs/scenario_pilots.XXXXXX)
for scenario in baseline small_offset swapped_candidate; do
  /isaac-sim/python.sh scripts/tools/check_make_toast_scenarios.py \
    --scenario_id "$scenario" --headless --snapshots \
    --output_dir "$pilot_run/$scenario" || break
done
```

The diagnostic compares instantiated poses against cfg, holds the original
open-gripper/lift-zero action, deliberately perturbs bread_0, and checks two
resets with different seeds. It checks robot/object root states, robot/toaster
joints, static shelf pose and toast-cycle state. It preserves all terminations
and physics configuration, and does not run the expert or record demonstrations.
Each new output directory contains a JSON report and optional camera snapshots.
For GUI inspection, omit `--headless` and optionally use `--steps 250`; this is a
finite diagnostic, not an indefinite viewer. Runtime verification has not been
performed in the development session because Docker socket access was denied.

Existing success constraints are unchanged: `task_done()` still requires plate
X > 0.419 m and proximity to its configured default pose, and spare bread is
checked against the shelf cfg. These pilot plate X values satisfy that fixed
cutoff at spawn, but future layouts may conflict with it. Standby/lift conditions
and the expert's fixed hand roles/waypoints also remain unchanged.

### Existing expert failure evidence (closed without rerun or tuning)

`logs/toast_recheck.P10wCH` records v2, motion_speed 2.0, first attempt (reset seed
1), failure `bread_0_release_check_failed` at step 2817 / 112.68 simulation seconds.
These task/speed/seed choices match the README diagnostic and the first attempt
of the collection example. Check-only rendering differs from dataset collection.

Between `bread_0_lower_to_plate` (2715) and `bread_0_plate_release` (2745), bread_0
moved (-58.704, -15.894, -82.181) mm to (0.367838, 0.015705, 0.998417) m.
The plate moved (-1.059, +2.734, +5.229) mm. Left TCP moved approximately
(+1.229, -0.086, +2.058) mm and the left gripper joint magnitudes fell from
about 0.99–1.10 rad to at most 0.000102 rad. Over the following 72 steps the bread
position was effectively unchanged. The failure pose reports plate tilt ~6.71
degrees; its preceding full orientation is not in the regular phase metrics.

From the final pose matrices, the bread/plate relative normal alignment is
0.996687 (>0.94) and bread speed is 0.033638 m/s (<0.15): flatness and speed pass.
Therefore containment and/or the support-vertex height interval failed.
Exact hull containment/height values were not recomputed. The final head/wrist
snapshots show bread extending beyond the plate outline; gripper occlusion and
the absence of a bread–finger contact trace prevent attribution to finger snagging
versus impact/sliding during release. Zero reported robot–plate sensor force
does not imply zero bread–plate impact. The message's word "free" is not an
independent finger-contact test. No expert, physical setting or success threshold
was changed in response to this single failure.

## License

This repository is licensed under the **Apache 2.0 License**. See [LICENSE](LICENSE) for details.

### Third-party components

- **Isaac Lab**: BSD-3-Clause License, see [LICENSE-IsaacLab](LICENSE-IsaacLab)

## Fixed 100-candidate delivery (not yet GPU verified)

See [scenario batch instructions](scenarios/make_toast_v2_batch01/README.md),
[fixed final poses](scenarios/make_toast_v2_batch01/manifest.json),
[50/50 assignments](scenarios/make_toast_v2_batch01/assignments.csv), and
[planar preview](scenarios/make_toast_v2_batch01/preview.html).
The three pilot results in `logs/scenario_pilots.mlY0sM` were reused, not rerun.
The new 100 IDs are **candidates**, with no runtime, usable-tabletop or actual
robot-model verification yet. Six permutations meet the stated provisional
visual-box planning filters; this does not establish six feasible task orders.
The instructions include USD evidence extraction, fixed-pose auditing and an
isolated per-ID reset runner that records exit codes and continues after errors.
Neither model distance bounds nor heuristic IK are reported as reachability PASS.
Original physics, expert and completion criteria remain unchanged.
