# Toast Quest

Quest WebXR로 FFW BG2의 양팔 IK·그리퍼를 조작하고 상태/카메라 미리보기를 보는 공유용 브랜치다.
새 4홈 빵 거치대와 새 시나리오 100개(A_1/A_2/B_1/B_2 각 25개)를 포함한다.
기존 시나리오 목록도 유지한다. 현재 작업 대상은 `Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2`다.

## 1. Clone 및 설치

Linux, NVIDIA GPU/드라이버, NVIDIA Container Toolkit, Docker Compose v2, Git LFS,
Python 3와 OpenSSL이 필요하다. 컨테이너는 Isaac Sim **5.1.0**, Isaac Lab **v2.3.0 계열의 저장소 내 소스 snapshot**을
사용한다. 현재 Git tree에는 submodule gitlink가 없고 `third_party` 소스가 직접 포함되어 있다.
`.gitmodules`는 원본 URL 정보로 보존되어 있으며 아래 submodule 명령은 현재 tree에서는 no-op이다.
NVIDIA EULA에 동의하는 환경에서 실행한다(`docker/.env.base`의 `ACCEPT_EULA=Y`).

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

RoboDojo 물체는 [asset manifest](source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/asset_manifest.json)의
고정 Hugging Face revision에서 내려받아 크기/SHA256을 확인한다. 외부 의존성 버전·설치 범위는 [의존성 안내](docs/toast_quest/DEPENDENCIES.md)에 정리했다. 새 rack의 USD wrapper와
USDZ 패키지는 LFS에 포함한다. 다른 개인 폴더나 기존 브랜치에서 복사할 파일은 없다.
새 터미널에서는 `cd /사용자가/clone한/경로` 후 `export REPO="$PWD"`를 다시 설정한다.

## 2. GUI로 첫 환경 확인

`DISPLAY`와 `XAUTHORITY`는 **현재 데스크톱 세션 값**이어야 한다.
아래 예시 `:0`와 `$HOME/.Xauthority`가 다른 시스템에서는 실제 값으로 바꾼다.

```bash
cd "$REPO"
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group operator_A_1 --group_index 1
```

R로 reset한다. `run_mj.sh`는 현재 checkout을 `/workspace/cyclo_lab`에 mount한 별도
`cyclo_lab_mj` 프로젝트의 transient container를 사용한다. 다른 컨테이너를 중지하지 않는다.
GPU 실행은 자원 여유를 확인한 뒤 하나씩 수행한다.

## 3. Quest 연결 서버

PC와 Quest가 연결 가능한 네트워크에서 `QUEST_HOST`를 **PC LAN IP/호스트명**으로 바꾼다.
미사용 포트를 선택하고 PC 방화벽에서 허용한다. 이 터미널은 서버 실행 상태로 둔다.

```bash
cd "$REPO"
export QUEST_HOST=YOUR_PC_LAN_IP
export QUEST_PORT=8766
python3 scripts/quest_diagnostic/server.py \
  --host "$QUEST_HOST" --port "$QUEST_PORT" \
  --bridge-dir "$REPO/logs/quest_toast_quest"
```

Quest Browser에서 `https://<설정한_PC_IP>:8766/`에 접속하고 터미널 PIN으로 Pair한다.
기본 인증서는 자동 생성하며 개인키는 `~/.local/state/cyclo-quest-tls`에 보관한다.
신뢰할 인증서를 직접 쓰려면 서버 명령에 `--cert /인증서/경로 --key /개인키/경로`를 추가한다.
브라우저의 인증서 확인 후 Secure context/WebXR/immersive-vr 및 client/server build를 확인한다.

## 4. Quest 조작 및 그룹 선택

GUI viewer를 사용자가 종료한 뒤 별도 터미널에서 실행한다. 서버는 유지한다.
아래 `GROUP`과 `INDEX`만 바꾸면 GUI와 Quest 모두 같은 배치를 선택한다.

