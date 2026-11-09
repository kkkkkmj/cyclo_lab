# Toast Quest — 현재 작업 진입점

대상은 `Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2`이다. 기존
`toast-scenarios-100`의 `29c04a5592bb20bfe4dc0134bf1ff4bed64e67ca`에서 이어진 작업을
`toast-quest`에 정리했다. 이전 목록과 배정표는 유지하며 새 목록은 명시적으로 선택한다.
아래 기본값은 현재 코드 기준이다. 개별 README와 measurements의 과거 보고서·before 소스는
당시 설정/결과이며 현재 기본값이나 이번 실행 검증을 뜻하지 않는다.

## 기존 환경과 현재 설정

| 항목 | 이전 기준/중간 작업 | 현재 v2 |
|---|---|---|
| 입력 | 기존 GUI/시나리오 선택 | Quest WebXR 양손 pose, 양팔 IK, squeeze clutch, trigger 그리퍼, 상태·4카메라 미리보기 |
| 빵 거치대 | 기존 bread_shelf | 230×130×45 mm 4홈 rack, 네 빵 초기 pose |
| 자동 시작 | bread_0/1 대상, 95% 레버 진입 | 네 빵 중 하나 이상 정상 적재 + 레버 90% 상승 에지 |
| 가열 | 이전 5초 | 하강 완료 후 시뮬레이션 시간 4초 |
| LED | 레버 눌림 기준의 중간 구현 | 하강/가열 ON, 상승 시작부터 OFF |
| 캐리지 | 중간 +15 mm, 이동 60 mm | 목표/상한 +35 mm, 하강 목표/하한 -45 mm, 이동 80 mm |
| 빵 성공 | bread_0/1 모두 접시, 여분 거치대 유지 | 가열 완료한 동일 ID 빵 하나 이상 접시 조건 만족 |
| 접시 판정 | 빵 전체 외곽 포함 | 빵 형상 중심의 접시 로컬 XY 반경 **20 mm 미만** |
| 좌우 gain | slave 비교 설정 2/0.5 등 | master/slave 모두 stiffness=100, damping=4 |
| master joint1 속도 | 좌우 2.2 rad/s | 좌우 6.5 rad/s 상한 |
| 배정 | operator_A/B 각 50 | 새 100개, A_1/A_2/B_1/B_2 각 25 |

소스 기준은 `config/ffw_bg2/`의 `assets.py`, `toast_parameters.py`, `scene.py`,
`bimanual_env_cfg.py`, `toast_cycle.py`, `bimanual_mdp.py`다.
정상 적재는 기존 위치·높이·자세 판정을 사용한다. 레버를 누른 채 나중에 적재하면
새 진입까지 시작하지 않는다. 하강은 최소 0.60초, 위치 오차 <1.5 mm와 속도 <0.01 m/s를
만족해야 가열에 진입한다. 상승 보간 0.80초, 완료는 최소 0.92초 및 목표 오차 <1.5 mm다.
가열 중 이탈한 빵은 해당 가열 증거를 잃는다.

빵 조건만으로 전체 task 성공은 아니다. 접시 위 빵의 높이·기울기·속도,
접시 upright/초기 XY 위치에서 25 mm 미만 이동/X>0.419 m, phase 4와 레버 복귀,
손목 standby·그리퍼·lift 조건도 유지된다. 여분 빵의 거치대 잔류는 v2 성공 조건이 아니다.

## 설치와 컨테이너

NVIDIA GPU/드라이버, Docker Compose, NVIDIA Container Toolkit, Git LFS가 필요하다.
Isaac Sim 5.1.0 및 저장소에 포함된 Isaac Lab 소스 snapshot을 사용한다.
아래 `REPO`는 **이 브랜치를 checkout한 경로**로 사용자가 설정한다.

```bash
export REPO=/path/to/cyclo_lab_checkout
cd "$REPO"
git lfs install
git submodule update --init
git lfs pull
python3 scripts/tools/download_make_toast_assets.py
docker compose --project-name cyclo_lab_mj --env-file docker/.env.base \
  -f docker/docker-compose.yaml -f docker/compose.mj.yaml --profile base build cyclo_lab
```

