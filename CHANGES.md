# Changes

## ① 브랜치 목적

`toast-quest`는 FFW BG2 양팔 토스트 환경을 Quest WebXR로 조작하고, 배치를 바꿔 시연을
수집하기 위한 공유 브랜치다. 대상 task는 `Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2`다.
`toast-quest`는 Git 브랜치 이름이며 task의 `-v2` 등록 버전과 구분한다. Quest 실행기는 이 ID를
고정 사용하며 등록 환경 클래스는 `MakeToastFFWBG2BimanualEnv`, 설정 클래스는
`MakeToastFFWBG2BimanualServeEnvCfg`다.
4홈 빵 거치대, 현재 동작·성공 조건, Quest 서버/클라이언트, 새 시나리오 100개와 검사 도구를 포함한다.

원본 비교 기준은 `badajhong/cyclo_lab`의 **`5f5086d11f664494119086de30a9e925b12022ad`** (`add readme of toast`, 2026-11-02)로 고정했다. 최초 작업 커밋 `761c8ac`의 부모와 브랜치 생성 reflog가 이 커밋을 가리킨다.

분야별 실제 파일 변경과 기준 근거는 [원본 비교 기록](docs/toast_quest/BASELINE.md)에 정리했다.

## ② 기존 환경 대비 변경 전/후

현재 `toast-quest` 브랜치의 토스트 환경 코드 기준이다. 아래 ‘기존’ 열은 위 고정 커밋과 비교한다.

| 항목 | 기존 `5f5086d` | 현재 toast-quest |
|---|---|---|
| 조작 | 기존 양팔 IK·그리퍼와 recorder 도구 | Quest WebXR 양손 입력·clutch·trigger 조작, 상태/HUD·4카메라 미리보기 추가 |
| 거치대 | RoboDojo bread_shelf, 양팔 환경 scale (2,1,1) | native 230×130×45 mm 4홈 rack, scale (1,1,1), 네 빵 상대 pose 갱신 |
| 자동 시작 | bread_0와 bread_1이 각각 다른 슬롯에 적재 + 레버 95% 진입 | 네 빵 중 하나 이상 정상 적재 + 레버 90% 진입 |
| 가열 | 하강 완료 후 5초 | 하강 완료 후 4초, 시뮬레이션 시간 기준 |
| LED | cycle 상태 LED 없음 | 하강·가열 ON, 상승 시작부터 OFF |
| 캐리지 | 하한/하강 −45 mm, 상한/상승 +15 mm, 이동 60 mm | 하한/하강 −45 mm 유지, 상한/상승 +35 mm, 이동 80 mm |
| 빵 성공 | bread_0/1 모두 접시, bread_2/3 거치대 유지; 개별 가열 ID 증거 없음 | 가열을 완료한 동일 ID 빵 하나 이상 접시 조건 충족; 여분 빵 잔류 조건 제거 |
| 접시 XY 판정 | 빵 외곽 전체가 접시 반경−0.5 mm 안 | 빵 형상 중심의 접시 로컬 XY 반경 **20 mm 미만** |
| 좌우 master/slave gain | 대상 환경에서 이미 stiffness=100, damping=4 | 최종값 **동일**, 환경 설정에 명시·Quest 설정/readback 검증 추가 |
| 좌우 master joint1 속도 상한 | 2.2 rad/s | 6.5 rad/s |
| 시나리오 | 고정 100개 delivery/그룹 선택 없음 | 기존 목록을 보존하고 새 100개, A/B 및 네 하위 그룹 선택·배치도 추가 |
| 기록·재생 | 기존 Isaac Lab recorder/replay | 시나리오 provenance, 빵별 가열 상태, 진단 HDF5·검수 도구 추가 |

## ③ 현재 최종 설정과 성공 조건

- **토스터:** phase 0에서 정상 적재와 레버 비율 ≥0.90의 새 진입이 함께 필요하다.
  누른 채 나중에 빵을 넣으면 재진입 전까지 시작하지 않는다.
  하강 최소 0.60초, 목표 −45 mm 오차 <1.5 mm, 실제 속도 <0.01 m/s가 충족된 뒤
  4초 가열을 시작한다. phase 1/2에서 LED ON, phase 0/3/4에서 OFF다.
- **상승:** 0.80초 보간으로 +35 mm를 명령한다. 완료는 최소 0.92초 및 실제 위치 오차
  <1.5 mm를 요구한다. 캐리지 속도 제한 0.12 m/s는 유지됐으며 새 명령 곡선 최대속도
  0.15 m/s와 같지 않다. 실제 완료가 늦어질 수 있다.
