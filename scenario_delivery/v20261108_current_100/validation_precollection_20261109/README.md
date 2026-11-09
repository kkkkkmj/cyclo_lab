# 시연 수집 전 검증 — 2026-11-09

결과: **100/100 STATIC_PASS**, 정적 실패 목록은 비어 있다. **실제 PhysX 안정성/reset은 0/100 실행**, 작업 IK·충돌·경로와 전체 task 수행은 **100개 모두 미검증**이다. 수집 준비가 모두 완료됐다는 결과가 아니다. 실패한 시나리오의 자동 수정/교체는 하지 않았다.

- [시나리오별 CSV](results.csv), [읽기 쉬운 100개 보고서](REPORT.md), [세부 JSON](results.json)
- [실패 목록](failures.json): 현재 검사한 정적 범위에서 0개. 미실행을 통과로 세지 않는다.
- [34개 VR 대상·선정 이유·개별 GUI/Quest 명령·체크리스트](VR_CHECKLIST.md)
- [검사 방식·source/asset SHA256·허용오차](audit.json)
- [실제 실행 시도 로그](physx_launch_attempt.log): Docker API socket permission denied. NVIDIA driver 조회도 실패했다.

## 기존 결과 재사용과 추가 검사

기존 generator의 실제 USD 형상 읽기/변환, XY hull, polygon distance, table support 검사, rack 삼각형 clipper, loader 및 serving success 함수 검사 harness를 재사용했다. 이전 결과만 복사한 것이 아니라 현재 asset과 100개 pose로 정적 계산을 다시 수행했다. 부족했던 수치 테이블 가장자리 여유, 중심 거리와 표면 간격 구분, 각 접시 pose에서 실제 성공 predicate 논리 만족 가능성, 시나리오별 미검증 상태, VR 대상 선정을 추가했다. 새 파일은 `scripts/tools/validate_toast_collection.py`, `scripts/tools/test_toast_collection_validation.py`이며 기존 task/asset/시나리오/gain/속도/VR 코드를 수정하지 않았다.

최소 테이블 가장자리 여유 **29.3748mm**, 최소 물체 외곽 보수적 XY 간격 **138.9902mm**. 테이블 여유 기준20mm, 물체 접근 여유60mm를 유지했다. 정확한 mesh 삼각형 사이의 3D 최소 거리를 구했다고 주장하지 않는다.

### 정적 검사 방법과 한계

- 실제 USD mesh의 내부 transform, root pose, 회전, scale을 적용하고 XY convex hull로 투영한다. 토스터/접시/거치대 hull에는 1mm 여유를 주며, 거치대 외곽은 네 빵까지 포함한다. yaw 회전을 실제 적용했으며 단순 중심 거리로 관통을 판정하지 않는다.
- `center_distances_3d_m`은 토스터/접시/거치대 **root 원점 간** 3D 거리다. 기하 중심이나 표면 거리와 다르다.
- `surface_xy_lower_bounds_m`은 위 보수적 외곽 다각형 사이 간격이다. 실제 3D 표면 간격의 보수적 하한이며 표면 사이 정확한 거리는 아니다. XY hull은 홈/오목한 부분을 채우므로 과도하게 보수적일 수 있다. 이 검사에서는 분리돼 있어 주 물체끼리 초기 관통하지 않는다는 충분조건을 확인했다. 실제 PhysX cooked contact offset이나 움직이는 로봇/빵의 접근 경로 검사는 아니다.
- 테이블은 기존 추출 결과의 실제 지지 convex polygon을 사용했고 현재 로봇 USD SHA256 일치를 확인했다. 숫자 여유는 해당 경계까지의 최소 거리이며 기하 hull에 추가된 여유를 포함한 보수적 값이다.
- rack는 **실제 고정 충돌 삼각형**, bread는 **실제 authored convex collider**로 초기 교차 없음과 1mm 하강 안의 지지 접촉을 확인했다. 100개 모두 동일 rack-local 빵 pose를 유지한다. 이는 중력 아래 동적 정착/미끄러짐 검사와 다르다.
- loader를 각 scenario에 적용하고 plate init_state를 확인했다. success가 사용하는 plate.default_root_state 기준과 일치한다. 실제 task_done 함수에 각 현재 plate pose와 같은 ID 가열 완료/접시 배치 상태를 구성했을 때 **각각 네 bread 모두 논리적으로 통과**한다. 이 상태 구성은 CPU 모의 검사이며 실제 로봇/PhysX 상태를 바꾸지 않는다.
- 따라서 접시 위치·yaw 때문에 success가 논리적으로 처음부터 불가능한 시나리오는 이번 범위에서 발견하지 못했다. 실제 도달성·충돌·가열/집기는 별개다. 기존 높이/속도 predicate 자체가 접촉 센서를 요구하지 않으므로 낮은 공중 상태 일부를 허용할 수 있다는 기존 의미도 변경하지 않았다.

