> **과거 작업 기록**: 원래 설명·수치·실행 결과를 보존한 자료이며 현재 실행 안내가 아닙니다. 최신 설정과 명령은 [Changes](../../../CHANGES.md)를 따르세요. 특히 2/0.5 gain은 원본 v2 기본값이 아니라 중간 비교 설정이며, 거치대 안정 지지와 실기 검증 주장은 최신 진단 상태와 함께 읽어야 합니다. 본문의 호스트 경로·logs는 당시 로컬 증거 위치입니다.

> 현재 실행 진입점: [README_TOAST_QUEST.md](../../../CHANGES.md). 아래 단계별 작업·측정 기록의 과거 값은 당시 설정입니다. 현재 v2 상승 목표/상한은 +35 mm이며 하한은 -45 mm입니다. 기록 속 PC IP·호스트 절대 경로·컨테이너 이름은 실행 환경에 맞게 설정해야 합니다. 최신 문서의 변수 기반 명령을 사용하세요.

# 토스터 네 빵 적재 대상 / 4초 가열 / 자동 사이클 LED — 2026-11-08

현재 동작을 설명하는 문서다. 이전의 “레버 90% 이상이면 LED ON” 규칙은 제거했다.
수정 저장소는 `/home/mj/nrf_humanoid/cyclo_lab_mj`이며 연구실 원본은 수정하지 않았다.
실행 중인 다른 작업은 중단하지 않았으며 commit/push 없음.

## 조건 변경

최근 수정: 자동 시작에 사용하는 `pressed = ratio >= .95`만 `.90`으로 변경했다.
다른 용도의 0.95, phase 기반 LED, 4초 가열, 전체 성공 조건은 변경하지 않았다.
이번 변경 파일은 toast_cycle.py, scripts/tools/test_toaster_led.py, 이 보고서다.
검증 로그: `logs/toaster_start_90_validation/cpu_tests.log`.
실제 PhysX·GUI·Quest는 이번 변경에서도 실행하지 않아 미검증이다.

이전에는 bread_0 또는 bread_1만 작동 대상이었다.
이제 네 빵×두 슬롯의 기존 판정 중 **하나 이상** 참이면 적재 조건을 만족한다.

- bread_0이 슬롯 0 또는 슬롯 1에 정상 적재됨
- bread_1이 슬롯 0 또는 슬롯 1에 정상 적재됨
- bread_2가 슬롯 0 또는 슬롯 1에 정상 적재됨
- bread_3이 슬롯 0 또는 슬롯 1에 정상 적재됨

`bread_in_slot`의 위치·높이·자세 조건은 그대로다. 작동 대상만 확대했으며 공유 판정 함수 자체는 수정하지 않았다.
적재 조건과 함께 기존 `phase==0`, 실제 레버 눌림 비율 `>=0.90`, 직전 pressed=false가
필요하다. 누른 채 나중에 빵을 넣은 경우 새 눌림 진입 전에는 시작하지 않는다.
빵 두 개가 서로 다른 슬롯에 들어 있어도 정상 시작한다.

시작 이후에는 두 빵의 적재 여부를 요구하는 전이 조건이 없으므로 추가 완화하지 않았다.
시작 후 빵이 사라져도 기존처럼 cycle 자체는 진행한다. 새 취소 조건을 추가하지 않았다.

## 실제 phase와 LED

| phase | 의미 | LED |
|---|---|---|
| 0 | 대기 | OFF |
| 1 | 캐리지 하강 | ON |
| 2 | 가열 | ON |
| 3 | 상승 | OFF |
| 4 | 완료 | OFF |

`toast_cycle.phase`를 그대로 읽는다. 시작 조건을 LED 쪽에 복제하지 않는다.
실제 시작으로 phase가 1이 되는 update 직후 ON, 가열 종료로 phase가 3이 되는 update
직후 OFF를 적용한다. 갱신된 재질은 다음 렌더에 나타나며 이미 캡처한 프레임은 바꾸지 않는다.
레버가 90% 이상이어도 phase=0이면 OFF다. 하강/가열 중 레버의 작은 변동은 LED에 영향을 주지 않는다.
자동 cycle 없는 환경은 OFF다. 기존 코드에는 별도 취소 경로가 없고 정상 reset이 phase를 0으로
초기화하여 OFF로 만든다. 기록 복원(reset_to)은 복원된 실제 phase에 맞춰 표시한다.

## 유지한 시간·동작·성공 조건

- 레버 비율은 기존과 같이 실제 joint_1 위치와 런타임 한계에서 계산:
  `(q_actual-q_up)/(q_down-q_up)`. asset 한계는 약 −0.0138~+0.0642 m.
- 하강 stroke 45 mm, 최소 0.60초, 목표 위치 오차 1.5 mm 미만,
  실제 캐리지 속도 0.01 m/s 미만일 때 가열 시작.
- phase=2 진입 때 elapsed=0. 이후 `env.step_dt`로 누적한 **시뮬레이션 시간 4초**
  (`elapsed >= 4.0`)에 도달하는 첫 update에서 상승한다. 4초 미만에 상승하지 않도록
  기존 1e−5 조기 허용치를 제거했다. 벽시계를 사용하지 않는다.
- 상승 보간 시간 0.80초, v2 캐리지 목표 +15 mm. 레버 목표는 완전히 올라온 lower limit.
- 상승 완료는 0.92초 이상 및 캐리지 목표 오차 1.5 mm 미만. 기존과 같다.
- **현재 v2 task의 빵 성공 조건:** 네 빵 중 하나 이상이 동일 ID로 가열을 완료하고
  접시에 중심 반경·기존 높이·기울기·속도 조건을 만족해야 한다.
  bread_0/1 모두 접시에 있어야 하는 조건과 bread_2/3 거치대 잔류 조건은 제거했다.
  빵 외 조건과 레버/LED/4초 가열 동작은 유지했다.
  상세 조건·가열 이력·검증 한계는 [README_TOAST_SUCCESS.md](TOAST_SUCCESS.md) 참조.


