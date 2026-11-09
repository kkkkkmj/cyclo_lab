> **과거 작업 기록**: 원래 설명·수치·실행 결과를 보존한 자료이며 현재 실행 안내가 아닙니다. 최신 설정과 명령은 [Changes](../../../CHANGES.md)를 따르세요. 특히 2/0.5 gain은 원본 v2 기본값이 아니라 중간 비교 설정이며, 거치대 안정 지지와 실기 검증 주장은 최신 진단 상태와 함께 읽어야 합니다. 본문의 호스트 경로·logs는 당시 로컬 증거 위치입니다.

> 현재 실행 진입점: [README_TOAST_QUEST.md](../../../CHANGES.md). 아래 단계별 작업·측정 기록의 과거 값은 당시 설정입니다. 현재 v2 상승 목표/상한은 +35 mm이며 하한은 -45 mm입니다. 기록 속 PC IP·호스트 절대 경로·컨테이너 이름은 실행 환경에 맞게 설정해야 합니다. 최신 문서의 변수 기반 명령을 사용하세요.

# v2 서빙 성공 조건 — 임의의 가열 완료 빵 한 개 이상

수정 대상은 `/home/mj/nrf_humanoid/cyclo_lab_mj`의 현재 v2 serving task다.
연구실 원본, 실행 중인 프로세스, 거치대·빵 초기 배치·Quest 입력·관절 gain·시나리오·A/B
배정은 수정하지 않았다. commit/push 없음. 접시가 없는 이전 non-serving task는 기존 조건을 유지한다.

## 실제 asset 검사와 중심 허용 반경

프로젝트의 `robodojo_make_toast/bread/object.usdz` 및 `plate/object.usdz`를 pxr로 열고
내부 transform을 반영해 측정했다. 빵 실제 크기는 약 116.948 × 116.062 × 11.799 mm다.

빵 root는 형상 중심이 아니다. 형상 중심은 **실제 visual convex hull의 AABB 중점**으로 정의한다.
root-local 좌표는 `(0.0000864230, -0.0002499074, 0.0056075576) m`이다.
질량 중심이라고 가정하지 않는다. `bread_geometry_center()`가 실제 asset의 정점에서 계산한다.

접시 scale `(1.5,1.5,.22)`를 반영한 XY 윤곽의 내접 반경은 `0.0967231746 m`이다.
빵 형상 중심 기준 최대 XY 반경은 약 `0.0750437343 m`, 최대 3D 반경은 `0.0750439491 m`이다.
회전·기울기에도 보수적인 3D 반경을 사용하여,

`0.020 + 0.0750439491 = 0.0950439491 < 0.0967231746 - 0.0005`

가 되도록 중심 허용 반경을 **20 mm**로 정했다. 기존 테두리 여유 0.5 mm를 제외하고도
약 1.18 mm 여유가 남는다. 기존 전체 정점용 반경 `0.0962231746 m`를 중심 반경으로 재사용하지 않았다.
이 반경은 `assets.py`의 명시적 설정값 `SERVING_BREAD_CENTER_RADIUS = .020`으로 관리한다.

현재 접시 pose를 기준으로 빵 root pose를 상대 변환한 뒤, 빵 회전을 적용한 형상 중심을 더한다:

```
center_plate_local = relative_bread_position + relative_bread_rotation @ geometry_center
sqrt(center_plate_local.x**2 + center_plate_local.y**2) < SERVING_BREAD_CENTER_RADIUS
```

XY만 중심점 검사로 변경했다. 높이 검사에는 계속 실제 모든 hull 지지 정점을 사용한다.

## 빵별 가열 완료 이력

기존 `ToastCycle.state()`와 recorder에는 phase·elapsed·command·previous_pressed·heating_time만
있었으며 빵별 가열 이력은 없었다. 환경별로 두 개의 bool `[num_envs,4]` 기록을 추가했다.

