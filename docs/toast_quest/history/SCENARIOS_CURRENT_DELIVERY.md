> 과거 안내/생성 기록 보존본입니다. 현재 공유 안내는 [Changes](../../../CHANGES.md)와 [현재 시나리오](../../../scenario_delivery/v20261108_current_100/README.md)를 따르세요. 아래 개인 경로·실행 결과는 당시 기록이며 최신 설정을 뜻하지 않습니다.

# 현재 토스트 환경용 새 시나리오 100개 — v20261108_current_100

생성 작업 시작일을 버전명에 사용했다. 기존 `scenario_delivery`의 manifest/배정표를 보존하고 이 하위 폴더에 독립적인 100개를 생성했다. 새 목록은 **명시적으로 manifest를 지정해야** 선택된다. 기본 목록은 기존 목록 그대로다.

## 근거와 기존 방식

요청한 GitHub branch 페이지 및 raw 자료 접근이 실패(cache miss)하여 원격과 로컬의 동일성은 확인하지 못했다. 근거는 로컬 `scenario_delivery/{manifest.json,manifest_bread_slot.json,assignments.csv}`와 `/home/mj/nrf_humanoid/toast_minimal_c73kwi_y/files/scripts/tools/`의 이전 생성기/기하 도우미다. 사용한 이전 생성기와 도우미는 `inputs/reference_*.py`에 보관했다.

기존 방식은 toaster / plate / bread_shelf를 +Y에서 −Y로 놓는 6개 순열, 종류별 17/17/17/17/16/16개, seed 20261102, 종류 안에서 A/B 교대 배정이었다. 하위 그룹은 없었다. X 앵커는 토스터 .55m, 접시 .49m, 거치대 .46m이며 Y 앵커는 +.4/0/−.4m. X 변화는 토스터/거치대 ±15mm, 접시 ±10mm, Y 변화는 모두 ±15mm, yaw는 기준 토스터150°/접시0°/거치대−90°에서 ±5°. Z는 현재 기준 배치를 유지한다.

기존 제외 기준은 테이블 가장자리 20mm, 형상/메타데이터 오차 여유 1mm, 충돌 여유 30mm, 접근 여유 60mm, 접시 X>.419m, 중복 배치 제외, 로봇 링크 길이에 기반한 거리 상한 필터였다. 링크 길이 필터는 IK/로봇 충돌/집기 검증이 아니다.

새 생성은 seed **20261108**, 배정 seed **20261109**, 종류별 Latin hypercube 표본과 유효성 검사 후 배정이다. 모든 100개가 새 pose이며 이전 두 manifest와도 동일 pose가 없다. native 230×130×45mm 거치대와 네 빵을 실제 USD에서 검사한 결과 기존 허용 범위 및 제외 여유를 유지할 수 있어 범위를 바꾸지 않았다. 이 seed에서는 100개 후보 모두 통과해 재시도/제외는 0개였다. 부적합 후보는 생성기가 제외하고 다시 뽑으며 기준을 완화하지 않는다.

## 저장 파일

- `manifest.json`: 100개 ID, 상위 operator/그룹/두 순번, 모든 7개 물체(toaster, plate, bread_shelf, bread_0~3)의 pose/scale, 기하 검사, 소스/asset SHA256.
- `poses.csv`: 전체 700개 물체 초기 pose. quaternion은 wxyz, 거리 m.
- `assignments.csv`, [ASSIGNMENTS.md](../../../scenario_delivery/v20261108_current_100/ASSIGNMENTS.md): 전체 배정표. 그룹1은 상위 순번1~25, 그룹2는26~50. 구 목록의 같은 순번과 같은 배치라는 의미는 아니다.
- [overview.svg](../../../scenario_delivery/v20261108_current_100/overview.svg): 100개 위쪽 정적 배치도(주황 토스터, 파랑 접시, 초록 거치대+빵 외곽). 시뮬레이터 화면이 아니다.
- `generation_config.json`: seed, 범위, 종류별 할당량과 분포 균형화 방식.
- `distribution.json`: 각 그룹 및 A/B의 모든 위치/회전/거리 지표 min/max/mean/std/p25/median/p75.
- `validation.json`, `cpu_tests.log`, `reproducibility.json`: 정적 검사, CPU 테스트, 8개 생성 산출물의 바이트 단위 재현성.
- `inputs/geometry_evidence.json`: 이전에 추출된 테이블 지지 다각형/로봇 링크 모델. 현재 robot USD SHA256 일치 확인. 과거 FK 검증 표시를 재사용했으며 이번 실행의 FK/PhysX 검증으로 취급하지 않는다.