| GROUP | INDEX 범위 | 첫 ID |
|---|---|---|
| operator_A_1 | 1~25 | toast_v20261108_097 |
| operator_A_2 | 1~25 | toast_v20261108_087 |
| operator_B_1 | 1~25 | toast_v20261108_041 |
| operator_B_2 | 1~25 | toast_v20261108_011 |

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

Quest에서 VR 진입 후 최신 카메라 영상·양손 입력 상태를 확인한다. 양쪽 squeeze를 놓아
기준을 잡고 X(키보드 n)로 시작한다. squeeze를 누른 손의 목표를 이동하고 trigger로 그리퍼를
조작한다. A(키보드 s)로 에피소드를 마친다. 이동/회전 1:1은 **목표 배율**이며 실제 추종 속도는
IK·관절 제한·접촉·제어/렌더 주기에 좌우된다. 위 명령에는 시연 저장이 켜져 있지 않다.

## 5. 배치도와 현재 동작

`scenario_delivery/v20261108_current_100/overview_cards.html`을 브라우저로 직접 연다.
SVG 배치도와 manifest·배정표·700개 물체 pose·seed도 같은 디렉터리에 있다.
생성/배정 seed는 20261108/20261109이며 100개 고유 ID, 네 그룹 각 25개다.

시연 수집을 위해 토스터·접시·거치대의 순서 6종을 로봇 왼쪽(+Y)→오른쪽(−Y)으로 구성하고
위치·yaw를 변화시켰다. 형상·간격 제외 검사와 작업자별 분포 균형화를 적용했으며,
도달 가능성이나 동일 난이도를 보장하지 않는다. [Scenario Design](scenario_delivery/v20261108_current_100/SCENARIO_DESIGN.md)에
실제 범위·제외 기준·6종×4그룹 배정표·재현 방법을 설명한다.

| 항목 | 이전 기준/중간 설정 | 현재 v2 |
|---|---|---|
| 거치대 | 기존 shelf | 230×130×45 mm 4홈 rack |
| 시작 | bread_0/1, 레버 95% | 네 빵 중 하나 이상 정상 적재 + 레버 90% 진입 |
| 가열·LED | 5초, 레버 기반 중간 구현 | 하강 완료 후 4초, 하강/가열 ON·상승부터 OFF |
| 캐리지 | 중간 +15 mm / 60 mm 이동 | 상한·상승 +35 mm, 하한·하강 -45 mm / 80 mm 이동 |
| 빵 성공 | 두 빵 접시 + 여분 rack | 가열한 동일 ID 하나 이상, 형상 중심 접시 로컬 XY 반경 <20 mm |
| gain·속도 | slave 2/0.5 비교, master 2.2 rad/s | 좌우 master/slave 100/4, master joint1 상한 6.5 rad/s |

전체 성공에는 접시 자세/위치, 빵 높이/기울기/속도, cycle 완료·레버 복귀 및 로봇 standby 조건도 필요하다.
재생성 명령·6종 배정표·정확한 성공 조건은 [상세 설정 및 검증](docs/toast_quest/DETAILS.md)에 있다.

## 현재 제한사항

- 거치대의 빵 내려앉음은 관측됐지만 정상 안착/관통 여부는 미확정이다. 100개 전체 PhysX 안정성은 미검증이다.
- +35 mm 상승의 실제 노출률·빵 이탈은 미측정이다. 과거 +15 mm 결과와 구분해야 한다.
- 카메라 종료 정리 코드는 수정됐지만 실제 Isaac 종료 오류 해결은 미검증이다.
- CPU 검사는 실제 PhysX·GUI·Quest 추종 검증이 아니다. 브라우저 검사는 이번 실행 권한 제한으로 미완료다.
- 진단 JSON/CSV/RGB 및 `diagnostic=true, success=false` HDF5는 검수된 학습용 성공 시연이 아니다.
- GitHub 접속 제한으로 원격 clone/LFS/submodule 다운로드와 새 환경의 실제 실행은 이번 정리에서 검증하지 못했다.
  로컬 커밋 파일 검증 결과는 [검증 기록](docs/toast_quest/VALIDATION.json)에 구분해 기록한다.