### 접근 가능성

현재 팔은 상대 pose DLS IK, 실제 soft joint limits clamp 및 standby null-space 보정을 사용한다. 로컬 reference의 `ik_probes`는 USD joint limits 내 least-squares, 여러 seed를 사용하는 기존 구현이다. 하지만 target orientation과 OPEN gripper TCP가 휴리스틱이고 grasp 접촉 자세가 검증되지 않았으며 독립 팔/리프트 해를 사용한다. 따라서 이를 재실행해 실제 작업 PASS로 포장하지 않았다.

기존 링크 길이 거리 상한 필터는 100개를 제외하지 않았다. 이는 필요한 조건에 가까운 거친 제외 검사이며 접근 가능 증명이 아니다. `results.csv`에는 **bread_0~3 각각의 grasp IK/목표 충돌/경로**, insert/lever/serve, **최소 한 개 빵 사용 가능**을 모두 별도 `UNVERIFIED`로 저장했다. 실제 grasp frame, finger clearance, insertion/lever contact pose, 충돌 scene 및 경로 검증이 준비되어야 해당 항목을 통과시킬 수 있다. VR 체크리스트에서 이 부분을 실제로 확인한다.

## PhysX 검사 동작과 고정 허용오차

`--mode physx`는 100개를 하나씩 별도 자식 Python/Isaac 환경에 적용한다. 기존 실행 중 프로세스에는 접근하지 않는다. 현재 task의 physics/충돌/종료 조건을 변경하지 않는다. 매 step 물체 pose를 쓰지 않는다.

- 초기 reset 직후 검사 → 최소5초 sim time 진행 → reset 도전 검사 → 동일 배치에서 다시5초 진행한다. 100개 모두 종료 이벤트가 없을 때 총1000초 이상의 sim time이다. 렌더링/프로세스 시작 시간은 포함되지 않는다.
- 대기 action: 양팔12개 값은0(상대 IK delta, 기존 standby 보정 유지), 그리퍼/리프트3개 값은+1. 그리퍼 action `(a+1)/2`에서+1은0rad open, 리프트 `.25*a-.25`에서+1은0m target이다. **전체 action=0은 대기가 아니다.** 기존 action 차원15, relative IK, lift scale/offset도 runtime assert한다.
- physics substep마다 상태를 관측하고 초기/최종 pose, 최대 이동/회전, 마지막 선·각속도, rack-local 이탈, 기하 최저 Z, 로봇 drift, termination을 기록한다. gzip JSONL trace와 scenario별 JSON에 저장한다. 자동 reset이 일어나면 해당 trial은 실패이며 reset된 최종 pose를 안정성 PASS로 사용하지 않는다.
- reset 도전은 첫 물리 trial이 끝난 뒤 **진단용 cycle/빵별 기록을 nonzero로 두고 LED ON으로 만든 다음 즉시 reset**한다. 이 인위적 상태에서는 physics를 step하지 않는다. reset 뒤 phase/elapsed/command/previous_pressed/heating_time 및 heating_present/heated_bread가 모두0, 실제 LED material 및 상태 OFF, 물체 pose와 toaster joints가 default인지 확인한다. 실제 가열 수행 검증은 아니다.

| 항목 | 사전 고정 기준 | 근거/의미 |
|---|---|---|
| trial | 각각 ≥5 sim seconds | 제어 dt로 올림하여 실행 |
| 물체 최대 root 이동 | 10mm 이하 | 환경 접시 위치 여유25mm보다 작게 잡은 안정성 진단 기준 |
| bread rack-local 최대 편차 | X5/Y3/Z6mm 이하 | 기존 홈25mm·빵 두께11.8mm와 spare placement 검사 기준 재사용 |
| bread 최대 상대 회전 | 20° 이하 | 기존 정렬 dot .94에 가까운 진단 기준 |
| plate 최대 상대 회전 | acos(.985)=9.94° 이하 | 기존 upright 조건에 기반, yaw까지 보는 보수적 안정성 진단 |
| toaster/rack 최대 상대 회전 | 5° 이하 | 초기 정지 물체의 진단 기준 |
| 마지막 선속도 | <.15m/s | 기존 bread stability 기준 |
| 마지막 각속도 | ≤.5rad/s | 별도 정지성 진단 기준; task 성공 조건은 아님 |
| 낙하 | 기하 최저점 < tableZ−10mm면 실패 | root 원점 높이 대신 형상 기준 |
| robot joint 최대 drift | ≤.05rad 또는 lift .05m | 기존 대기 제어가 크게 이탈하는지 진단, task 성공 기준 아님 |
| reset position | 축별 ≤50µm | 기존 viewer reset readback 기준 |
| reset rotation | 1−abs(normalized quat dot) ≤5e−5 | 기존 viewer 기준 |
| cycle/기록/LED | reset 후 모두 초기값 | 실제 state/material readback |
| termination/timeout | 하나라도 발생 시 실패 | 안정성 시간 채우기 위해 자동 종료를 무시하지 않음 |

