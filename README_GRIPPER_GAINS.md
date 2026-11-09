> 현재 실행 진입점: [README_TOAST_QUEST.md](README_TOAST_QUEST.md). 아래 단계별 작업·측정 기록의 과거 값은 당시 설정입니다. 현재 v2 상승 목표/상한은 +35 mm이며 하한은 -45 mm입니다. 기록 속 PC IP·호스트 절대 경로·컨테이너 이름은 실행 환경에 맞게 설정해야 합니다. 최신 문서의 변수 기반 명령을 사용하세요.

현재 v2 속도 상한은 좌우 master joint1 모두 6.5 rad/s다(기존 2.2에서 변경).
slave 기본 속도와 gain 100/4는 유지했다. 상세 근거와 검증:
[README_GRIPPER_SPEED.md](README_GRIPPER_SPEED.md).

# v2 토스트 / Quest 그리퍼 gain 100/4

현재 `/home/mj/nrf_humanoid/cyclo_lab_mj`의
`Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2` 설정이다.

| 관절 | 역할 | stiffness | damping |
|---|---|---:|---:|
| gripper_l_joint1 | master, 유지 | 100.0 | 4.0 |
| gripper_l_joint2 | slave, 변경 | 100.0 | 4.0 |
| gripper_l_joint3 | slave, 변경 | 100.0 | 4.0 |
| gripper_l_joint4 | slave, 변경 | 100.0 | 4.0 |
| gripper_r_joint1 | master, 유지 | 100.0 | 4.0 |
| gripper_r_joint2 | slave, 변경 | 100.0 | 4.0 |
| gripper_r_joint3 | slave, 변경 | 100.0 | 4.0 |
| gripper_r_joint4 | slave, 변경 | 100.0 | 4.0 |

## 적용 경로 및 override 확인

- 공용 `assets/robots/FFW_BG2.py`의 slave 기본값 2/0.5는 다른 task에 영향을 주지 않도록
  그대로 두었다. master joint1은 원래부터 100/4이며 변경하지 않았다.
- `MakeToastFFWBG2BimanualEnvCfg`가 slave를 100/4로 설정한다.
- 기존에는 파생 `MakeToastFFWBG2BimanualServeEnvCfg`가 마지막에 2/0.5로 낮췄다.
  이 v2 override를 **100/4**로 바꿨다. 현재 v2 뷰어와 Quest 모두 이 설정을 사용한다.
- Quest `configure_slave_gains()`는 현재 여섯 slave 매핑과 100/4를 검증한다.
  다른 값이면 실행 전에 실패한다. 설정을 몰래 다시 쓰지 않는다.
- 이전 비교 옵션 `--gripper-slave-gains-official`은 2/0.5로 되돌리는 경로였으므로
  이제 명시적 오류를 내도록 했다. 현재 실행 명령에서는 이 옵션을 빼야 한다.
- 선택적 J1/J3 속도 비교 옵션은 최종 actuator를 복사하며 gain 100/4를 보존한다.
  기본 speed/effort 값과 VR 입력 매핑은 변경하지 않았다.
- 시작 reset 및 후속 reset의 기존 PhysX readback hook을 유지했다.
  기대값은 master와 slave 모두 100/4다. cfg가 2/0.5로 변경돼도 이를 기대값으로
  받아들이지 않는다. 각 관절 이름으로 실제 PhysX tensor를 조회하고 불일치 시 실패한다.
- 시뮬레이터가 이미 실행 중인 경우 이 변경을 hot reload하지 않는다.

## 변경 파일

- `source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/bimanual_env_cfg.py`:
  v2의 마지막 slave gain override만 100/4로 변경.
- `scripts/quest_diagnostic/teleop_slave_gains.py`:
  soft-gain override 거부, 설정 검증 및 엄격한 100/4 readback 기대값.
- `scripts/quest_diagnostic/teleop_toast.py`: 폐기한 옵션의 도움말 갱신.
- `scripts/quest_diagnostic/test_teleop_slave_gains.py`:
  최종 gain·옵션·reset·관절별 잘못된 readback 거부 검사 갱신.
- `scripts/quest_diagnostic/test_teleop_gripper_options.py`:
  J3 속도 비교 후 gain 기대값을 100/4로 변경.
- `README_QUEST.md`, `README_TOASTER_LED.md`, `README_BREAD_SLOT.md`:
  현재 gain 안내와 과거 2/0.5 기록의 구분.
- `README_GRIPPER_GAINS.md`: 이 보고서.

## 검증 결과

CPU 테스트 **13개 통과**:
실제 robot 설정 literal과 task override를 평가해 좌우 joint1~4의 최종 gain을 확인했다.
기본 Quest 설정이 값을 바꾸지 않음, 과거 soft override 거부, J1/J3 속도 옵션의 gain 보존,
시작/reset readback 호출 위치, 각 관절 stiffness/damping 불일치 거부를 검사했다.
readback 테스트의 PhysX tensor API는 **모의 객체**이며 실제 PhysX 조회 결과가 아니다.
Python 구문 검사 및 git diff --check 통과.

실제 GUI smoke는 Docker 소켓 접근 거부로 시작 전에 실패했다.
**실제 PhysX joint gain readback, GUI·Quest 제어 응답은 미검증**이다.
CPU 설정값을 실제 런타임 readback으로 보고하지 않는다.

증거:
- `logs/gripper_gains_100_4_validation/configured_gains.json` — CPU 최종 설정
- `logs/gripper_gains_100_4_validation/cpu_tests.log`
- `logs/gripper_gains_100_4_validation/gui_attempt.log`

새 거치대·빵 배치, 90% 레버 시작, 4초 가열, phase 기반 LED, 최근 가열 ID 기반 성공 조건,
VR 입력과 다른 관절 설정, 시나리오는 변경하지 않았다.
원본 `/home/mj/nrf_humanoid/cyclo_lab` 및 실행 중인 프로세스는 건드리지 않았다.
commit/push 없음.

## 실행 / 재검증

기존 수정본 명령을 그대로 사용하되 `--gripper-slave-gains-official`은 넣지 않는다.
GUI와 Quest 전체 명령은 [README_TOASTER_LED.md](README_TOASTER_LED.md) 참조.
새 프로세스에서 적용된다.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
python3 -m unittest discover -s scripts/quest_diagnostic -p 'test_teleop*py'

DISPLAY=:1 XAUTHORITY=/run/user/1000/gdm/Xauthority \
./scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --operator operator_B --scenario_index 1
```

Quest 시작/reset에서 `GRIPPER_RUNTIME_OK` 로그의 joint_names/stiffness/damping을 확인할 수 있다.
이 로그는 actual PhysX readback이 기대값을 통과했을 때만 출력된다.