- `heating_present`: 가열 phase 진입 시 정상 적재된 ID를 설정한다. 가열 중 매 제어 갱신에서
  기존 bread_in_slot 검사를 재사용하며, 한 번이라도 빠지거나 자세/위치 조건을 벗어난 ID는
  해당 사이클에서 무효로 유지한다. 재삽입해도 되살리지 않는다.
- `heated_bread`: 4초 가열 완료로 상승을 시작할 때 끝까지 유효했던 ID만 기록한다.

따라서 시작 순간만 적재했다가 가열 전에 꺼낸 빵, 가열 중 제거/재삽입한 빵, 늦게 들어온 빵은
완료로 기록하지 않는다. 어느 슬롯이든 허용하지만 정상 적재가 모든 가열 갱신에서 유지되어야 한다.
실제 열전달 모델은 아니며 **기존 정상 적재 판정 + 4초 가열 상태**의 이력이다.
검사 해상도는 기존 제어 주기(기본 약 40 ms)이다. 제어 샘플 사이의 순간 이탈까지 증명하지 않는다.

reset 시 두 기록 모두 초기화한다. 기존 recorder의 state()/restore() 경로에 함께 저장·복원한다.
새 기록은 기존 scalar 상태의 shape를 바꾸지 않고 별도 `[N,4]` key로 추가한다.
이 필드가 없는 과거 recording을 복원하면 증거가 없으므로 두 기록을 false로 처리한다.
과거 phase/타이머만으로 가열 ID를 추정하지 않는다. action/observation 차원은 변경하지 않았다.

## 최종 성공 조건 전체

아래 조건을 **모두** 만족해야 한다. 빵 항목은 네 빵 중 **동일한 한 개 이상**이 모두 만족해야 한다.

| 구분 | 정확한 조건 |
|---|---|
| 빵 대상 | bread_0, bread_1, bread_2, bread_3 중 하나 이상 |
| 해당 빵 가열 | 해당 ID의 heated_bread=true: 가열 진입부터 4초 종료까지 정상 적재 이력 |
| 해당 빵 XY | 현재 접시 좌표계의 형상 중심 거리 d_xy < 0.020 m |
| 해당 빵 높이 | 접시 로컬에서 모든 지지 정점의 min Z > −0.002 m, max Z < 0.050 m (기존 유지) |
| 해당 빵 기울기 | 접시 상대 회전의 abs(R[2,2]) > 0.94 (기존 유지) |
| 해당 빵 선속도 | world 선속도 norm < 0.15 m/s (기존 유지) |
| 다른 빵 | 성공 판정에서 위치·속도·거치대 잔류를 요구하지 않음 |
| 접시 자세 | world 회전 R[2,2] > 0.985 |
| 접시 위치 | 초기 위치 대비 환경 상대 XY 이동 norm < 0.025 m, 환경 상대 X > 0.419 m |
| 사이클 완료 | 해당 환경 phase=4 |
| 레버 복귀 | 기존 lever_pressed=false, 즉 실제 눌림 비율 < 0.85 (시작 임계값 0.90과 별개) |
| 그리퍼 | 좌우 gripper joint1 각각 < 0.15 |
| 팔 대기 | 양쪽 arm_link7 각각 기준 standby에서 거리 < 0.04 m. 좌측 (0.3609426,0.3954084,1.4419125), 우측 Y 부호 반전 |
| lift | abs(lift_joint) < 0.02 m |

**높이 판정의 기존 한계:** 접촉력/지지 여부를 직접 검사하지 않는다. 접시 로컬 중심 높이
0.10 m의 공중 빵은 실패하지만, 0.025 m에서 낮게 떠 있어도 지지 정점 높이·기울기·속도 조건을
만족하면 통과할 수 있다. 요청대로 기존 높이·기울기·속도 조건을 유지했으므로 이 경우를
막는 별도 contact 조건은 추가하지 않았다. ‘실제 접촉 지지까지 검증 완료’로 해석하면 안 된다.