다운로더는 기존 `asset_manifest.json`의 고정 revision/크기/SHA256을 검증한다.
다운로드된 RoboDojo USDZ는 기존 정책대로 Git에 넣지 않는다. 새 rack의 `rack.usda`와
그 상대 참조 `bread_slot.usdz`는 둘 다 LFS에 포함한다. USDZ 내부 참조/텍스처는 패키지에 포함된다.
`run_mj.sh`는 현재 checkout을 `/workspace/cyclo_lab`에 mount하고 소스 경로를 우선하며,
`cyclo_lab_mj` 프로젝트의 별도 transient container를 실행한다. 원본 컨테이너에 exec하지 않는다.
호스트 경로와 컨테이너의 `/workspace/cyclo_lab`은 서로 다르다.
GUI는 현재 세션의 `DISPLAY`와 `XAUTHORITY`를 설정하고 `--gui`를 사용한다.
이번 정리에서는 컨테이너 빌드/실행 또는 기존 프로세스 재시작을 하지 않았다.

## Quest 연결과 실행

사용 가능한 포트와 별도 bridge를 선택한다. 서버와 시뮬레이터가 같은 bridge를 공유해야 한다.
`QUEST_HOST`에는 Quest에서 접근 가능한 PC의 LAN IP 또는 호스트명을 직접 넣는다.

```bash
cd "$REPO"
export QUEST_HOST=YOUR_PC_LAN_IP
export QUEST_PORT=8766
python3 scripts/quest_diagnostic/server.py --host "$QUEST_HOST" --port "$QUEST_PORT" \
  --bridge-dir "$REPO/logs/quest_toast_quest"
```

Quest Browser에서 `https://<QUEST_HOST>:<QUEST_PORT>/`를 열어 인증서를 확인하고
터미널 PIN으로 Pair한다. Secure context/WebXR/immersive-vr와 client/server build를 확인한 뒤
VR에 진입한다. 자동 생성 TLS 개인키는 사용자 state 디렉터리에 보관하며 Git에 포함하지 않는다.
다른 터미널에서 다음을 실행한다. `GROUP`은 아래 네 값 중 하나, `INDEX`는 1~25다.

```bash
cd "$REPO"
GROUP=operator_A_1
INDEX=1
bash scripts/run_mj.sh scripts/quest_diagnostic/teleop_toast.py \
  --headless --keep-open --enable-grippers --control-profile practice \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group "$GROUP" --group_index "$INDEX" \
  --bridge-dir /workspace/cyclo_lab/logs/quest_toast_quest \
  --position-scale 1 --rotation-scale 1
```

| 선택 예 | 첫 ID |
|---|---|
| `GROUP=operator_A_1; INDEX=1` | toast_v20261108_097 |
| `GROUP=operator_A_2; INDEX=1` | toast_v20261108_087 |
| `GROUP=operator_B_1; INDEX=1` | toast_v20261108_041 |
| `GROUP=operator_B_2; INDEX=1` | toast_v20261108_011 |

GUI 배치 확인은 위 GROUP/INDEX를 사용해 다음으로 실행한다.

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group "$GROUP" --group_index "$INDEX"
```

이동/회전 배율 1:1은 목표 변환의 배율이다. 실제 VR 추종 속도나 실시간 배율을 보장하지 않는다.
IK·관절 속도/effort·목표 제한·접촉·렌더/제어 주기가 실제 응답에 영향을 준다.
위 명령은 기존 practice 보호 제한을 유지한다. `analyze_response.py`, `sample_performance.py`,
`analyze_interruptions.py` 등으로 측정해야 하며 최신 실제 Quest 추종 성능은 검증하지 않았다.

## 새 시나리오 100개

`scenario_delivery/v20261108_current_100/`에 manifest, 700개 물체 pose CSV,
배정표, 생성 설정/seed, 형상 증거 및 입력 생성기 사본을 보존했다.
생성 seed는 20261108, 배정 seed는 20261109다. ID는 000~099로 고유하며
manifest와 배정표가 일치하고 그룹별 순번 1~25에 누락/중복이 없다.

+Y→−Y 순서에서 T=toaster, P=plate, S=bread_shelf:

| 종류 | A_1 | A_2 | B_1 | B_2 | 합계 |
|---|---:|---:|---:|---:|---:|
| T>P>S | 5 | 4 | 4 | 4 | 17 |
| T>S>P | 4 | 4 | 5 | 4 | 17 |
| P>T>S | 4 | 5 | 4 | 4 | 17 |
| P>S>T | 4 | 4 | 4 | 5 | 17 |
| S>T>P | 4 | 4 | 4 | 4 | 16 |
| S>P>T | 4 | 4 | 4 | 4 | 16 |
| 합계 | 25 | 25 | 25 | 25 | 100 |

브라우저로 `scenario_delivery/v20261108_current_100/overview_cards.html`을 열면 카드형
100개 배치도를 볼 수 있다. `overview.svg`도 함께 제공한다. 이는 정적 배치도이며 PhysX 화면이 아니다.
필요하면 저장소에서 `python3 -m http.server 8000 --bind 127.0.0.1` 실행 후
`http://127.0.0.1:8000/scenario_delivery/v20261108_current_100/overview_cards.html`을 연다.