- **가열 증거:** 가열 진입 때 정상 적재된 빵 중 가열 동안 계속 적재 판정을 통과한 ID를
  기록한다. 중간 이탈/재삽입 또는 늦은 투입은 그 사이클의 증거가 되지 않는다.
  reset에서 초기화하며, 개별 증거가 없는 과거 기록 복원으로 가열 성공을 추정하지 않는다.
- **빵 관련 성공:** `bread_0`~`bread_3` 중 동일 ID가 가열 완료 및 접시 조건을 모두 만족해야 한다.
  형상 중심의 접시 로컬 XY 반경 <20 mm, 형상 전체 로컬 Z가 −2 mm 초과/50 mm 미만,
  기울기 `abs(R[2,2])>0.94`, 선속도 <0.15 m/s다. 이 판정은 접시 접촉력 검사가 아니다.
- **전체 성공:** 위 빵 조건 외에도 접시 upright `R[2,2]>0.985`, 초기 XY에서 이동 <25 mm,
  환경 기준 접시 X>0.419 m, phase 4·레버 복귀, 양 손목 standby 오차 <40 mm,
  기존 gripper 판정 <0.15 및 lift 절댓값 <20 mm를 요구한다. 여분 빵이 없어도 빵 성공은
  가능하지만 다른 빵 낙하 등 기존 종료 조건은 별도로 적용된다.
- **그리퍼:** 좌우 master joint1·slave joint2/3/4 모두 100/4. master 속도 상한 6.5 rad/s,
  effort 30; slave effort 20, 속도는 USD 값을 상속한다. 6.5는 실제 도달 속도가 아닌 상한이다.
  폐기된 `--gripper-slave-gains-official`은 사용하지 않는다.
- **Quest:** 아래 명령은 practice profile의 이동·회전 목표 배율 1:1이다. 기본 home 범위
  0.55 m/120°, action 보정 제한 0.10 m/시뮬레이션초·0.8 rad/시뮬레이션초,
  목표 선행 0.12 m/45° 등을 유지한다. 실제 VR 추종 속도는 이 배율과 다르며
  IK·관절 제한·접촉·시뮬레이션/렌더 주기에 좌우된다.

진단 JSON/JSONL·CSV·RGB는 학습용 시연이 아니다. 선택적 `--record-dir`의 HDF5는
`data/demo_*/{actions,obs,states,initial_state,processed_actions}`와 metadata/manifest snapshot을
저장하지만 **diagnostic=true, success=false**인 진단 경로다. 기존 recorder 형식과 같아도
검수된 성공 학습 데이터로 분류하면 안 된다. action replay와 saved-state 영상도 구분해야 하며,
영상 재생만으로 물리 재현 성공을 주장하지 않는다. 아래 실행 예시는 무기록 조작이다.

## ④ 필요한 환경·의존성

Linux 데스크톱, NVIDIA GPU/드라이버, NVIDIA Container Toolkit, Docker Compose v2,
Git LFS, Python 3, 호스트 OpenSSL이 필요하다. GUI에는 X11/Xauthority 접근이 필요하다.
Quest와 PC는 HTTPS 연결 가능한 네트워크를 사용한다.

| 의존성 | 준비 방식 |
|---|---|
| Isaac Sim | Docker build가 `nvcr.io/nvidia/isaac-sim:5.1.0` 다운로드 |
| Isaac Lab 및 third_party | v2.3.0 계열 소스 snapshot이 Git에 직접 포함. 현재 gitlink 0개이며 submodule update는 no-op |
| RoboDojo 물체 | manifest에 고정된 revision `63fcc045f2e974902eb7800d29de48004cf86016`; 다운로더가 크기/SHA256 검증 |
| 새 거치대 | `rack.usda`와 상대 참조 `bread_slot.usdz` 모두 LFS. USDZ 내부 mesh 포함, 별도 텍스처 없음 |
| PackingTable 및 재질 | Isaac Sim asset cloud root의 `/Isaac/Props/PackingTable/packing_table.usd`와 참조 파일. 클라우드 접근 또는 사용자 설정 asset root/cache 필요 |
| Python 패키지 | Dockerfile/constraints에서 설치. 일부 선택 패키지는 범위 또는 미고정 버전이므로 이미지 전체의 완전한 재현성은 미보장 |

다른 개인 폴더에서 파일을 복사할 필요는 없지만 **외부 asset 다운로드까지 없는 오프라인 패키지는 아니다**.
자세한 버전은 [의존성 목록](docs/toast_quest/DEPENDENCIES.md), 물체 출처는
[asset manifest](source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/asset_manifest.json)에 있다.

## ⑤ Clone·submodule·LFS·설치

NVIDIA EULA에 동의하는 환경에서 실행한다(`docker/.env.base`의 `ACCEPT_EULA=Y`).
clone 위치는 사용자가 선택한다. `REPO`는 그 checkout 루트이며 새 터미널에서도 다시 지정한다.