**별도 종료 조건:** 기존 `bread_dropping`(네 빵 중 root Z<0.75 m가 있으면 episode 종료)과
시간 제한 등은 성공 predicate와 별개로 유지했다. 다른 빵을 거치대 밖에 둬도 성공 predicate는
허용하지만, 떨어뜨려 기존 종료 조건을 일으키면 실제 episode는 종료될 수 있다.

## 보존한 토스터 동작

네 빵 중 하나 정상 적재 + 대기 상태 + 실제 레버 90% 진입으로 시작한다.
하강 최소 0.60초/위치 1.5 mm/속도 0.01 m/s 조건 후 가열 phase에 진입하고 그때부터 4초를 센다.
하강·가열 LED ON, 상승 시작 OFF, 대기·완료·reset OFF.
기존 상승 보간/캐리지 +15 mm 목표/레버 복귀 목표 및 상승 완료 조건은 변경하지 않았다.

## 변경 파일

공통 config 경로:
`source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/`

| 파일 | 변경 내용 |
|---|---|
| assets.py | SERVING_BREAD_CENTER_RADIUS=0.020 명시 |
| bread_geometry.py | 실제 hull의 형상 중심 계산 추가 |
| toast_cycle.py | 빵별 가열 유효/완료 bool 기록, reset·저장·복원 연결 |
| bimanual_mdp.py | XY 중심 검사, 동일 가열 ID의 OR 성공, serving에서 나머지 빵 제약 제거 |
| scripts/tools/test_toast_serving_success.py | 실제 predicate/cycle/asset 기반 CPU 검증 |
| README_TOASTER_LED.md | 현재 성공 조건 안내 갱신 |
| README_TOAST_SUCCESS.md | 본 보고서 |

## 검증과 미검증

CPU 테스트 22개 통과(기존 cycle/LED 11 + 새 serving/가열 이력 11).

- 네 빵 각각 단독 가열 완료 및 단독 접시 배치 성공.
- 가열 ID와 배치 ID 불일치/생빵 실패.
- XY 경계 안/정확한 경계/밖, 접시 이동·yaw 및 빵 yaw에 따른 로컬 좌표 검사.
- 실제 root 중심 offset 및 반경 여유 계산.
- 높은 공중/너무 낮은 위치/기울기/속도 실패. 낮은 공중 상태의 기존 허용 한계도 명시적 검사.
- 가열 전 제거, 중간 제거/재삽입, 늦은 투입 실패.
- 타이머 4초/LED 유지, 가열 중 및 완료 상태 저장·복원, 과거 기록의 증거 없는 복원 거부.
- reset/부분 환경 reset으로 가열 기록 초기화, 다른 환경 기록 보존.
- 나머지 빵의 임의 위치·속도에도 선택된 가열 빵으로 성공 가능.
- 접시/팔/그리퍼/lift/레버/cycle 완료 조건의 실패 사례 확인.

테스트는 실제 USD와 함수 본문을 사용했지만 scene I/O와 좌표 연산 fixture는 CPU 모의 환경이다.
실제 PhysX 적분/열전달/접촉/RTX는 실행하지 않았다.
GUI smoke는 Docker 소켓 접근 거부로 시작 전에 실패했다.
**실제 PhysX·GUI·Quest 및 실제 집기/접시 배치 성공은 미검증**이다.
로그: `logs/toast_serving_success_validation/{success_tests,cycle_led_tests,gui_attempt}.log`.

CPU 재검증:

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
/home/mj/hand-sim-conda/bin/python scripts/tools/test_toast_serving_success.py
/home/mj/hand-sim-conda/bin/python scripts/tools/test_toaster_led.py
```

GUI/Quest 실행은 기존 `scripts/run_mj.sh --gui ...`를 그대로 사용한다.
전체 명령은 [README_TOASTER_LED.md](TOASTER_LED.md)의 실행 방법 참조.