## 종류별 배정

순서는 +Y → −Y이며 S=bread_shelf, T=toaster, P=plate.

| 종류 | A_1 | A_2 | B_1 | B_2 | A | B | 합계 |
|---|---:|---:|---:|---:|---:|---:|---:|
| T > P > S | 5 | 4 | 4 | 4 | 9 | 8 | 17 |
| T > S > P | 4 | 4 | 5 | 4 | 8 | 9 | 17 |
| P > T > S | 4 | 5 | 4 | 4 | 9 | 8 | 17 |
| P > S > T | 4 | 4 | 4 | 5 | 8 | 9 | 17 |
| S > T > P | 4 | 4 | 4 | 4 | 8 | 8 | 16 |
| S > P > T | 4 | 4 | 4 | 4 | 8 | 8 | 16 |
| 합계 | 25 | 25 | 25 | 25 | 50 | 50 | 100 |

각 종류에서 A/B 차이 ≤1, A_1/A_2 및 B_1/B_2 차이 ≤1을 고정했다. 50,000회의 seed 고정 종류 내 교환으로 signed XY 변화, 변화 크기, yaw/절대 yaw, 기준 배치로부터 변위, 로봇 원점 거리, 작업 probe와 어깨 거리의 표준화 평균·2차 모멘트·사분위 점유 편차를 함께 줄였다. 그룹 실행 순서는 종류를 교차하도록 섞었다. 이는 **배치 분포의 균형**이며 실제 조작 난이도의 동등성을 검증한 결과는 아니다.

| 그룹 | 평균 XY jitter T/P/S (mm) | 평균 절대 yaw 변화 T/P/S (°) | 평균 최대 probe–어깨 거리 (m) |
|---|---|---|---:|
| operator_A_1 | 11.45/9.55/11.40 | 2.46/2.46/2.63 | 0.6229 |
| operator_A_2 | 11.73/9.14/11.21 | 2.57/2.54/2.46 | 0.6191 |
| operator_B_1 | 11.60/9.66/11.55 | 2.47/2.45/2.49 | 0.6234 |
| operator_B_2 | 11.16/9.75/11.24 | 2.45/2.58/2.45 | 0.6215 |

완전한 거리/변위 분포는 `distribution.json`을 참조한다. 로봇 원점은 장면 로컬 (0,0,0)이며 shoulder 지표는 리프트 축 구간에 대한 최소 거리다. probe 필터는 기존 빵0/1에서 네 빵으로 확장했으며 특정 빵을 task 목표로 강제하지 않는다. 삽입 probe는 슬롯을 교대로 샘플링하는 상한 검사이지 모든 경로의 실행 가능성 증명이 아니다.

## 현재 환경과 배치/reset 검증 범위

소스 확인 결과 요청한 설정과 일치했다: rack.usda 230×130×45mm 및 현 네 홈 bread offsets, 아무 빵 정상 적재+90% 레버 진입, 하강 완료 후4초, phase1/2 LED ON, 같은 ID의 가열 완료 빵 하나 이상 접시 배치, 중심 반경20mm, master/slave100/4, master6.5rad/s. 이번 작업은 task/asset/VR 입력/관절 설정을 수정하지 않았다. 설정 검증이며 PhysX readback이 아니다.

거치대 rigid transform으로 네 빵 pose를 함께 변환한다. loader가 100개 모두 상대 pose를 검증하고 scene.init_state에 적용한다. `reset_objects`는 해당 default_root_state에 env origin을 더한다. 실제 reset 함수 본문을 CPU tensor와 모의 write API에 연결해 전체/부분 env reset을 검사한다. 정적 rack은 spawn pose를 유지한다. 접시 성공 함수가 검사하는 default_root_state도 시나리오 plate pose에서 생성되므로 접시 기준 위치가 일치한다.