```bash
git clone --branch toast-quest https://github.com/kkkkkmj/cyclo_lab.git cyclo_lab_toast_quest
cd cyclo_lab_toast_quest
export REPO="$PWD"
git lfs install
git submodule update --init
git lfs pull
python3 scripts/tools/download_make_toast_assets.py
docker compose --project-name cyclo_lab_mj --env-file docker/.env.base \
  -f docker/docker-compose.yaml -f docker/compose.mj.yaml --profile base build cyclo_lab
```

`.gitmodules`의 원본 URL 정보는 보존하지만, 현재 포함된 소스를 최신 upstream main으로 교체하지 않는다.
`scripts/run_mj.sh`는 checkout을 `/workspace/cyclo_lab`에 mount하고 해당 소스를 우선 사용한다.
`cyclo_lab_mj` 프로젝트의 별도 transient container이며 원본 컨테이너에 exec하지 않는다.

## ⑥ GUI 환경 확인

새 터미널에서는 첫 줄을 실제 clone 경로로 바꾼다. `DISPLAY`와 `XAUTHORITY`는 현재
데스크톱 세션 값으로 설정한다. `:0`/`$HOME/.Xauthority`는 예시 기본값이며 로그인 환경에 따라 다르다.

```bash
export REPO=/path/to/cyclo_lab_toast_quest
cd "$REPO"
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery/manifest.json \
  --scenario_group operator_A_1 --group_index 1
```

R로 같은 배치를 reset한다. GUI와 다음 Quest 시뮬레이션은 GPU 자원 여유를 확인하고 하나씩 실행한다.

## ⑦ Quest 서버와 로봇 조작

**서버 터미널:** `REPO`는 clone 경로, `QUEST_HOST`는 Quest에서 접근 가능한 PC LAN IP/호스트명,
`QUEST_PORT`는 미사용 포트로 바꾼다. PC 방화벽에서 해당 HTTPS 연결을 허용한다.

```bash
export REPO=/path/to/cyclo_lab_toast_quest
export QUEST_HOST=YOUR_PC_LAN_IP
export QUEST_PORT=8766
cd "$REPO"
python3 scripts/quest_diagnostic/server.py \
  --host "$QUEST_HOST" --port "$QUEST_PORT" \
  --bridge-dir "$REPO/logs/quest_toast_quest"
```

Quest Browser에서 설정한 `https://<QUEST_HOST>:<QUEST_PORT>/`에 접속하고 인증서를 확인한 뒤
터미널 PIN으로 Pair한다. 기본 인증서/개인키는 `~/.local/state/cyclo-quest-tls`에 자동 생성한다.
사용자 인증서를 쓰려면 위 명령에 `--cert /인증서/경로 --key /개인키/경로`를 추가한다.
개인키는 Git에 넣지 않는다. Secure context/WebXR/immersive-vr와 client/server build를 확인한다.

**조작 터미널:** GUI viewer를 사용자가 종료한 뒤 실행한다. 서버는 유지한다.
서버의 호스트 bridge와 아래 컨테이너 bridge는 같은 디렉터리다.

```bash
export REPO=/path/to/cyclo_lab_toast_quest
cd "$REPO"
GROUP=operator_A_1
INDEX=1
bash scripts/run_mj.sh scripts/quest_diagnostic/teleop_toast.py \
  --headless --keep-open --enable-grippers --control-profile practice \
  --scenario_manifest scenario_delivery/manifest.json \
  --scenario_group "$GROUP" --group_index "$INDEX" \
  --bridge-dir /workspace/cyclo_lab/logs/quest_toast_quest \
  --position-scale 1 --rotation-scale 1
```

VR 진입 후 상태·최신 영상·양손 입력을 확인하고 양쪽 squeeze를 놓아 기준을 잡는다.
X(키보드 n)는 같은 시나리오 reset 후 시작, squeeze를 누른 손은 팔 목표 제어,
trigger는 그리퍼 제어(놓으면 열기, 누르면 닫기), A(키보드 s)는 WAITING으로 전환한다.
practice에서 squeeze 해제/입력·영상 무효 시 팔 목표를 측정 자세에 맞추며, 그리퍼는 마지막 목표를 유지한다.
물리 관성까지 순간 정지한다는 의미는 아니다. 입력 복구 뒤 squeeze를 놓고 다시 잡는다.
미리보기는 overview/head/좌·우 wrist 네 카메라와 상태/HUD를 제공한다. 캐스팅 정렬·실제 가독성은 미검증이다.

그룹·순번 선택과 배치도 사용법은 [시나리오 안내](scenario_delivery/README.md)를 따른다.
