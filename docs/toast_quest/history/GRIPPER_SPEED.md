> **과거 작업 기록**: 원래 설명·수치·실행 결과를 보존한 자료이며 현재 실행 안내가 아닙니다. 최신 설정과 명령은 [Changes](../../../CHANGES.md)를 따르세요. 특히 2/0.5 gain은 원본 v2 기본값이 아니라 중간 비교 설정이며, 거치대 안정 지지와 실기 검증 주장은 최신 진단 상태와 함께 읽어야 합니다. 본문의 호스트 경로·logs는 당시 로컬 증거 위치입니다.

> 현재 실행 진입점: [README_TOAST_QUEST.md](../../../CHANGES.md). 아래 단계별 작업·측정 기록의 과거 값은 당시 설정입니다. 현재 v2 상승 목표/상한은 +35 mm이며 하한은 -45 mm입니다. 기록 속 PC IP·호스트 절대 경로·컨테이너 이름은 실행 환경에 맞게 설정해야 합니다. 최신 문서의 변수 기반 명령을 사용하세요.

# v2 토스트·Quest master 속도 상한 6.5 rad/s

수정은 `/home/mj/nrf_humanoid/cyclo_lab_mj`에서만 진행했다. 원본 cyclo_lab과 실행 중인
프로세스는 건드리지 않았다. commit/push 없음.

## 확인한 출처와 적용 순서

1. 현재 토스트가 상속하는 robot은 `FFW_BG2_WITHOUT_MIMIC_CFG`이며 asset은
   `source/cyclo_lab/data/robots/FFW/FFW_BG2_without_mimic.usd`다.
2. 해당 USD의 좌우 joint1~4 모두 `physxJoint:maxJointVelocity=372.42254638671875 deg/s`,
   약 6.5 rad/s다. 각 prim의 위치 제한도 조회해 로그로 남겼고 USD는 수정하지 않았다.
3. 공용 Python `assets/robots/FFW_BG2.py`의 `gripper_master.velocity_limit_sim=2.2`가
   USD 기본값을 덮어쓰므로 수정 전 v2의 좌우 master 최종 설정은 **2.2 rad/s**였다.
4. 다른 task를 바꾸지 않도록 공용 robot은 그대로 두고,
   `MakeToastFFWBG2BimanualServeEnvCfg.__post_init__`에
   `self.scene.robot.actuators["gripper_master"].velocity_limit_sim = 6.5`를 추가했다.
   이 그룹은 정확히 좌우 joint1을 대상으로 한다.
5. IsaacLab articulation은 actuator의 `velocity_limit_sim`을
   `write_joint_velocity_limit_to_sim` → PhysX `set_dof_max_velocities`로 전달한다.
   VR 손 이동 배율이나 관절 목표 속도를 수정한 것이 아니다.
6. Quest의 기존 `--right-gripper-j1-speed-6p5` 옵션도 오른쪽을 6.5로 설정하므로
   현재 기본 설정에서 관절별 수치 변화는 없다. 옵션 도움말과 테스트를 갱신했다.
   다른 master 속도 override/reset 쓰기 경로는 현재 v2·Quest 경로에서 발견하지 않았다.

## 최종 기본 설정

| 관절 | 속도 상한(rad/s) | stiffness/damping | effort 설정 |
|---|---:|---|---:|
| gripper_l_joint1 | 6.5 (2.2에서 변경) | 100/4 | 30 |
| gripper_r_joint1 | 6.5 (2.2에서 변경) | 100/4 | 30 |
| 좌우 joint2·3·4 | 약 6.5, 기존 USD 유지 | 100/4 | 20 |

slave의 Python `velocity_limit_sim=None`은 그대로이며 기존 USD 값을 상속한다.
기존 명시적 `--right-gripper-j3-speed-2p2` 비교 옵션은 변경하지 않았다.
이 옵션을 선택한 경우에만 오른쪽 joint3은 예전처럼 2.2이며 master는 둘 다 6.5다.
기본 실행에는 이 옵션이 없다.

**6.5 rad/s는 시뮬레이션 속도 상한이지 실제 관절이 항상 그 속도로 움직인다는 뜻이 아니다.**
실제 속도는 위치 오차·부하·접촉·effort·servo 응답 등에 따라 달라진다.

## 변경 파일

- `source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/bimanual_env_cfg.py`:
  v2 좌우 master의 velocity_limit_sim만 6.5로 설정.
- `scripts/quest_diagnostic/teleop_slave_gains.py`: 기본 PhysX 속도 readback 기대값을 좌우 master 모두 6.5로 변경.
- `scripts/quest_diagnostic/teleop_toast.py`: 기존 오른쪽 master 비교 옵션의 도움말 갱신.
- `scripts/quest_diagnostic/test_teleop_gripper_options.py`: 실제 v2 override 평가 및 속도 기대값 갱신.
- `scripts/quest_diagnostic/test_teleop_slave_gains.py`: 모의 readback 속도값·관절별 불일치 거부 검사 갱신.
- `README_QUEST.md`, `README_GRIPPER_GAINS.md`, `README_GRIPPER_SPEED.md`: 현재 설정 안내.

## 검증 및 한계

CPU 테스트 **13개 통과**. 실제 설정 소스 literal과 v2 override를 평가해 변경 전후를 비교했다.
최종 actuator 설정의 차이는 아래 두 항목뿐이었다:

- gripper_l_joint1.velocity_limit_sim: 2.2 → 6.5
- gripper_r_joint1.velocity_limit_sim: 2.2 → 6.5

모든 gain, slave 속도, effort, 팔·head·lift 설정은 이 비교에서 동일했다.
관절 위치 제한을 정의한 USD는 수정하지 않았다.
시작/reset readback은 기본 모든 그리퍼 속도 상한 6.5를 확인하며,
기존 명시적 J3 비교 옵션의 2.2도 구분한다. 관절별 잘못된 속도·gain을 거부하는 모의 테스트를 통과했다.

실제 GUI smoke는 Docker 소켓 접근 거부로 시작 전에 실패했다.
**실제 PhysX readback, 실제 속도/접촉 응답, GUI·Quest 실기는 미검증**이다.
새 거치대·90% 시작·4초 가열·LED·성공 조건·VR 입력은 변경하지 않았다.

증거: `logs/gripper_master_speed_validation/`의 `before.json`, `config_delta.json`,
`usd_limits.json`, `tests.log`, `gui_attempt.log`.

새로 실행하는 v2 viewer/Quest에 기본 적용되므로 추가 옵션이 필요 없다.
기존 프로세스는 재시작하지 않았으며 자동으로 값이 바뀌지 않는다.
GUI/Quest 실행 명령은 [README_TOASTER_LED.md](TOASTER_LED.md) 참조.