새 거치대와 빵 배치, Quest 입력, slave gain 100.0/4.0, master/팔 설정,
100개 시나리오와 A/B 배정 및 action/observation 차원은 변경하지 않았다.

## LED 형상과 환경별 분리 — 유지

- prim: `/World/envs/env_N/Toaster/base/LeverPressLED/Lens`
- base 로컬 중심 `(0.1027,−0.045,0.050) m`, +X 레버 면의 왼쪽 위.
- 지름 8 mm, 두께 1.2 mm, 표면에서 약 1.1 mm 돌출.
- OFF 짙은 회색 `(0.025,0.025,0.025)`, emission=0.
- ON 초록 `(0.01,0.8,0.025)`, emission `(0.01,1.2,0.025)`.
- 환경마다 독립된 Material/Shader. 충돌체·질량·관절·별도 광원 없음.
- 기존 공통 환경의 생성/step/reset/reset_to/render 갱신 경로를 유지했다.

## 이번 수정 파일

아래 config prefix는
`source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/`이다.

| 파일 | 변경 이유 |
|---|---|
| toast_cycle.py | 네 빵×두 슬롯 판정 OR 결합, 가열 4초 및 엄격한 경계 |
| bimanual_env_cfg.py | 4초 가열에 맞게 설명 문자열만 수정 |
| scripts/tools/check_toast_cycle.py | 기존 실행 검사의 하드코딩 5초를 cycle.HEATING_SECONDS 참조로 교체 |
| scripts/tools/test_toaster_led.py | 한 개/두 개/없음, 실제 cycle 진행 및 phase 기반 재질 검사 |
| README_TOASTER_LED.md | 현재 규칙과 검증 결과로 갱신 |

## 검증

CPU 테스트 **11개 통과**. 실제 ToastCycle 함수에 fake scene I/O를 연결하고 USD는 실제
로컬 asset을 읽었다. 물리 적분과 렌더러를 실행한 테스트는 아니다.

- 빵 없음 + 90%/95%/100% 진입: 시작 안 함, OFF.
- 경계 검사: 89.9999%에서 대기/OFF, 90%에서 시작/ON.
- float32 실제 위치의 임계값 직전/직후 인접 표현값도 검사했다. 초기 테스트의
  역변환 반올림 문제는 fixture에서 보정했으며 실행 코드에 epsilon을 추가하지 않았다.
- bread_0~bread_3 각각만 슬롯 0/1에 적재한 여덟 조합:
  89%에서는 대기/OFF, 90% 진입 시 시작/ON.
- 두 빵이 서로 다른 슬롯에 있는 두 순서 및 bread_2+3도 시작/ON.
- 실제 기존 적재 함수와 캐리지 높이 wrapper로 8개 조합과 X/Y/Z 이탈·잘못된 자세 검사.
- 누른 채 적재 상태만 바꿔도 시작 안 함; 재진입 필요.
- 한 개로 시작 후 레버 변동/적재 소실에도 기존 하강·가열 진행, ON 유지.
- 하강 최소 시간/속도 조건, 가열 진입 시 timer=0, 3.96초에는 가열,
  추가 0.04초에 상승/OFF; 3.99999초 근처와 4초 초과 첫 update도 검사, 기존 상승 목표/완료 확인.
- reset OFF 및 다시 적재/누름으로 시작/ON.
- 실제 공통 환경 LED hook의 phase 전달 및 cycle 없는 환경 OFF 확인.
- clone 상속 환경 간 독립 재질, 중복 prim 없음, 이동/회전 추종,
  LED 하위 physics API 없음 확인.
- 변경 Python 구문 검사와 git diff --check 통과.

GUI smoke를 별도 컨테이너로 시도했으나 Docker 소켓 접근 거부로 시작 전에 실패했다.
**실제 PhysX·GUI·RGB·Quest 검증과 실제 화면 캡처는 미검증**이다.
로그: `logs/toaster_four_bread_4s_validation/cpu_tests.log`, `gui_attempt.log`.

## 실행 방법

현재 데스크톱 값은 DISPLAY=:1, Xauthority=/run/user/1000/gdm/Xauthority.
다른 로그인 세션에서는 그 세션의 값을 사용한다. `--gui`는 DISPLAY, X11 socket,
Xauthority read-only mount, HEADLESS=0, LIVESTREAM=0을 전달한다. `--headless`는 넣지 않는다.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
DISPLAY=:1 XAUTHORITY=/run/user/1000/gdm/Xauthority \
./scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --operator operator_B --scenario_index 1
```

viewer는 초기 배치 확인용이다. R로 reset하며, 시작 전 LED는 OFF다.
직접 빵과 레버를 조작하려면 기존 Quest 입력 서버/bridge를 사용해 다음을 실행한다.

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

GUI 없이 기존 Quest RGB preview만 쓰려면 `--gui`를 빼고 기존 `--headless`를 유지한다.
LED 전용 옵션은 없다. 새 환경 프로세스에서 공통 코드가 적용된다. 이 작업에서는
실행 중인 프로세스를 재시작하거나 hot reload하지 않았다.

```bash
# CPU 재검증
cd /home/mj/nrf_humanoid/cyclo_lab_mj
/home/mj/hand-sim-conda/bin/python scripts/tools/test_toaster_led.py
```