현재 USD visual/collider의 보수적 XY hull 및 rack+네 빵 외곽에 대해 테이블20mm 여유와 물체간60mm 여유를 검사했다. 100개 중 최소 물체 간격은 **138.99mm**. 고정 rack의 실제 충돌 삼각형과 bread convex collider를 사용해 초기 관통이 없고 1mm 하강 안에 접촉함을 검사한다. 모든 시나리오에서 같은 rack-local bread pose임을 검증해 이 관계가 보존된다. 중력 아래 정착·접촉 안정성은 실제 시뮬레이션 미검증이다.

이번 세션은 Docker API 소켓 permission denied, `nvidia-smi` 드라이버 통신 실패로 PhysX/GUI/Quest 실행, 렌더링, 실제 reset/집기/전체 task 성공은 미검증이다. 기존 실행 중 프로세스를 중단·재시작하지 않았다. Compose 설정 해석으로 host cyclo_lab_mj → `/workspace/cyclo_lab` mount와 수정본 우선 PYTHONPATH를 확인했다. 컨테이너 내부 경로 이름이 cyclo_lab인 것은 수정본 mount 목적지이며 원본 저장소를 의미하지 않는다.

CPU 결과: 새 delivery 테스트 **6개**, 기존 시나리오 선택/loader **8개**, 기존 기록 metadata **6개**, 총 **20개 통과**. 새 테스트는 100개 전체에 대한 반복 검사를 포함한다. 상세 실행 환경과 검사 구분은 `verification_report.json`에 저장했다.

## 재생성과 CPU 테스트

저장된 산출물을 덮어쓰지 않도록 생성기는 기존 출력 파일이 있으면 실패한다. 아래는 새 임시 폴더에 생성한다. 같은 소스/asset/입력 및 Python/numpy/scipy/USD 환경에서 8개 생성 파일의 바이트 동일성을 확인했다(`reproducibility.json`).

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
MJ_SCENARIO_OUTPUT=$(mktemp -d /tmp/toast-scenarios-rebuild.XXXXXX)
/home/mj/hand-sim-conda/bin/python scripts/tools/generate_current_toast_scenarios.py --output "$MJ_SCENARIO_OUTPUT"
/home/mj/hand-sim-conda/bin/python -m unittest discover -s scripts/tools -p 'test_current_toast_delivery.py' -v
python3 -m unittest discover -s scripts/tools -p 'test_toast_scenario_runtime.py'
python3 -m unittest discover -s scripts/tools -p 'test_toast_recording_metadata.py'
```

## GUI: 각 그룹 첫 번째 배치

기존 목록 선택은 계속 `--operator operator_A --scenario_index 1`처럼 사용한다. 새 목록은 아래 manifest를 반드시 지정한다. 새 목록 안에서도 `--operator operator_A --scenario_index 26`은 `--scenario_group operator_A_2 --group_index 1`과 같다. 그룹/상위 operator/직접 ID 선택은 서로 함께 지정하지 않는다. 그룹 번호는1~25, 상위 번호는1~50이다.

실제 데스크톱에서 아래 명령을 **하나씩** 실행한다. 이번에 확인된 DISPLAY/XAUTHORITY 값이며 로그인 세션이 바뀌면 그 세션의 값을 사용한다. `run_mj.sh --gui`가 DISPLAY, X11 socket, Xauthority, HEADLESS=0, LIVESTREAM=0을 전달한다. R로 같은 배치를 reset, 창을 닫아 종료한다. 아래 여덟 명령을 동시에 실행하지 않는다.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
export DISPLAY=:1
export XAUTHORITY=/run/user/1000/gdm/Xauthority
```

operator_A_1 첫 항목: `toast_v20261108_097` (상위 번호 1).

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_A_1 --group_index 1
```

operator_A_2 첫 항목: `toast_v20261108_087` (상위 번호 26).

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_A_2 --group_index 1
```