허용오차는 실행 전에 `LIMITS`로 고정하고 결과에 저장한다. 실제 결과를 본 뒤 통과시키려고 자동 완화하지 않는다. 수치 nonfinite는 오류로 처리한다. 비정상 종료 때문에5초를 채우지 못하면 실패/오류이며 5초 검증 완료로 표시하지 않는다.

## Ubuntu 터미널에서 전체 실행

현재 세션에서는 Docker 접근 거부로 시작하지 못했다. 아래를 **Docker/GPU가 동작하는 Ubuntu 터미널**에서 실행한다. 설정이나 프로세스를 자동으로 고치는 명령은 포함하지 않았다. 각 worker가 카메라 포함 현재 환경을 시작하므로 시간이 걸린다.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
MJ_AUDIT_RUN="logs/toast_precollection_physx_$(date +%Y%m%d_%H%M%S)"
bash scripts/run_mj.sh scripts/tools/validate_toast_collection.py \
  --mode physx --headless --seconds 5 \
  --manifest scenario_delivery/v20261108_current_100/manifest.json \
  --output "$MJ_AUDIT_RUN"

python3 scripts/tools/validate_toast_collection.py \
  --mode report \
  --manifest scenario_delivery/v20261108_current_100/manifest.json \
  --static-dir scenario_delivery/v20261108_current_100/validation_precollection_20261109 \
  --runtime-dir "$MJ_AUDIT_RUN" \
  --output "${MJ_AUDIT_RUN}_report"
```

동일 터미널에서 실행해 `MJ_AUDIT_RUN`을 유지한다. 출력 폴더는 새 경로여야 하며 기존 결과를 덮어쓰지 않는다. 결과 폴더의 scenario별 JSON/log/trace와 합친 `results.csv`, `REPORT.md`, `failures.json`을 확인한다. batch 명령의 종료만으로 모든 항목 PASS를 뜻하지 않는다. worker 오류도 scenario별 ERROR로 저장한다. 일부 runtime 결과가 없으면 미실행으로 남긴다. 전체 작업은 안정성 검사를 통과해도 `NOT_VERIFIED`로 남는다.

정적 검사를 다시 실행하려면 기존 결과를 보존하고 새 output을 지정한다:

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
/home/mj/hand-sim-conda/bin/python scripts/tools/validate_toast_collection.py \
  --mode static --manifest scenario_delivery/v20261108_current_100/manifest.json \
  --output "logs/toast_precollection_static_$(date +%Y%m%d_%H%M%S)"
```

동일 script의 static 모드도 `bash scripts/run_mj.sh scripts/tools/validate_toast_collection.py --mode static ...`으로 실행 가능하다(컨테이너 numpy/scipy/USD 필요). 생성/검증용 로컬 Python 환경은 기존 것 그대로 사용했다.

## VR 대상과 검사 순서

각 그룹6종류 대표24개 + 그룹별 최장 거리/최소 간격/최대 yaw 변화 항목을 추가해 중복 제거한 **34개**다. 최장 거리는 기존 max probe–shoulder 거리, 회전은 기준 yaw에서의 최대 절대 변화로 정의한다. 대표는 해당 그룹/종류 내 거리 중간 항목이다. 모든 선정 이유와 **34개 각각의 정확한 GUI/Quest 명령**은 [VR_CHECKLIST.md](VR_CHECKLIST.md)에 저장했다.

각 대상에서 빵 ID/손/슬롯을 기록하고 **집기 → 삽입 → 레버90% 진입/LED ON → 하강 완료 후4초 → 상승/LED OFF → 같은 빵 접시 배치 → 그리퍼 열림/팔 standby/리프트 복귀 → 실제 success → reset**을 확인한다. 빵 하나로 성공했다고 나머지 세 빵의 접근성을 통과시키지 않는다.

## 코드 검사와 보존

추가 검증 코드의 CPU/모의 테스트7개 통과: 대기 action/5초×2/기록 reset, termination 실패 처리, nonfinite 오류, 빵 이탈·속도·reset 실패, quaternion 부호/각도, 보고서 병합의 미실행/오류 구분, VR 종류 커버리지 및 기존 source/asset/manifest hash 보존. 이는 PhysX 검증이 아니다. 기존 테스트/결과를 재사용했고 환경 구현은 변경하지 않았다. manifest와 소스/asset hash를 저장했으며 runtime 병합 시 static/runtime hash 불일치를 거부한다.

```bash
/home/mj/hand-sim-conda/bin/python -m unittest discover -s scripts/tools -p test_toast_collection_validation.py -v
```

원본 cyclo_lab 및 실행 중 작업에 변경 없음. commit/push 없음.