재생성은 numpy/scipy/torch/pxr(USD)를 갖춘 Python을 `TOAST_PYTHON`으로 지정한다.
기존 출력은 덮어쓰지 않는다.

```bash
export TOAST_PYTHON=python3
MJ_SCENARIO_OUTPUT=$(mktemp -d /tmp/toast-scenarios-rebuild.XXXXXX)
"$TOAST_PYTHON" scripts/tools/generate_current_toast_scenarios.py --output "$MJ_SCENARIO_OUTPUT"
"$TOAST_PYTHON" scripts/tools/test_current_toast_delivery.py
"$TOAST_PYTHON" scripts/tools/test_toast_scenario_runtime.py
"$TOAST_PYTHON" scripts/tools/test_toast_serving_success.py
"$TOAST_PYTHON" scripts/tools/test_toaster_led.py
"$TOAST_PYTHON" measurements/toast_lift_35mm_20261109/check_change.py
```

## 진단 기록과 학습 데이터

상태 JSON/JSONL, CSV, RGB, 노출률·성능 trace는 진단 증거다. 학습용 성공 시연이 아니다.
`--record-dir`로 저장하는 Quest recorder HDF5는
`data/demo_*/{actions,obs,states,initial_state,processed_actions}` 구조와 manifest snapshot,
metadata를 사용하지만 **diagnostic=true, success=false**로 기록하는 진단 경로다.
HDF5 형식이 같다고 성공 학습 데이터로 분류하면 안 된다. 학습용 시연은 기존 Isaac Lab
recorder의 task 성공·검수 정책에 따라 별도 수집해야 한다. 개인 시연 HDF5는 이번 커밋에서 제외한다.
재생 도구의 action replay와 saved-state 영상도 구분한다. 후자는 물리 재현 성공의 증거가 아니다.

## 검증과 남은 문제

- **거치대:** 기존 첫 시나리오 2 trial에서 빵 약 18.499~18.502 mm 하강,
  XY 4.72~4.80 mm 이동, 6.02~6.08° 회전이 기록됐다. 초기 1 mm 접촉 검사는
  한쪽 어깨 접촉만 확인했으므로 안정 지지를 보장하지 않는다. cooked collider/접촉 상대가
  없어 정상 안착·관통 여부 미확정이며 전체 100개 PhysX 검증은 완료되지 않았다.
  [진단 보고서](../../scenario_delivery/v20261108_current_100/rack_diagnosis_20261109/README.md) 참조.
- **노출률:** 가장 최근 저장된 실제 결과는 **+15 mm 당시**
  `measurements/toast_exposure_20261109/runs/run_20261109_122359_CrxPWU/results/`다.
  bread_0 슬롯0/1의 phase4 노출률은 각각 46.987384% / 46.921157%,
  완료+1초는 46.987478% / 46.920935%였다. 해당 검사 구간은 VALID이며 슬롯 조건을 유지했다.
  초기 README의 미실행 표시는 실행 전 작성 기록으로 보존한다.
  **+35 mm 실제 노출률·튀어오름·이탈은 미측정**이다.
  [35 mm 보고서](../../measurements/toast_lift_35mm_20261109/REPORT.txt)의 정적 교차 0건은
  동적 물리 검증이 아니다. 명령 최대 속도 0.15 m/s가 기존 제한 0.12 m/s를 넘으므로
  추종 지연 가능성도 남는다. 새 측정은 `bash measurements/toast_lift_35mm_20261109/run_measurement.sh`.
- **카메라 종료:** 진단 도구에 strong reference 유지→callbacks 해제→annotator detach→
  registry 정리→env/app close 순서를 구현했다. 모의 lifecycle 검사를 통과해도
  실제 Isaac 종료/weakref 오류 해결은 아직 미검증이다.
- **CPU/정적 검증:** 이번 정리의 상세 결과는 [검증 기록](VALIDATION.json)에 저장한다.
  USD 형상/시나리오/제어/기록 계약 검사는 PhysX/GUI/VR 완료를 의미하지 않는다.
  실제 시뮬레이터, 원본 저장소, 기존 프로세스는 이번 정리에서 실행·수정·중단하지 않았다.
- **과거 증거:** measurements 보고서와 before 소스는 당시 비교 재현 입력으로 보존한다.
  실행 로그·대형 정점 덤프·캐시는 제외하며, 과거 보고서의 로컬 logs 링크는 별도 로컬 증거 위치다.