operator_B_1 첫 항목: `toast_v20261108_041` (상위 번호 1).

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_B_1 --group_index 1
```

operator_B_2 첫 항목: `toast_v20261108_011` (상위 번호 26).

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_B_2 --group_index 1
```

유한 smoke/reset 실행은 위 뷰어 명령에 `--steps 120 --reset_every 60`을 추가한다. 이번 세션에서는 실행하지 못했다.

## Quest: 전용 bridge와 각 그룹 첫 번째 배치

현재 실행 중 서버/시뮬레이션에 영향을 주지 않도록 새 bridge와 별도 포트를 사용한다. 기존 입력 매핑은 그대로다. 별도 터미널에서 서버를 실행한 뒤 Quest에서 표시된 HTTPS 주소로 접속/Pair한다. `192.168.10.116`은 기존 문서의 host 주소이므로 현재 PC의 Quest 접근 가능한 주소와 다르면 `--host`를 바꾼다. 포트8766이 점유 중이면 종료시키지 말고 다른 미사용 포트를 선택한다. 서버 자체는 이번 작업에서 실행하지 않았다.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
python3 scripts/quest_diagnostic/server.py \
  --host 192.168.10.116 --port 8766 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab_mj/logs/quest_scenarios_v20261108
```

Quest 브라우저 주소: `https://192.168.10.116:8766/`. 서버가 만든 input.json을 아래 시뮬레이션이 사용한다. 새 bridge는 처음부터 기존 브라우저/서버 입력 세션과 연결되는 것이 아니므로 이 주소에서 Pair해야 한다. GUI 환경 변수는 위와 같다. 아래에서 필요한 그룹 명령 **하나만** 실행한다. `--keep-open`은 여러 episode 사이 대기하며 유지한다. 기록은 기본으로 켜지지 않는다.

operator_A_1:

```bash
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_scenarios_v20261108 \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_A_1 --group_index 1 \
  --enable-grippers --keep-open
```

operator_A_2:

```bash
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_scenarios_v20261108 \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_A_2 --group_index 1 \
  --enable-grippers --keep-open
```

operator_B_1:

```bash
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_scenarios_v20261108 \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_B_1 --group_index 1 \
  --enable-grippers --keep-open
```

operator_B_2:

```bash
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_scenarios_v20261108 \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_B_2 --group_index 1 \
  --enable-grippers --keep-open
```

다음 항목은 `--group_index 2`처럼 바꾸어 새 실행에서 선택한다. 단일 프로세스 중 다른 시나리오로 갈아타는 기능은 추가하지 않았다. 기존 기록 기능을 사용할 때는 새 `--record-dir`과 기존 기록 옵션을 사용하며, metadata에 상위 operator/순번 및 그룹/그룹 순번을 함께 기록한다. 기존 진단 기록은 성공 demonstration으로 자동 표시되지 않는다.

## 이번 변경 파일

- `scripts/tools/generate_current_toast_scenarios.py`: 현재 소스 계약/asset 확인, 새 표본, 배치 유효성, 균형 배정, 산출물 생성.
- `scripts/tools/toast_scenario_geometry.py`: 로컬 기존 기하/거리 검사 방식 재사용. task probe 대상 네 빵으로 확장.
- `scripts/tools/test_current_toast_delivery.py`: 고유성/균형/그룹선택/기록/loader/reset/실제 USD 정적 검사.
- `scripts/tools/view_make_toast_scenario.py`: 그룹 선택, version manifest 옆 assignments.csv 사용, 기존 A/B 선택 호환.
- `scripts/quest_diagnostic/teleop_toast.py`: 동일 선택기를 사용하고 그룹을 기존 recorder operator/index로 연결. 기존 B 첫 ID guard는 구 manifest에만 적용.
- `scripts/tools/toast_recording_metadata.py`: 새 기록에 그룹/두 순번 메타데이터 추가.
- 이 버전 폴더: 새 시나리오/배정/pose/분포/검증/참조 입력/설명서.

원본 cyclo_lab과 기존 시나리오 파일을 수정하지 않았고 commit/push하지 않았다.
