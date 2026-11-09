> **과거 작업 기록**: 원래 설명·수치·실행 결과를 보존한 자료이며 현재 실행 안내가 아닙니다. 최신 설정과 명령은 [Changes](../../../CHANGES.md)를 따르세요. 특히 2/0.5 gain은 원본 v2 기본값이 아니라 중간 비교 설정이며, 거치대 안정 지지와 실기 검증 주장은 최신 진단 상태와 함께 읽어야 합니다. 본문의 호스트 경로·logs는 당시 로컬 증거 위치입니다.

> 현재 실행 진입점: [README_TOAST_QUEST.md](../../../CHANGES.md). 아래 단계별 작업·측정 기록의 과거 값은 당시 설정입니다. 현재 v2 상승 목표/상한은 +35 mm이며 하한은 -45 mm입니다. 기록 속 PC IP·호스트 절대 경로·컨테이너 이름은 실행 환경에 맞게 설정해야 합니다. 최신 문서의 변수 기반 명령을 사용하세요.

현재 v2의 좌우 master joint1 속도 상한은 기본 6.5 rad/s이며 별도 속도 옵션이 필요 없다.
[설정/검증 보고서](GRIPPER_SPEED.md) 참조. 아래 과거 속도 비교 기록의 2.2는 당시 값이다.

현재 v2 그리퍼 설정: 좌우 master joint1 및 slave joint2/3/4 모두 stiffness=100.0,
damping=4.0이다. 과거 `--gripper-slave-gains-official`(2/0.5 비교) 옵션은 이제 거부된다.
현재 실행·readback 검증 결과는 [README_GRIPPER_GAINS.md](GRIPPER_GAINS.md) 참조.
아래 기존 실험 기록은 당시 결과이며 현재 기본값을 뜻하지 않는다.

# Quest Touch Plus → Toast v2: bounded two-arm test

## Meta 웹 캐스팅 기본 배치·설정 유지 — casting-fit-3

**실제 캐스팅 중앙 일치는 미검증이다.** 기본 배율 .50은 사용자 지정값이고 가로 중심 +.24는
실측 행렬을 참고한 추정값이다. 상태·네 카메라·테두리·십자가가 들어 있는 전체 패널을 함께 이동한다.

수정 전 최신 `packet.xr_display`에서 client build `preview-v3-643d85fe9ef3`, revision `casting-fit-2`,
배율 .60, 중심 (+.12,+.10), framebuffer 3360×1760을 확인했다.
왼눈 viewport는 (0,0,1680,1760), 오른눈은 (1680,0,1680,1760)이며 실제 중심도 요청값과 같아 clamp는 없었다.
왼눈 projectionMatrix[8] = −0.2425125688이다. 눈의 정면 벡터 (0,0,−1,1)를 투영하면
NDC x = −P[8] = +0.2425125688이므로 이를 +.24로 반올림했다.
현재 +.12에서 이동량은 (.24−.12)×1680/2 = **100.8 eye-viewport pixels 오른쪽**이다.
새 .50 배율에서 패널은 840×840 pixels, 눈 내부 중심은 (1041.6,968), NDC bounds는
[−.26,−.3772727,+.74,+.5772727]로 잘리지 않는다 (픽셀 y는 아래 원점 기준).
이 값은 Meta가 왼눈의 정면점을 캐스팅 중앙으로 삼는다는 가정의 추정이며 실제 crop 변환은 알 수 없다.
확인 가능한 첨부 캡처만으로 현재 분홍 십자와 영상 경계의 픽셀 대응을 정확히 구할 수는 없다.

눈별 viewport와 framebuffer 크기를 혼용하거나 십자만 따로 이동하지 않는다.
제어·시나리오·카메라 원본·기록·재생·입력 보호 코드는 변경하지 않았다.

### 새 기본값과 저장

| 설정 | 캐스팅 맞춤(최초 기본 모드) | Quest 기본 모드 |
|---|---|---|
| 배율 | .50 | .65 |
| 가로 중심 | +.24 (눈 viewport 폭의 12% 오른쪽) | 0 |
| 세로 중심 | +.10 (높이의 5% 위) | 0 |
| 영상 내부 여백 | .02 | .02 |
| 모서리 진단 | ON | OFF |

전체 패널(상태+네 카메라)을 함께 오른쪽·위로 이동하며, 배율은 .60에서 사용자 지정 .50으로 조정했다.
영상 종횡비·원본 카메라·UV는 그대로이며 영상을 잘라 채우지 않는다.
브라우저 localStorage `cyclo.quest.display.v2` (schema 2)에 모드와 모드별 배율/중심/여백/진단 표시를 저장한다.
v2 키가 없으면 페이지 로드 시 새 기본값을 즉시 한 번 저장한다. 기존 v1 키는 그대로 두되 읽지 않는다.
이후 v2의 사용자 수정값을 복원하며 기본값을 매번 덮어쓰지 않는다. 설정 변경 또는 VR 진입 시에도 저장하고, 새로고침·VR 재진입·일반 브라우저 재실행 후 같은 origin에서 복원한다.
IP/포트 변경, 사이트 데이터 삭제, 비공개 창 종료는 저장 범위를 바꿀 수 있다.
저장 차단/용량 오류는 페이지에 명시하고 현재 VR 표시는 계속 가능하다.
`현재 모드 기본값 복원`은 위 기본값으로 되돌리고 저장한다. 모드를 바꿔도 다른 모드의 저장값은 유지한다.

### 최소 적용 절차 — 기본값으로 한 번 확인

1. 가능하면 A로 기록을 마감하고 WAITING에서 진행한다. 시뮬레이터와 배치 작업은 재시작하지 않는다.
2. 사용자가 **입력 서버 터미널만** Ctrl+C로 종료하고 재실행한다. 서버가 시작 시 build를 고정하기 때문이다.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/server.py \
  --host 192.168.10.116 --port 8765 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab/logs/quest_teleop
```

3. Quest에서 VR을 종료하고 `https://192.168.10.116:8765/` 페이지를 새로고침한다.
   새 PIN으로 Pair한 뒤 CLIENT BUILD가 서버의 SERVER BUILD와 같은지 확인한다.
4. `casting-fit-3`, 캐스팅 맞춤 / .50 / +.24 / +.10이 자동 표시된다.
   **슬라이더는 조절하지 말고 Enter VR을 한 번 누른다.** 이미 v2 설정을 저장한 상태라면
   캐스팅 맞춤에서 `현재 모드 기본값 복원` 한 번으로 같은 기준에 맞출 수 있다.
5. Meta 캐스팅에서 TL/TR/BL/BR, 상태 문구와 하단 세 영상까지 들어오는지 한 번 확인한다.
   이후 새로고침·VR 재진입에도 설정은 유지된다. 이 확인 전에는 해결 완료로 보고하지 않는다.

이번부터 Applied XR 진단은 약 1초마다 갱신하여 기존 입력 패킷의 `xr_display`에 싣는다.
`logs/quest_teleop/input.json`과 `server_status.json`의 `packet.xr_display`에서 revision/build,
요청 설정, framebuffer, 각 눈 viewport·실제 scale/center/bounds·projectionMatrix,
`reported_client_ms`를 확인할 수 있다. 입력 수신 시각과 함께 오래된 진단인지 판단한다.
마지막 정상 draw의 진단이며 VR 종료 후 마지막 값이 남을 수 있다. 캐스팅 결과를 자동 판정하는 값은 아니다.
이 필드는 관찰용이고 제어 좌표·버튼·영상 유효성 판정에는 사용하지 않는다.

CPU/모의 검사: HUD geometry/render 16개 + 저장/복원 8개 + 버전 이전/실측 viewport 검사 6개 통과. 기존 Python 테스트는 앞선 작업에서 57개 통과했다.
실제 Quest 광학·Meta 캐스팅 중심과 가독성은 미검증이다.

## 현재 상태

- 사용자 실기 확인: 양손 `meta-quest-touch-plus`, `valid:true`, 위치/회전 수신, 버튼 `pressed:true`, 양쪽 초록 표시.
- **스틱은 실기 미검증이며 로봇 action에 사용하지 않는다.**
- 이번 수정: 엄격한 입력 소스 선택, 무효 사유/통신 구분, 로컬 IPC, bounded 양팔 제어, 선택적 그리퍼,
  착용 상태에서 확인할 카메라 패널 구현. 변경된 HUD·로봇 움직임·그리퍼는 GPU/Quest 실기 미검증.
- CPU 테스트 57개 PASS(Quest 43, metadata 6, scenario loader 8), 소스 선택 JS 테스트 10개 및 preview client 모의 테스트 8개 PASS, JS 문법 검사 PASS.
- 이 세션에서는 NVIDIA/NVML 및 Docker 소켓 접근이 불가능했다. GPU 유휴 여부는 확인되지 않았다.
  시뮬레이터를 시작하지 않았으며 실행 중 진단 서버/시나리오 작업을 중지하지 않았다.
- 기존 recorder 연결 및 B 첫 시나리오 테스트 저장/replay 경로 구현. 실제 저장·replay는 미검증, 이 작업의 수집 시연 0회. 로봇 하드웨어/Zenoh 연결 없음.

## Operator B 첫 시나리오: 현재 실행 절차

아래 1–4단계를 현재 운영 절차로 사용한다. marker-file 입력은 호환용으로만 남아 있으며 X/A 또는 n/s를 사용한다. 구현은 준비되었으나
**실제 GPU 기록·재생 및 Quest 화면/캐스팅 개선은 미검증**이다. 이 작업에서 실제 시연은 저장하지 않았다.
`operator_B`, `scenario_index=1`은 `scenario_delivery/assignments.csv` 순서로 해석하며
`batch02_toast_001`인지 별도로 검사한다. 전체 목록의 51번을 사용하는 방식이 아니다.

### 1. 입력 서버 적용

실행 중인 서버와 시뮬레이터를 자동 종료하지 않았다. 사용자가 현재 teleop 터미널에서 Ctrl+C로
종료한 뒤, **진단 서버 터미널만** Ctrl+C로 종료하고 다음 명령으로 다시 실행한다.
시나리오 배치 작업은 종료하지 않는다. 새 GPU 작업 전 `nvidia-smi`로 기존 작업 사용량을 확인한다.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/server.py \
  --host 192.168.10.116 --port 8765 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab/logs/quest_teleop
```

Quest를 착용하고 Browser에서 **https://192.168.10.116:8765/** 를 다시 연다.
터미널의 새 6자리 PIN으로 Pair한다. `CLIENT BUILD`가 터미널 `SERVER BUILD`와 같고
`Secure context / WebXR / immersive-vr`가 모두 true인지 확인한 다음 **Enter VR diagnostic**을 누른다.
서버 재시작은 쿠키를 무효화한다. 같은 서버에서 다음 에피소드/일반 새로고침/VR 재진입은 유효한
8시간 쿠키가 있으면 PIN 재입력이 필요 없다. 브라우저 재실행은 쿠키 보존 여부에 달려 있다.

### 2. 움직이지 않고 네 카메라 확인

기존 teleop이 종료되었고 다른 GPU 작업과 중복되지 않는 시점에 한 번만 실행한다.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --preview-only --keep-open
```

시작 로그에 `SCENARIO_SELECTED ... id=batch02_toast_001 seed=1`, manifest SHA256,
`RESET_POSES_OK`의 7개 실제 pose, `READY / WAITING`이 보여야 한다.
**X/n을 누르지 않아도 WAITING에서 영상은 갱신된다.** WAITING은 render만 하며 물리 시간은 진행하지 않는다.
상단 FRONT OVERVIEW, 하단 HEAD / LEFT WRIST / RIGHT WRIST를 확인한다.
VR 패널은 종횡비를 보존한다. 잘리면 VR에서 나온 뒤 웹페이지의 `Scale`을 줄이고 다시 진입한다.
`Inner margin`은 패널 내부 여백이다. Quest 기본 모드 scale=.65, margin=.02. 캐스팅 맞춤은 상단의 저장형 기본값을 사용한다.
PC 캐스팅의 실제 crop 개선은 별도로 확인해야 한다. 이 페이지가 PC 입력 모드를 제공하는 것은 아니다.
카메라를 확인했으면 이 teleop 터미널에서 Ctrl+C로 종료한다. 입력 서버는 유지한다.

### 3. 같은 시나리오에서 짧게 조작·저장

아래 디렉터리는 **새 경로**여야 한다. 이미 존재하면 `B001_test_002` 등 새 이름을 사용한다.
정식 성공 시연과 구분해 `datasets/quest_tests/`에만 이 테스트를 보관한다.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open \
  --record-dir /workspace/cyclo_lab/datasets/quest_tests/B001_test_001 \
  --record-seconds 8
```

1. Quest를 착용하고 정면을 본다. 양손 squeeze(옆면 쥐기 버튼)를 모두 놓는다.
   양손 유효 입력과 최신 영상이 있어야 시작 가능하다.
2. **왼쪽 X를 한 번 누른 뒤 놓는다.** 또는 PC teleop 터미널에서 `n`+Enter.
   같은 시나리오/seed로 reset 후 `EPISODE_STARTED`가 출력된다. 이때부터 기록한다.
3. squeeze가 놓인 상태에서 새 기준을 설정한 후 **왼쪽 squeeze만 다시 눌러** 컨트롤러를
   앞으로 2–4cm 정도 천천히 움직이고 놓는다. 목표 이동은 그 0.25배다. 첫 테스트는 한쪽 팔만 사용한다.
4. **오른쪽 A를 한 번 누르거나 `s`+Enter**로 짧게 마감한다. 누르지 않아도 시작 후
   약 8 wall seconds에 마감한다. GPU 지연이 있으면 실제 simulation 기록 길이는 더 짧다.
   `RECORD_SAVED demo_0 ... success=False`와 `EPISODE_WAITING`을 확인한다.
5. 다음 테스트는 squeeze를 모두 놓고 X/n으로 명시적 시작한다. 파일 안에 demo_1 등이 추가된다.
   `--keep-open`은 앱 유지 옵션이며 원래 **240 simulation seconds timeout**을 늘리지 않는다.
6. 최종 종료는 Ctrl+C (또는 `q`+Enter). 활성 기록을 마감하고 HDF5를 닫은 뒤
   `RECORD_FINALIZED`와 producer `stopped` 상태를 남긴다. 중간 step에서 중단됐다면
   obs/actions/states가 모두 있는 완결 행까지만 저장한다. 완결 행이 없으면 빈 에피소드는 저장하지 않는다.

X=reset/start, A=save/wait는 edge 방식이다. 버튼을 계속 누른 채로 다음 에피소드가 시작되지 않는다.
B/Y는 기존 정면 재설정, squeeze는 clutch다. 위치 .25/회전 .5, 초기 기준 5cm/15도 제한,
그리퍼 열린 상태 고정과 lift 고정을 유지한다. 트리거/스틱으로 물체를 잡는 단계가 아니다.
입력/영상 손실 때 목표 유지, 복구 후 squeeze 해제·재입력 조건도 유지한다.
실패·미완료 기록도 테스트 파일에 저장되며 `success=False`, `diagnostic=True`이다.
원래 성공 판정 결과는 별도 `task_success_observed`에 남긴다. 폐기할 테스트는 정식 수집에 포함하지 말고
파일을 그대로 두거나 종료 후 별도 보관한다. 이 실행기에는 저장한 에피소드 삭제 버튼이 없다.

### 4. 종료 후 CPU 파일 검사 → action replay → 참고 영상

시뮬레이터를 종료하고 HDF5가 닫힌 뒤 검사한다. 입력 서버는 켜 두어도 된다.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/tools/toast_recording_metadata.py \
  /workspace/cyclo_lab/datasets/quest_tests/B001_test_001/dataset.hdf5
```

이 명령은 시뮬레이터를 시작하지 않는다. actions [N,15], 세 RGB [N,244,244,3],
초기 상태/후속 상태, toast_cycle, 프레임 정합성과 manifest hash를 검사한다.

다음은 **action으로 실제 물리를 다시 계산하는 replay**다. 앞의 teleop과 동시에 실행하지 않는다.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_demos.py \
  --dataset_file /workspace/cyclo_lab/datasets/quest_tests/B001_test_001/dataset.hdf5 \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episodes 0 --headless --enable_cameras --validate_states
```

`SCENARIO_REPLAY batch02_toast_001`, `STATIC_RACK_POSE_OK`, `REPLAY_INITIAL_STATE_OK`,
마지막 `REPLAY_VALIDATION checked=... mismatched=0`을 확인한다.
초기 로봇/물체 상태·toast cycle을 검사하고, static rack은 별도 world pose로 검사한다.
후속 상태 비교는 기존 replay의 절대 오차 .01 기준이다. mismatch가 있으면 진단 replay는 오류로 종료한다.
replay의 기존 termination 비활성화 동작은 그대로이며 원래 작업 정의의 판정을 변경하지 않는다.

그다음 참고 영상처럼 **저장 상태를 렌더링하는 MP4**를 만든다. 이 명령은 action 물리 replay 검증과 다르다.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_demos.py \
  --dataset_file /workspace/cyclo_lab/datasets/quest_tests/B001_test_001/dataset.hdf5 \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episodes 0 \
  --video_file /workspace/cyclo_lab/datasets/quest_tests/B001_test_001/replay.mp4
```

PC 파일 위치: `datasets/quest_tests/B001_test_001/replay.mp4`.
FRONT OVERVIEW는 저장된 scene state를 새 카메라로 렌더링하며, 아래 세 영상은 원래 기록된 RGB다.
live/replay는 같은 `toast_overview.py` 카메라(eye 3.1,0,2 / target .35,0,1)를 사용한다.
새 overview는 학습 policy 관측이나 HDF5 RGB에 추가하지 않았다.

### 메타데이터와 검증 범위

기록 디렉터리에는 원본 manifest의 byte-for-byte snapshot, metadata.json, 기존 Isaac Lab recorder의
`dataset.hdf5`가 들어간다. HDF5와 sidecar에 operator/index/ID/seed/hash/측정 reset pose/
physics dt/decimation/control dt를 저장하고 에피소드에 종료 사유와 판정 결과를 추가한다.
시간은 wall-monotonic, simulation elapsed time, 시작·종료 Unix time을 저장한다.
기존 policy의 로봇 관측, 세 카메라 RGB, actions, processed_actions, 초기/후속 scene state,
toast_cycle을 재사용한다. raw Quest pose/buttons와 새 overview RGB는 학습 데이터로 저장하지 않는다.

replay는 기록 옆 manifest snapshot의 hash를 확인하고 **gym.make 전에** scenario/manifest/seed를 적용한다.
누락·변조·task/timing/static-rack metadata 불일치에는 오류로 중단한다. 현재 프로젝트 manifest로
조용히 대체하지 않는다. 실제 reset과 초기 상태 복원의 일치는 GPU 실행 시 추가 assert한다.

CPU: Python 57개(Quest 43 + metadata 6 + 기존 scenario loader 8), JS 입력 10개,
preview 8개 모의 테스트, Python/JS 문법, 합성 영상 종횡비 검사 통과.
모의 recorder 테스트는 실제 HDF5 write의 증거가 아니다. GPU 접근 불가로 실제 HDF5 생성·static rack
world pose·물리 replay 일치·Quest 네 영상·캐스팅은 미검증이다.


## 적용 환경과 실제 action 계약

`docker/.env.base`는 Isaac Sim 5.1.0, `/isaac-sim`, `/workspace/cyclo_lab`을 지정한다.
체크아웃의 `third_party/IsaacLab/VERSION`은 2.3.0이고 기존 시나리오 로그에도 Sim 5.1 기록이 있다.
실행 중 컨테이너의 패치 버전/드라이버는 직접 조회하지 못했다. 업그레이드하지 않았다.
프로젝트 및 scripts 경로에서 적용 대상 AGENTS.md를 발견하지 못했다.

대상: `Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2`, FFW-BG2,
`MakeToastFFWBG2BimanualEnv` + `MakeToastFFWBG2BimanualServeEnvCfg`.

| action 인덱스 | 실제 의미 |
|---|---|
| 0:6 | 왼손목 arm_l_link7, base-frame 위치 delta 3 + axis-angle 회전 delta 3 |
| 6:12 | 오른손목 arm_r_link7, 같은 형식 |
| 12,13 | 왼/오른 CoupledGripperPositionAction: +1 열기, -1 닫기, 중간값 연속 보간 |
| 14 | lift target = .25 × action − .25, joint 범위 [-.5,0] |

기존 `StandbyPostureIKAction`/DLS/relative pose/scale=.3을 그대로 사용한다.
`arm_action.py`의 null-space standby 보정과 관절 제한 회피도 그대로 남는다.
그리퍼 joint target은 open=0, closed=1.10이며 단순 bool action이 아니다.
테스트 실행기는 action 이름/차원/IK 설정을 assert하고, 기존
`action_to_target_eef_pose` ↔ `target_eef_pose_to_action` round-trip을 비영(非零) 샘플로 검사한다.
이 샘플 action은 로봇에 적용하지 않는다.

## 입력 선택과 상태 표시

`input.js`는 아래 규칙을 적용한다.

1. `source.hand`가 있거나 profiles 중 `hand`가 포함된 이름이 있으면 제외. `meta-fixed-hand`도 제외.
2. **`meta-quest-touch-plus`가 profiles에 있어야 허용**. 다른 controller fallback만 있는 경우도 현재는 거부.
3. tracked-pointer, xr-standard gamepad, 실제 grip pose, !emulatedPosition, visible 세션 검사.
4. 같은 handedness 후보를 각각 새 객체로 평가한다. 유효 Touch Plus 우선, 복수 유효 소스는 안정적인 source ID 순.
5. 유효 소스가 없으면 선택된 무효 후보의 reason만 표시하며 이전 pose/button을 섞지 않는다.
   후보 요약 `candidates`와 선택된 `source_id`를 로그에서 확인할 수 있다.

Python 수신기와 제어 어댑터도 프로필을 다시 검사한다. 구버전 페이지에서 손 프로필을 valid=true로 보내도
서버가 valid=false로 바꾸고 pose/button을 지운다.

HUD의 왼손/오른손 패널: 초록=유효 입력, 밝은 초록=버튼 pressed, 황색=무효 입력과 reason.
COMM은 별도: ACK OK / 응답 지연 / HTTP 오류. 초록 입력 패널만으로 통신 정상 또는 로봇 활성화를 뜻하지 않는다.
손 입력 제외, profile 거부, grip pose 없음, emulated position, visibility 등의 원인을 문자열로 표시한다.

서버 `communication=receiving`은 최근 패킷 도착을 뜻한다.
`live=true`는 최근 250ms 내 패킷 + visibility=visible이며, 양손 valid와 별개다.
입력/preview 유효→무효 전환 및 수신 공백은 `safety_epoch`에 남겨 시뮬레이터가 짧은 손실 프레임을 건너뛰어도
복귀 직후 버튼 release가 필요하도록 했다. 실제 입력 소스 교체도 재기준화한다.

## 제어 방식과 제한

- CPU 어댑터의 pose는 **로봇 root/base 기준 손목 위치와 xyzw quaternion**이다.
  Isaac의 wxyz를 입력/출력 경계에서 바꾼다. 손가락 TCP offset을 새로 추가하지 않는다.
- WebXR는 local-floor metre 좌표: +X 오른쪽, +Y 위, -Z 정면.
- 초기/재기준 시 헤드셋 정면을 바닥 평면에 투영하여 사용자 forward/right를 구한다.
  사용자 forward→로봇 +X, 사용자 left→로봇 +Y, 위→로봇 +Z.
  헤드셋이 기본 정면이면 `(xr_x,xr_y,xr_z) → (-xr_z,-xr_x,xr_y)`.
- 양손 squeeze를 모두 놓고 로봇의 정면으로 삼을 방향을 보면 초기 기준을 설정한다.
  이후 머리 회전은 제어 좌표계를 계속 회전시키지 않는다.
- 각 손 squeeze를 새로 누르는 순간 controller pose와 유지 중인 robot target을 anchor로 잡는다.
  그 순간에는 이동하지 않는다. 이후 anchor 대비 이동 × **0.25**, 회전 × **0.5**를 적용한다.
  회전은 `q_current × inverse(q_anchor)`의 shortest axis-angle을 같은 기저로 변환 후 robot anchor에 왼쪽 곱한다.
- 목표 범위: 초기 안정화된 손목에서 반경 **5cm**, 초기 방향에서 **15도**. 여러 번 clutch/rebase해도 범위는 누적 확장되지 않는다.
- IK action은 매 step 측정 자세와 유지 목표의 오차를 구해 `.3`으로 나눈다.
  오차 보정은 **0.05m/s**, **0.5rad/s**에 해당하는 step별 한도로 제한한다.
  25Hz라면 1 step 최대 2mm / .02rad 보정이다. 실제 손목 속도를 보장하는 물리 속도 제한은 아니다.
- 버튼 해제/추적 손실/250ms 수신 공백/1초 이상 오래된 화면/시뮬레이션 loop 지연 시 **마지막 목표 유지**.
  zero action을 반복해서 목표가 현재 자세로 떠다니게 하지 않는다.
  기존 IK servo가 유지 목표로 수렴하거나 null-space 자세를 보정하는 움직임은 남을 수 있다.
- 복귀/새 session/새 source/reference reset/server 교체 시 squeeze를 놓았다 다시 눌러 새 anchor 설정.
  1 sample 이동 >20cm 또는 회전 >60도도 동작 중단 후 release 요구.
- 목표와 실제 손목 위치 차이가 8cm를 넘으면 실행기를 종료한다.
- 리프트는 초기 관절 위치에 대응하는 action으로 고정한다. 스틱/베이스 이동 없음.
- 원래 termination/timeout은 유지한다. 발생하면 기록을 마감하고 환경의 원래 reset 동작 후 WAITING으로 전환한다.
  WAITING에서는 render만 수행한다. `--keep-open`이면 X/n으로 다음 에피소드를 시작할 때까지 앱을 유지한다.

| 버튼 | 역할 |
|---|---|
| 각 손 중지 squeeze, buttons[1] | 그 손 clutch. 값 >=.8 활성, <.2 완전히 놓음/재활성 준비 |
| 각 손 검지 trigger, buttons[0] | `--enable-grippers`에서만: squeeze 중 +1−2×trigger값으로 열기/닫기 |
| 오른손 B / 왼손 Y, buttons[5] | 양손 squeeze를 놓은 상태에서 정면 기준 재설정; 로봇/환경 reset 아님 |
| 왼손 X, buttons[4] / 터미널 n+Enter | WAITING에서 같은 시나리오 reset 후 시작. RUNNING에서는 무시 |
| 오른손 A, buttons[4] / 터미널 s+Enter | RUNNING에서 기록 마감 후 WAITING. 기록 옵션이 없으면 저장 없이 대기 |
| thumbstick | 로봇 명령 없음. 스틱 실기 미검증 |

버튼 인덱스는 [공식 WebXR input profile](https://github.com/immersive-web/webxr-input-profiles/blob/main/packages/registry/profiles/meta/meta-quest-touch-plus.json)에 맞춘다.
사용자의 A/X/trigger 입력은 확인되었지만 **squeeze와 B/Y 매핑은 새 테스트 전에 로그로 확인**한다.
첫 실행은 `--enable-grippers`를 주지 않아 그리퍼를 열린 상태로 고정한다.

## 연결 구조와 카메라

```text
Quest HTTPS → 인증된 Python 입력 서버 → 로컬 input.json → Isaac Sim test → 기존 15D IK
                         ↑                     ↓
                   /preview.jpg ← FRONT OVERVIEW + head/left wrist/right wrist 합성 JPEG
```

`--bridge-dir`을 주지 않은 서버는 로봇용 IPC를 쓰지 않는다.
IPC 디렉터리는 사용자 전용, input.json은 0600 atomic replace. Linux monotonic 수신시각을 사용한다.
기본 host-network Docker는 호스트와 monotonic clock을 공유한다. 별도 time namespace는 지원하지 않는다.
같은 디렉터리의 입력 서버/시뮬레이터 중복 실행을 각각 flock으로 막는다.

약 5Hz의 합성 화면 위에는 관찰용 FRONT OVERVIEW, 아래에는 기존 244×244 세 카메라를 표시한다.
기존 세 카메라와 학습 관측은 유지한다. overview는 학습 RGB에 저장하지 않으며 replay 영상에서 저장 상태로 재렌더링한다.
헤드셋의 정면 고정 패널이며 **입체 CloudXR 스트리밍이 아니다**. GPU→CPU JPEG 변환 비용이 있다.
HTTP 이미지 age와 요청시간을 고려해 1초 이상 오래된 영상이면 화면/조작을 무효화한다.
서버 종료/영상 중단 때도 시뮬레이션은 마지막 손목/그리퍼 목표를 유지한다.
preview.jpg는 root Docker writer와 호스트 reader 간 공유를 위해 0644, 외부 디렉터리는 기본 0700이다.

## 실행 전 GPU 작업 확인

실행 명령과 버튼 순서는 이 문서 상단의 **Operator B 첫 시나리오: 현재 실행 절차**를 사용한다.
이전의 `--headless --duration 180`만 사용한 명령은 B 시나리오 선택·기록·무기한 대기를 지정하지 않으므로 이 목표에 사용하지 않는다.

```bash
nvidia-smi
docker ps --format '{{.Names}} {{.Image}} {{.Status}}'
docker top cyclo_lab
```

시나리오 배치/다른 Isaac Sim이 실행 중이면 새 시뮬레이터를 중복 실행하지 않는다.
이 세션의 NVIDIA/Docker 접근 실패는 연구실 PC 드라이버 고장을 뜻하지 않는다.
현재 서버와 페이지의 build가 같으면 이번 문서 정리만을 위해 서버를 재시작할 필요는 없다.

## PIN 재입력이 필요한 시점

코드 수명과 인증 세션 수명은 다르다. PIN은 5분/5회/1회 사용,
인증 쿠키와 서버 token은 **페어링 시점부터 8시간**이며 활동할 때마다 연장하지 않는다.
쿠키는 Secure, HttpOnly, SameSite=Strict, Max-Age=28800; token 목록은 서버 메모리에만 있다.

| 상황 | PIN 재입력 |
|---|---|
| 같은 연결에서 다음 시연/시뮬레이션 시작 | 원칙적으로 불필요. 입력 서버와 8시간 인증이 유지되어야 함. X/n으로 다음 기록 시작 가능 |
| Quest 페이지 새로고침 또는 VR 종료 후 재진입 | 원칙적으로 불필요. 쿠키/서버 token 유지 시 자동 확인. VR 기준과 clutch는 새로 설정 |
| 브라우저 종료 후 다시 실행 | 일반 창에서 영속 쿠키가 보존되고 8시간 이내면 불필요. 비공개 창/쿠키 삭제/브라우저 정책으로 지워졌으면 필요 |
| PC **입력 서버** 재시작 | **필요**. 기존 쿠키가 남아도 새 서버 메모리에 token이 없음. 인증서 재사용과 무관 |
| Isaac Sim 테스트 실행기만 재시작 | 입력 서버가 그대로면 불필요. 로봇 기준/초기 위치는 새 실행에서 재설정 |

8시간 만료, 새 브라우저 프로필, PC IP 변경, 쿠키 삭제 또는 8개 인증 세션 제한으로 오래된 token 제거 시에도 필요하다.
서버 터미널 `p`는 새 PIN만 만들며 기존 인증 세션을 즉시 취소하지 않는다.

## 검증과 남은 작업

```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 -m unittest discover -s scripts/quest_diagnostic -p 'test_*.py' -v
python3 -m py_compile scripts/quest_diagnostic/*.py
```

현재 Python CPU 테스트 57개(Quest 43 + metadata 6 + scenario loader 8): 기존 인증/TLS/수신기 + hand 차단, bridge timeout/손실 epoch,
좌표 및 head yaw/회전 변환, 양팔 독립, clutch/재연결/rebase, loop stall/영상 손실,
workspace/회전/action 보정 범위, 선택적 그리퍼/lift 고정.
`test_input.js`의 10개 소스 선택 테스트는 V8에서 실행했다.
preview client의 HTTP 실패/디코딩 실패/그리기 확인/만료를 모의 API로 8개 테스트했다.
실제 WebGL texture 렌더링 및 Quest의 화면 표시는 확인이 필요하다.
**사용자 실행에서 환경 초기화/READY와 실제 카메라 JPEG 생성은 확인했다. 새 HUD 표시/영상 확인 전달/양팔 동작은 검증 대기**다.

기존 README_TOAST.md 사용자 변경, 환경 정의, 물리/보상/성공 조건, 시나리오 정의를 수정하지 않았다.
현재 연결 파일: `scripts/quest_diagnostic/teleop_toast.py`, `episode_control.py`, `diagnostic_recorder.py`,
`index.html`/`hud.js`, `scripts/tools/toast_overview.py`, `toast_recording_metadata.py`,
`replay_demos.py`, `replay_video.py` 및 CPU 테스트.

기존 ActionStateRecorderManagerCfg를 연결했으며 initial_state, states, actions, processed_actions,
policy obs(기존 세 카메라 포함), toast_cycle, step별 wall/simulation 시간을 저장한다.
Quest raw 입력은 저장하지 않는다. 실제 GPU 저장·재생은 검증 대기다.

## 과거 진단 기록: 영상 미표시 조사와 preview-v3 수정 (2026-11-02)

아래는 당시 증거와 문제 해결 기록이다. 현재 카메라 구성·실행 명령·조작은 상단의 B 시나리오 절차를 따른다.

### 확인된 증거와 한계

- 조사 시 `logs/quest_teleop/preview.jpg`는 732×280 JPEG, 13,661 bytes, 0644,
  sandbox에서 uid/gid 65534(nobody/nogroup)로 보였다. 파일을 직접 열어 토스터/로봇 영상을 확인했다.
  따라서 적어도 마지막 JPEG의 RGB 생성·인코딩·호스트 읽기까지는 성공했다.
- `args.enable_cameras=True`가 AppLauncher 생성 전에 설정된다. 체크아웃된 Lab app_launcher.py는
  headless+enable_cameras에서 `isaaclab.python.headless.rendering.kit`을 선택한다.
  headless 자체가 카메라를 끄는 구성이 아니며 실제 JPEG도 이를 뒷받침한다.
- `input.json`에는 visibility=visible이지만 `preview_ok`, `head_quaternion_xyzw`가 없었다.
  이 필드들은 직전 페이지의 매 XR frame 패킷에 항상 들어가므로 **예전 진단 페이지가 계속 실행 중인 정황**이다.
  사용자가 본 '초록 네모만 있음'도 이전 scissor-only 렌더링과 일치한다.
- 기존 make_handler는 HTML을 서버 시작 시 한 번 읽었다. `Cache-Control: no-store`가 있어도 이미 열린
  탭의 실행 중 JavaScript를 교체하지 않으며, 이전 서버의 메모리에 든 HTML도 바꾸지 않는다.
  브라우저 캐시인지, 열린 탭인지, 오래된 서버 페이지인지는 당시 served HTML에 접근하지 못해 확정할 수 없다.
- 기존에는 preview 메타데이터/HTTP 카운터가 없었다. 남은 JPEG 하나로 연속 갱신 주기나 당시 HTTP 200,
  이미지 디코딩/VR 표시 성공까지 증명하지 않는다.
- Docker inspect와 HTTPS 직접 조회는 이 세션에서 실패했다. 현행 컨테이너 mount와 서버 프로세스 UID의
  직접 검증은 남았다. 그러나 사용자 로그의 live:true와 호스트 JPEG 존재는 양방향 파일 공유 성공의 근거다.
- 실행기가 셸로 돌아온 것은 --duration 180에 따른 종료일 수 있다. 마지막 exit code/종료 로그가 없으므로
  정확한 종료 원인은 단정하지 않는다. 남은 JPEG는 기존 finally의 삭제가 실제 수행됐다는 증거가 아니다.

### preview_not_live 판정과 강화한 경로

기존 control.py는 `live=true`, loop gap 없음, `packet.get('preview_ok',False)==false`이면
`preview_not_live`를 출력했다. **필드가 아예 없어도 false**이다. 입력 수신 live와 영상 live는 별개다.
기존 페이지는 HTTP 200→createImageBitmap 성공→유효기간 1초 + viewer 존재만으로 preview_ok를 보냈으며
그리기 성공 자체는 확인하지 않았다. 비200/디코딩 예외도 화면 밖에서 숨겨졌다.

수정 경로:

1. 생산자: `preview.jpg` + `preview.json`에 run_id/frame_id, monotonic capture 시각,
   SHA-256/크기, RGB shape/dtype/min/max/mean/std, step 시간/프레임 간격을 남긴다.
   메타데이터를 commit record로 마지막에 쓰고 읽는 쪽은 hash/신선도를 확인한다.
2. 서버: 인증된 `/preview.jpg`에서 JPEG + age/frame/run 헤더를 반환한다.
   bridge 미설정, 파일 없음, 권한 오류, 오래된 프레임, 생산자 종료, publication 경합을
   HTTP 503 JSON reason으로 구분한다. 401도 요청 카운터에 남긴다.
3. 브라우저: HTTP/디코딩 상태·오류와 received/decoded/drawn 카운터, frame/run ID를 표시·전송한다.
   숨기는 catch 대신 `fetch_or_decode_error`, `http_error`, `draw_error`를 남긴다.
4. HUD: 새 이미지면 즉시 texture 업로드한다. WebGL context/error를 검사하고 view draw 제출이 성공한
   **다음에** preview_ok를 보낸다. 이미지가 1초 이상 오래되면 여전히 false.
5. 서버: client protocol/build 일치, 유효한 producer run/frame과 `draw_submitted` 확인을 추가한다.
   이를 통과한 preview_ok만 로컬 IPC에 전달한다. 구버전 client는 입력 로그를 받더라도 로봇은 hold한다.

`draw_submitted`는 소프트웨어가 WebGL 그리기를 제출했다는 의미다. 실제 사용자의 눈에 영상이 보였다는
증명은 아니므로 **Quest 화면의 직접 확인은 필수**다. 영상 보호 조건은 완화하지 않았다.
생산자가 종료하면 JPEG는 조사용으로 보존하되 metadata=stopped로 무효화한다.
강제 종료로 stopped 기록이 없더라도 기존 1초 freshness 제한으로 거부한다.

### 적용 절차와 정확한 영상 전용 실행 명령

1. 기존 입력 서버를 수정 작업 중 종료하지 않았다. 적용할 때 사용자가 **그 입력 서버 터미널만** Ctrl+C하고
   위의 `server.py --host ... --port ... --bridge-dir ...` 명령으로 재시작한다.
2. Quest에서 VR을 나와 기존 진단 탭을 닫고 Browser에서 **`https://192.168.10.116:8765/`**를 다시 연다.
   PC의 `SERVER BUILD: preview-v3-…`와 페이지의 **CLIENT BUILD**가 정확히 같아야 한다.
   `/version`에서도 server_build와 disk_build를 확인할 수 있다. 다르면 VR 진입 버튼이 활성화되지 않는다.
   새 서버이므로 PIN을 다시 입력한다. 버전 query와 no-store를 사용하고 HTML은 GET마다 읽는다.
3. 다른 GPU/시나리오 작업이 없는지 확인한 다음 아래 **영상 전용** 테스트를 실행한다.
   이 모드는 controller.update를 호출하지 않아 사용자 입력으로 목표를 바꾸지 않는다.
   기존 IK로 초기 자세를 유지하는 물리 안정화 움직임은 있을 수 있다.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab \
  /isaac-sim/python.sh scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --headless --preview-only --duration 180
```

4. Quest에서 Enter VR. **버전 문구, COMM, 좌우 상태, 실제 3개 카메라 영상**이 보여야 한다.
   PC에 CAMERA FIRST FRAME이 나오고, 서버의 preview_http.sent 증가,
   client preview_status의 decoded/drawn 증가와 stage=draw_submitted를 각각 확인한다.
   input.json의 최종 preview_ok=true, preview_guard_reason=ok까지 확인한다.
5. 영상이 보이지 않으면 보호 조건을 우회하지 말고, 실행 중 별도 PC 터미널에서 아래 읽기 전용 진단을 실행한다.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/inspect_preview.py \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab/logs/quest_teleop

docker exec -w /workspace/cyclo_lab cyclo_lab \
  /isaac-sim/python.sh scripts/quest_diagnostic/inspect_preview.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop
```

같은 producer run_id/frame_id(갱신 중이면 근접한 번호)와 JPEG 크기/메타데이터가 보이면 경로 공유를 확인할 수 있다.
모든 파일에 대해 uid/gid/mode와 읽기 오류를 보고한다. 서버는 server_status.json에 최신 진단을 남긴다.

| 관찰 | 실패 구간 |
|---|---|
| CAMERA FIRST FRAME 없음 / preview metadata 없음 | 시뮬레이터 RGB/인코딩/파일쓰기 확인 |
| producer=ok, HTTP requests=0 | 열린 페이지가 새 버전인지, VR 세션/페어링/preview poll 실행 확인 |
| HTTP last=file_missing/permission_denied | 서버 bridge 경로·권한 |
| HTTP last=frame_stale | 생산 갱신/성능. step_ms와 frame_interval_ms 확인, 보호 시간 늘리지 않음 |
| HTTP sent 증가, decoded=0 | HTTP 응답 수신/이미지 decode 오류 확인 |
| decoded 증가, drawn=0 | viewer/WebGL texture 업로드·그리기 오류 확인 |
| drawn 증가, preview_guard_reason 오류 | client/server build, run/frame, metadata freshness 확인 |
| preview_ok=true지만 눈에 안 보임 | 실제 HUD/양안 표시 조사 필요. 그리기 제출 성공과 가시성은 다름 |

이번 수정은 CPU 테스트와 mock HTTP/JS까지만 검증했다. GPU를 중복 실행하거나 실제 Quest에 접속하지 않았다.
영상 전용 확인을 마치기 전에는 --preview-only를 빼고 양팔 테스트를 진행하지 않는다.


## action replay 첫 프레임 지연 조사 및 demo_8 선택

실제 B001_test_001 HDF5의 이름 순서는 demo_0, demo_1, demo_10, demo_2, …이다.
**목록 인덱스 8은 demo_7, demo_8의 인덱스는 9**이다. 이름 선택을 사용한다.
원본 demo_8/actions는 [95,15]이며 데이터 파일은 읽기 전용으로 검사했다.

기존 비교는 GPU 원소마다 Python 조건문을 실행했고 NaN을 실패로 처리하지 않았다.
새 비교기는 텐서 필드 전체를 CPU로 옮긴 뒤 NumPy로 벡터 비교한다. 절대 허용오차 .01은 유지하고
상대 허용오차는 없다. shape/key 불일치 및 NaN/Inf는 실패다. 상세 오차 출력은 길이를 제한한다.
get_state BEGIN/END, compare_states BEGIN/END, compare.cpu_transfer BEGIN/END,
compare.numpy BEGIN/END가 flush와 elapsed_s를 출력한다. get_state 시간은 호스트 반환까지이며,
GPU 완료 대기는 cpu_transfer 단계에서 드러날 수 있다. 원래 멈춤 위치는 아직 실기로 확정하지 않았다.

이번 환경에서는 Docker 접근이 거부되고 NVML 조회가 실패했다. 격리된 ps로 기존 replay PID를
확인할 수 없어 프로세스를 종료하거나 새 GPU replay를 실행하지 않았다.
CPU 단위 테스트 6개와 실제 저장 상태 95프레임/18필드의 자기 비교 및 오차 주입은 통과했다.
이것은 물리 action replay의 checked=95/mismatched=0 증거가 아니다.

호스트의 기존 replay 터미널에서 해당 replay만 Ctrl+C로 정리하고 종료를 확인한 뒤 실행한다.
프로세스를 확인해야 한다면 `docker top cyclo_lab -eo pid,ppid,args`로 명령을 대조한다.
확인되지 않은 PID나 다른 시뮬레이터를 종료하지 않는다.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_demos.py \
  --dataset_file /workspace/cyclo_lab/datasets/quest_tests/B001_test_001/dataset.hdf5 \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episode_names demo_8 --headless --enable_cameras --validate_states
```

기대되는 선택 로그는 `indices=[9] names=['demo_8']`, `EPISODE_LOADED ... frames=95`다.
완료 기준은 `REPLAY_VALIDATION checked=95 mismatched=0 expected=95`, `APP_CLOSE END`,
`REPLAY_EXIT status=completed code=0`이다. 비교 실패나 프레임 수 부족은 오류 종료한다.
중단/예외에서도 진행 카운트를 출력하고 환경·파일·앱 정리를 시도한다.

### 실제 EpisodeData 환경 축 수정 및 프로세스 종료 확인

`EpisodeData.get_state()`는 `states[state_index, None]`을 반환한다. 따라서 실제 로더를 통과하면
저장 상태의 joint_position은 (1,25), root_pose는 (1,7), root_velocity는 (1,6)이다.
이전 비교기는 runtime에서만 환경 축을 제거해서 전 프레임을 shape mismatch로 판단했다.
기존 직접 HDF5 배열 인덱싱 CPU 테스트는 이 로더 동작을 재현하지 못했다.

replay 호출에 `dataset_has_single_env_axis=True`를 명시하고 다음 조건을 모두 확인한 뒤
저장 상태의 첫 축만 `[0]`으로 처리한다: runtime 환경 수=1/index=0, 저장 첫 축=1,
저장 ndim=runtime 샘플 ndim+1, 나머지 shape 완전 일치. 일반 squeeze/flatten/broadcast 정렬은 없다.
허용오차 .01, key/shape 검사와 NaN/Inf 실패 처리는 유지한다.
`REPLAY_FIELD_ERRORS`에 에피소드/필드별 max_abs와 first_mismatch_frame(0부터)을 출력한다.
shape/비유한 값 때문에 수치 비교가 불가능하면 max_abs는 null이다.

실제 vendored HDF5DatasetFileHandler → EpisodeData.get_next_state() 회귀 테스트를 추가했다.
CPU 테스트 10개 통과. 원본 demo_8을 이 로더로 읽고 저장 배열로 runtime 형태를 재현한 검사도
95프레임/18필드에서 통과했다. **이는 실제 물리 replay나 수치 재현 일치의 증거가 아니다.**
Docker/NVIDIA 접근 제한으로 실제 재실행 및 기존 프로세스 PID/종료코드는 확인하지 못했다.

`APP_CLOSE BEGIN` 뒤 셸로 돌아오는 것만으로 close() 정상 반환이나 종료코드 0을 확정할 수 없다.
`replay_checked.py`는 한 개의 replay 자식만 실행하고 OS에서 반환받은 종료코드를 출력한다.
기존 replay가 끝났는지 호스트에서 확인한 뒤 아래 명령을 사용한다. 다른 프로세스는 종료하지 않는다.

```bash
docker top cyclo_lab -eo pid,ppid,args
```

기존 replay가 남아 있으면 해당 터미널에서 Ctrl+C로 종료를 확인한 다음:

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_checked.py \
  --dataset_file /workspace/cyclo_lab/datasets/quest_tests/B001_test_001/dataset.hdf5 \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episode_names demo_8 --headless --enable_cameras --validate_states
replay_rc=$?
printf 'DOCKER_EXEC_EXIT=%s\n' "$replay_rc"
```

실제 수치 검증은 REPLAY_VALIDATION checked=95/mismatched=0/expected=95로 확인한다.
불일치가 있으면 REPLAY_FIELD_ERRORS를 확인한다. 프로세스 종료는 별도로
REPLAY_PROCESS_EXIT의 returncode와 DOCKER_EXEC_EXIT를 확인한다.
프로세스 코드 0만으로 수치 검증 성공을 판단하지 않는다. APP_CLOSE END가 없더라도 부모의
REPLAY_PROCESS_EXIT가 나오면 해당 자식은 종료된 것이다 (Kit 내부 정리 완료를 보증하는 것은 아님).

### 접시 속도 checkpoint와 검증 실패 종료코드

사용자 실기 결과: 로봇/토스터/빵의 비교 필드는 max_abs=0, 접시 pose 오차는 8.28e-5로 통과했지만
접시 velocity 최대 오차 .06838538로 95프레임 전체 상태 검증은 실패했다. 로봇 궤적 일치와 전체 상태
검증 성공은 구분한다. 임계값 .01 유지, 접시 필드 제외 없음.

root_velocity는 InteractiveScene.get_state → RigidObjectData.root_vel_w → root_com_vel_w이며
월드 좌표계 COM 속도 [vx,vy,vz,wx,wy,wz], 단위 [m/s,m/s,m/s,rad/s,rad/s,rad/s]이다.
인덱스 3,4는 각속도 x,y이다. 원본 demo_8 초기 속도는 모두 0이다.
첫 기록 상태의 각속도는 [0.112790756,-0.031493440,-0.012129337] rad/s이다.
이는 오차값이 아니라 기록된 실제 속도다.

기록 initial_state는 reset 이후, states[i]는 decimation=4인 env.step 종료 후 취득한다.
replay도 같은 종료 시점에서 비교한다. dt=.01, render_interval=4, control_dt=.04는 기록 metadata와
configure_replay로 대조된다. reset_to는 기록된 root_velocity를 PhysX와 내부 캐시에 쓰며,
이 태스크의 추가 복원 처리는 articulation의 drive velocity target만 제거하고 접시 속도를 덮어쓰지 않는다.

현재 접시 cfg는 solver position/velocity iterations=16/4, mass=.35 kg,
contact_offset=.001 m, rest_offset=0, max_depenetration_velocity=1 m/s이다.
spawn 재질은 static/dynamic friction=.8/.6, restitution=0, friction combine=max이다.
**기록에 전체 물리 cfg·접촉력·접촉 manifold/solver 내부 상태는 없다.** 현재 설정과 당시 설정이
완전히 같았는지, 접촉 캐시 차이가 원인인지 기록만으로 확정할 수 없다. 접촉 떨림/비결정성은 결론이 아니다.

새 replay는 PLATE_CONFIGURATION과 다음 PLATE_CHECKPOINT를 출력한다:
- after_reset_to_before_physics: 초기 기록 속도 vs 복원 후 cached/PhysX 속도, pose 및 센서 접촉력.
- after_first_physics_step: 첫 .01초 physics step 직후 PhysX 속도. 이 시점은 HDF5 substep 기준값이 없다.
- after_first_control_step: 4개 substep 뒤 cached/PhysX 속도 vs states[0], 성분별 절대오차.

센서의 reset 직후 접촉력은 stale일 수 있으며 solver 접촉 상태 그 자체가 아니다.
진단은 첫 env.step의 기존 sim.step 호출을 관찰만 하며 추가 physics step/상태 쓰기를 수행하지 않는다.
실제 GPU checkpoint는 접근 제한으로 미검증이다. 원본 파일과 물리/시나리오/action은 변경하지 않았다.

이전 wrapper는 자식 returncode만 전달했다. Python 예외 재전파 도중 finally의 앱 close가
프로세스를 0으로 끝내면 검증 실패가 덮일 수 있다. 사용자 로그가 이 실패 전달 문제를 확인해 준다.
Kit 내부의 정확한 native 종료 호출 지점은 현재 접근 환경에서 확인하지 못했다.
새 wrapper는 실행별 임시 디렉터리/nonce를 사용한 별도 판정 JSON을 검사한다.
worker는 앱 정리 전에 판정을 원자적으로 저장한다. 부모는 자식의 raw code가 0이어도
failed 판정/불일치/불완전 프레임은 1, 누락·손상·다른 실행 판정은 2로 종료한다.
REPLAY_PROCESS_EXIT는 raw code, REPLAY_SUPERVISOR.effective_exit_code는 Docker에 전달할 code다.

기존 replay_checked.py 명령을 그대로 사용한다. 기존 replay 종료 확인 전 중복 실행하지 않는다.
실패 사례의 기대 결과:
```
REPLAY_PROCESS_EXIT ... returncode=0
REPLAY_SUPERVISOR {"verdict": {"status": "failed", ...}, "effective_exit_code": 1}
DOCKER_EXEC_EXIT=1
```
CPU 테스트 14개 통과: 실제 로더, 엄격한 비교, 추가 step 없는 checkpoint hook,
실패 판정 후 실제 자식 os._exit(0)에도 부모 1 반환, 누락 판정 2 반환 등을 포함한다.
이는 접시의 실제 물리 replay가 일치하게 됐다는 증거가 아니다.

### Quest 없는 접시 대조시험: reset/render 이력 및 실제 설정 근거

추가 실기 증거: 복원 직후 기록/PhysX/cache 속도는 모두 0, 첫 .01초 physics step은
vz=-.0981/각속도 0, 첫 .04초 control step부터 기록 각속도와 차이가 생긴다.
따라서 초기 속도 미복원/캐시 불일치로 설명할 근거는 없고 물리 진행 후 경로를 조사한다.
로봇 궤적은 일치했지만 전체 상태 검증은 접시 속도로 실패한 상태를 유지한다.

소스상 확인:
- teleop: 생성 → reset(seed) → render-only WAITING → X → reset(seed) → 기록/물리 step.
- replay: 생성 → reset() → reset_to(초기 상태) → 물리 step. reset_to의 _reset_idx 이후
  기록 상태를 다시 쓰고 forward/render하며 articulation drive target 처리가 추가된다.
- Isaac Lab forward()는 articulation kinematics/fabric 갱신이고, render()는 playSimulations를
  끈 app.update 경로다. WAITING 코드에 sim.step은 없다. 실제 시간/호출 수는 TimelineProbe로 추가 기록한다.
- 기록 states는 4개 substep 후 record_post_step에서, replay는 env.step 반환 후 취득한다.
  이 태스크 이벤트는 reset 이벤트뿐이다. 뒤의 command/observation 갱신이 접시 물리 상태를 쓰는 경로는 찾지 못했다.
- demo_8 전의 실제 누적 접촉/solver 내부 이력은 HDF5에서 복원되지 않는다. 이 차이가 원인인지는 미확인이다.
- 기록 때 overview 카메라 1개가 추가되고 replay에는 기본 3개만 있다. 렌더 부하는 다르지만
  그 사실만으로 접시 물리 차이의 원인이라고 판단하지 않는다.

새 read-only 진단:
- record/replay 공통 audit.jsonl에 reset 전후, WAITING 전후, public sim.step/forward/render 호출 수,
  current_time/current_time_step_index(조회 가능 시), 접시 PhysX 속도를 기록한다.
- plate/table 실제 prim과 충돌 하위 prim, 적용된 physics material binding과 USD 속성을 읽는다.
  각 속성은 authored 여부 및 resolved 여부를 남긴다. USD schema fallback은 실제 PhysX 조회값과 구분한다.
- 기존 plate PhysX tensor view에서 masses/inertias/COM/material properties/contact/rest offsets 등
  조회 가능한 항목을 읽는다. 지원하지 않는 getter는 unavailable, 오류는 query_failed로 기록한다.
- 정적 table에 기존 rigid tensor view가 없으면 USD 근거만 수집하며, engine 값을 추정하지 않는다.
- cfg의 null은 unspecified라는 설정 의도일 뿐 0 또는 실제 PhysX 기본값으로 해석하지 않는다.

현재 세션에서 Docker 권한/NVIDIA 조회 제한 때문에 GPU 시험은 실행하지 못했다.
아래는 구현된 시험 절차이며 성공한 실험 결과가 아니다. 기존 실행을 먼저 확인하고 중복 실행하지 않는다.
원본 B001_test_001에는 쓰지 않으며 새 출력 폴더가 이미 존재하면 실행을 거부한다.

1. Quest/입력 서버 없이 기록 (기존 teleop의 초기 손목 목표 유지 제어, 열린 그리퍼/고정 lift).
   95프레임씩 두 번, 각 명시적 reset 전에 30회 render를 수행한다.
   외부 조작은 없으나 중력 보상/목표 유지용 IK action은 존재한다. 이는 모든 action=0 시험이 아니다.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/record_toast_noinput.py \
  --output /workspace/cyclo_lab/datasets/quest_tests/plate_noinput_001 \
  --operator operator_B --scenario_index 1 --seed 1 \
  --episodes 2 --frames 95 --wait-renders 30 --headless
```

기록 완료와 프로세스 종료를 확인한 뒤 진행한다. 이것은 demo_8의 이전 8개 시연 이력을 정확히 복제하지 않는다.
새 metadata에 experiment 종류/프레임/에피소드/render 횟수를 남긴다.

2. 새 기록만 action replay (두 에피소드의 비교 기준도 .01 그대로).

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_checked.py \
  --dataset_file /workspace/cyclo_lab/datasets/quest_tests/plate_noinput_001/dataset.hdf5 \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episode_names demo_0 demo_1 \
  --audit-dir /workspace/cyclo_lab/datasets/quest_tests/plate_noinput_001/replay_audit \
  --headless --enable_cameras --validate_states
replay_rc=$?
printf 'DOCKER_EXEC_EXIT=%s\n' "$replay_rc"
```

3. 기록/재생 설정 근거와 첫 substep/control step을 CPU에서 비교한다.

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/compare_plate_audits.py \
  datasets/quest_tests/plate_noinput_001/record_audit/audit.jsonl \
  datasets/quest_tests/plate_noinput_001/replay_audit/audit.jsonl --episode demo_0
```

같은 명령의 마지막을 `--episode demo_1`로 바꾸면 반복 reset 에피소드를 비교한다.
첫 단계부터 차이나면 reset/render/설정 이력을, 첫 substep은 같고 control step부터 다르면
substep 2–4 및 접촉 형성 경로를 추가 조사한다. property_differences가 비어도 unavailable 항목과
solver cache까지 같았다는 뜻은 아니다. 무조작 시험에서도 재현되면 Quest의 움직임 없이도 발생한다는
근거가 되지만, 그 자체로 접촉 비결정성을 증명하지는 않는다.

CPU: 기존 replay 회귀 14개 + evidence 비교/호출 수/None 구분 3개 통과, Python 문법 검사 통과.
실제 USD/PhysX 조회 API와 GPU 무조작 기록·재생은 실기 미검증이다.

### 새 VR 기록 B001_test_002: 공통 audit 연결 후 단일 에피소드 비교

사용자 실기에서 무조작 2개 에피소드는 checked=190/mismatched=0/expected=190,
effective_exit_code=0으로 통과했다. 이는 무조작 경로 통과이며 기존 VR demo_8의 접시 차이 원인 확정은 아니다.
teleop에는 audit가 없었으므로 기록 모드(--record-dir)에만 같은 TimelineProbe,
plate_configuration, plate_checkpoint, 첫 physics step hook을 연결했다.
원본 데이터, 물리, 제어, 허용오차와 HTTPS/입력/영상 보호 경로는 변경하지 않았다.
표시 페이지와 입력 서버를 이번 변경 때문에 재시작할 필요는 없다. 실행 중인 이전 teleop이 있다면
사용자가 그 teleop만 종료하고 새 실행기를 시작한다. GPU replay와 동시 실행하지 않는다.

새 폴더에서 실행 (이미 존재하면 덮어쓰지 않고 중단):

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open \
  --record-dir /workspace/cyclo_lab/datasets/quest_tests/B001_test_002 \
  --record-seconds 8
```

기존 HTTPS 서버와 Quest VR 입력 연결을 유지한다. 양손 유효 입력과 네 영상이 표시된 뒤,
정면을 보고 양쪽 squeeze를 놓는다. X를 한 번 눌렀다 놓고 EPISODE_STARTED를 확인한다.
한쪽 squeeze를 새로 눌러 작은 움직임을 수행한 뒤 놓는다. A로 저장하거나 8 wall seconds 자동 마감을 기다린다.
RECORD_SAVED demo_0와 WAITING 확인 후 **X를 다시 누르지 않고 Ctrl+C**로 종료한다.
최종 metadata의 episode_count=1, frames>0을 확인한다. 첫 진단 조회 완료 후 8초 타이머를 시작한다.
정확한 프레임 수는 실행 속도에 따라 달라지며 95로 고정되지 않는다. 그리퍼는 열린 상태 고정이다.

기록 audit는 B001_test_002/record_audit/audit.jsonl에 들어간다. 각 행의 episode=demo_0으로
WAITING 전후/reset 전후/첫 physics step/첫 control step/실제 설정 근거를 replay와 대응한다.
실제로 export된 에피소드 수를 이름에 사용하므로 빈 기록 시도가 저장 이름을 밀어내지 않는다.

teleop 종료 및 HDF5 닫힘 확인 후 이름으로 replay:

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_checked.py \
  --dataset_file /workspace/cyclo_lab/datasets/quest_tests/B001_test_002/dataset.hdf5 \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episode_names demo_0 \
  --audit-dir /workspace/cyclo_lab/datasets/quest_tests/B001_test_002/replay_audit \
  --headless --enable_cameras --validate_states
replay_rc=$?
printf 'DOCKER_EXEC_EXIT=%s\n' "$replay_rc"
```

replay_audit는 새 디렉터리여야 한다. 재실행 시 다른 audit 폴더 이름을 지정한다.
checked=expected=N, mismatched=0, effective_exit_code=0, DOCKER_EXEC_EXIT=0을 확인한다.
실패 시 REPLAY_FIELD_ERRORS와 양쪽 audit를 보존한다. 비교 명령:

```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/compare_plate_audits.py \
  datasets/quest_tests/B001_test_002/record_audit/audit.jsonl \
  datasets/quest_tests/B001_test_002/replay_audit/audit.jsonl --episode demo_0
```

이번 변경의 CPU 회귀 60개(Quest 43 + replay/audit 17) 및 문법 검사 통과.
실제 새 VR 기록/재생은 사용자가 수행하며 이 작업에서는 실행하지 않았다.

### 중앙 영상 하단 제어 상태 패널 (control-status-1)

중앙 영상·눈별 변환·저장된 캐스팅 배치는 그대로 유지하며, 기존 하단 안내 영역에
WAITING/RUNNING, 좌우 입력 유효성, 시뮬레이터의 실제 제어 판정, squeeze 눌림/값,
trigger 값을 표시한다. `SQ ON`은 버튼 상태일 뿐이다. `팔 조작 중`은 실행기의
`controller.states[side].reason == active` 판정이며 실제 관절 이동량을 측정한 표시는 아니다.
`기준 잡음`은 squeeze를 처음 눌러 기준을 잡은 프레임이다.
상단 INPUT 주황은 입력 무효, 어두운 초록은 입력 유효, 밝은 초록은 유효 입력에서
어느 버튼이든 pressed인 경우다. 상단 색상은 제어 활성 여부를 의미하지 않는다.

상태는 각 JPEG의 메타데이터를 통해 전달되며 약 5 Hz로 갱신된다. 영상이 만료되면
이전 활성 표시 대신 상태 확인 불가를 표시한다. START_BLOCKED에는 현재 미충족 조건을
나열한다. 영상 표시 확인 없음은 오래된 영상 외에 미표시/버전 불일치도 포함할 수 있다.
이 정보는 표시 전용이며 제어 판정이나 HDF5 관측에 입력되지 않는다.

적용: 현재 teleop 터미널에서 정상 종료한 후 입력 서버를 같은 옵션으로 재시작하고,
teleop도 기존 실행 옵션 그대로 한 번 재시작한다. 다른 작업은 종료하지 않는다.
Quest에서 VR을 나온 뒤 같은 HTTPS 주소를 새로고침하고 새 PIN으로 페어링한다.
CLIENT BUILD와 서버 BUILD 일치, Applied XR display의 revision `control-status-1`을 확인한다.
저장된 표시 설정은 초기화하지 않는다. VR 진입 후 X로 시작하기 전 WAITING과
양손 상태를 확인한다. GPU/Quest 양안 가독성과 캐스팅은 실기 확인이 필요하다.

### overview-status-2: 상태 패널과 양팔 재현 진단

2026-11-03 조사 당시 bridge는 서버 `preview-v3-4c75fc835c8d`, Quest 페이지
`preview-v3-bb6990bfcc4c / casting-fit-3`, `reload_required`를 보고했다.
즉 이전 페이지가 실행 중이었고 영상 확인은 버전 검사에서 차단됐다.
같은 조사 시점에는 왼손 meta-fixed-hand, 오른손 소스 없음이었다. 이 순간값은 과거
양손 컨트롤러 조작 때의 원인을 입증하지 않는다. 당시 증거는
`logs/quest_diagnostics/status_investigation/*_before.json`에 보존했다.

상태 패널은 이제 FRONT OVERVIEW 영상 내부 상단에 겹쳐 그린다. 영상 위치·배율은
변경하지 않는다. 메타데이터 없음/오래됨도 텍스트로 표시한다. 패널 첫 줄의 C/S는
client/server build이며, Applied XR display의 status_panel에는 실제 canvas 좌표와
rendered, metadata_received/fresh, input_seq가 남는다. 이전 절의 control-status-1은 구버전이다.

`--diagnostic-log NEW_PATH.jsonl`은 HDF5와 분리된 표시/제어 진단이다. WAITING은 약 5 Hz,
RUNNING은 매 제어 단계, 시작/종료 요청도 기록한다. 각 decision 행에는:
- Quest seq/session, source handedness/candidates/pose 판정/원시 buttons, 서버 정규화 결과
- 입력을 읽은 순간의 age와 실제 제어 판정 시점 age, visibility, client/server build
- Quest가 보고한 프레임 경과 시간(동기화된 절대 시각 아님), 서버 영상 guard, loop_gap/step_ms
- 시작 전후 lifecycle, 요청 버튼, 이전/현재 제어 reason, ready/anchor/basis, safety_epoch
- 물리 step 전 measured 위치, 목표 위치, home 거리/회전, 목표 추종 오차
가 함께 저장된다. 원시 진단 필드는 제어 입력으로 사용하지 않는다. home_distance가 0.05m에
이르는 것과 목표 추종 오차는 별도 현상이며, 그 값만으로 IK 실패를 단정하지 않는다.

적용은 기존 teleop과 입력 서버를 각각 해당 터미널에서 정상 종료·재시작한 뒤,
Quest VR을 종료하고 같은 HTTPS 주소를 **새로고침**해야 한다. 재진입만으로는 이전 JS가
교체되지 않는다. 필요하면 기존 Quest 탭을 닫고 주소를 다시 연다(사이트 데이터 삭제 불필요).
서버 재시작 후 새 PIN으로 페어링하고 build 일치를 먼저 확인한다.

짧은 재현(시연 저장 없음):
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
QUEST_RUN="arms_$(date +%Y%m%d_%H%M%S)"
mkdir -p "logs/quest_diagnostics/$QUEST_RUN"
set -o pipefail
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers \
  --diagnostic-log "/workspace/cyclo_lab/logs/quest_diagnostics/$QUEST_RUN/decisions.jsonl" \
  2>&1 | tee "logs/quest_diagnostics/$QUEST_RUN/teleop.log"
```
WAITING에서 양 컨트롤러를 들고 squeeze/trigger를 좌우 차례로 눌렀다 놓아 원시 값만 확인한다.
양쪽 squeeze를 모두 놓고 정면을 본 채 X를 눌러 시작한다. RUNNING과 양쪽 준비를 확인할 때까지
계속 놓고 있다가 왼쪽 squeeze를 누른 채 2~3cm 이동 후 놓는다. 오른쪽도 동일하게 시험한다.
각 단계 2~3초씩 유지한다. 팔 조작 중인데 움직임이 없으면 값을 더 크게 밀지 말고 그대로
2초 기다린 뒤 놓는다. A로 WAITING, 마지막 Ctrl+C로 정상 종료한다. 고정 5cm/15도와
원래 240초 episode timeout은 그대로다. HDF5를 생성하지 않으며 기존 기록을 수정하지 않는다.

### compact-status-3: 영상과 겹치지 않는 두 줄 상태

overview-status-2의 영상 내부 overlay를 제거했다. 기존 상단 진단 영역에 고정 24px 글꼴로
첫 줄은 WAITING/RUNNING, 좌우 실제 제어 상태, SQ/TR 원시 값(소수점 한 자리)을 표시한다.
둘째 줄은 시작을 막는 핵심 이유만 표시한다. 메타데이터 미수신/영상 만료도 최대 두 줄로 표시한다.
영상 크기·위치·종횡비와 저장된 캐스팅 중심·배율은 유지한다. 중앙 십자는 영상 가림을 피하려고
그리지 않으며, 선택된 모서리/바깥 테두리 진단은 유지한다.

build/revision, 지연, 전체 차단 사유와 원시 상태는 페이지의 접힌 **상세 진단**에서 확인한다.
VR을 종료한 뒤 펼치면 최근 VR 수신 상태를 볼 수 있다. 새 컨트롤러 버튼 매핑은 없다.
이번 변경은 hud.js/index.html과 표시 테스트·문서에 한정된다. 입력·제어·물리·기록 코드 변경은 없다.

적용: squeeze를 놓고 VR에서 나온 다음 입력 서버만 기존 명령으로 정상 재시작한다.
Quest 페이지를 새로고침하고 새 PIN으로 페어링 후 VR에 다시 들어간다. teleop 시뮬레이터 재시작은
필요 없다. 표시 설정 초기화도 필요 없다. 실제 양안 가독성/캐스팅 잘림은 Quest에서 확인해야 한다.

### head-wrists-4: HEAD + 양손목, 컨트롤러 연결 표시

Quest 기본 화면은 상단 큰 HEAD와 하단 동일 너비의 LEFT WRIST / RIGHT WRIST로 구성된다.
기존 960×936 합성 영상에서 완전한 300×300 카메라 타일을 표시 단계에서 분리해 그린다.
HEAD 원본은 정사각형이므로 넓은 상단 영역에 좌우 여백을 둔다. 영상 일부를 잘라 채우거나
늘리지 않는다. FRONT OVERVIEW는 VR 표시에서만 제외하며 센서·기록·전송 원본은 보존한다.
확대해도 기존 스트림보다 해상도가 높아지는 것은 아니다.

HEAD 위 상태 바는 좌우 연결 여부만 표시한다(초록/회색 + 텍스트). 실제 Touch Plus 소스가
현재 존재하고, 같은 source_id의 입력 패킷이 서버에서 수락되었으며, ACK와 그 패킷의
클라이언트 입력 시각이 모두 250ms 이내일 때 연결됨이다. 손 입력은 제외한다. pose 무효,
WAITING, squeeze 해제, 영상 미수신은 그 자체로 연결 끊김을 의미하지 않는다. 이 표시는
제어 활성 여부가 아니다. 제어·안전 판정은 기존 그대로이며 상세 진단과 로그에서 확인한다.

이번 변경은 HUD/페이지 표시 및 테스트·문서뿐이다. teleop 재시작은 불필요하다.
입력 서버는 시작 시 build를 고정하므로 재시작이 필요하다. 기존 서버 터미널에서 Ctrl+C로
정상 종료 후 아래를 실행한다(별도 cert/key를 사용했다면 기존 옵션을 유지).

```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/server.py \
  --host 192.168.10.116 --port 8765 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab/logs/quest_teleop
```

Quest에서 squeeze를 놓고 VR을 종료한다. 서버 재시작 후 기본 주소
`https://192.168.10.116:8765/`를 새로고침하고 새 PIN으로 Pair한다. 상세 진단에서 CLIENT BUILD와
서버 BUILD 및 revision head-wrists-4를 확인하고 VR에 재진입한다. 기존 탭에서 VR만 재진입하면
이미 메모리에 있는 JS가 유지되므로 반드시 페이지를 새로고침한다. 필요하면 탭을 닫고 기본
주소를 다시 연다. 긴 URL, 수동 query, 사이트 데이터 삭제, 표시 설정 초기화는 필요 없다.

실제 GET 핸들러의 `/`, build query가 붙은 세 JS 경로, `/version`, Cache-Control:no-store를
소켓 없는 CPU 테스트로 검증한다. 실행 환경의 소켓 생성 제한 때문에 새 HTTP/TLS 서버를
띄운 실통신 시험은 수행하지 않았다. 실제 Quest 가독성/캐스팅 범위는 실기 확인이 필요하다.

### head-wrists-5: 내부 여백 축소와 안쪽 연결 상태 바

조사 시 packet.xr_display는 head-wrists-4 / status_panel.rendered=true, y=52.48을 보고했다.
상태 바 생성은 확인됐지만 실제 캐스팅 crop 영역은 확인되지 않았다. 새 상태 바는
1024×1024 canvas의 x=108,y=96,w=808,h=40으로 내려 상단 여유를 둔다. 수신 이력이 없으면
회색 '확인 중', 수신 후 판단은 기존 연결 판정을 사용한다. 알려진 입력 만료는 연결 안 됨이다.

HEAD는 (272,144)에 480×480, 좌우 WRIST는 (108,648)/(588,648)에 각각 328×328이다.
이전 기본 배치의 약 462×462 / 257×257에서 확대했다. 제목은 HEAD 옆의 빈 공간 및
영상 사이의 24px 간격에 두고 영상에 겹치지 않는다. 하단에는 48px 여유가 있다.
전체 XR 배율·중심은 유지한다. 세 영상의 크기·간격은 이 고정 내부 배치를 사용하며
기존 Inner margin 저장값은 이 레이아웃에는 적용하지 않는다. 센서/원본/제어는 변경하지 않는다.

미리보기: `logs/quest_diagnostics/layout_preview_v5/preview.html`을 PC 브라우저로 연다.
현재 HUD 코드를 직접 사용하는 독립 HTML이며 카메라는 캡처 당시 프리뷰, 연결 상태는 예시다.
실제 Quest 광학/캐스팅 crop을 재현한 것은 아니다. sandbox 제한으로 Chrome 스크린샷 실행은
실패했으며 CPU 모의 렌더링과 HTML 구성만 검증했다.

입력 서버는 build 갱신을 위해 정상 재시작 필요, teleop은 재시작 불필요하다.
기본 HTTPS 주소에서 페이지 새로고침·새 PIN 페어링·VR 재진입 순서로 적용한다.

### native-preview-rec-6: 원본 크기 전송과 실제 REC

원본 HEAD/LEFT WRIST/RIGHT WRIST는 런타임 stats와 B001_test_002 HDF5에서 모두 244×244 RGB다.
기존 경로는 244→300(Pillow RGB 기본 BICUBIC)→960×936 합성 JPEG Q75(실측 4:2:0)→
Quest 타일 300→HEAD480/WRIST328→1024 HUD 텍스처→눈별 viewport다. 텍스트는 HUD에 직접
그려져 JPEG를 거치지 않는다. 저장된 .5 배율과 1680×1760 viewport에서는 HUD 1024가
눈별 약840px로 표시되므로 HEAD는 약394px, 손목은 약269px다. Meta 재인코딩/crop은 미측정이다.

새 경로는 244px 전체 타일을 리사이즈 없이 768×256 atlas에 넣고 JPEG Q90/4:4:4로 전송한다.
원본 타일 영역은 (6,6)/(262,6)/(518,6), 모두 244×244. Quest에서는 기존과 동일한 480/328px에
한 번 확대한다. 샤프닝 없음. 센서·FOV·학습 관측·HDF5는 그대로다. overview 센서와 수집도
유지하지만 표시하지 않는 overview 픽셀은 새 프리뷰에 전송하지 않는다. 기존 960×936 프리뷰도
클라이언트가 읽을 수 있으나 새 선명도 개선과 실제 REC는 teleop 재시작이 필요하다.

REC는 DiagnosticRecorder.active만 읽는다(start에서 true, export/finish에서 false).
RUNNING/record-dir 여부로 추정하지 않는다. 상태 프레임 만료 또는 recording 필드 없는
구버전 producer는 '확인 중'이다. 세 영상과 연결 표시의 위치/크기는 유지한다.

같은 저장 원본 48프레임을 읽기 전용으로 비교한 결과는
`logs/quest_diagnostics/quality_native_v6/report.json`과 `comparison.html`에 있다.
표시 크기로 bilinear 확대하는 CPU 모델 PSNR 평균은 HEAD 42.12→47.96dB,
LEFT 46.15→54.62dB, RIGHT 46.21→54.57dB. 실제 Quest 광학 측정은 아니다.
CPU 합성+인코딩 중앙값은 기존10.37ms/새0.45ms, 새 전송량 중앙값21,139bytes였다.
이 비교의 기존 overview는 검정 대체이므로 기존 전체 전송량/시간은 실시간 동등 비교가 아니다.
변경 전 실제 bridge 3초 샘플에서는 새프레임10개, 프레임 간격 중앙값316ms, step150ms,
전송량65,506bytes였다(live_before.json). 변경 후 실제 GPU/Quest 속도·지연은 미검증이다.
`preview.json.timings.encoding`에 encode_ms/bytes/quality, Quest preview_status에
bytes/decode_ms/fetch_decode_ms/frame_age_ms가 남아 적용 후 비교할 수 있다. 보호 timeout은 그대로다.

244×244 자체의 세부정보 한계는 남는다. 더 높은 원본이 필요하면 학습 카메라를 바꾸는 대신
별도 관찰 전용 고해상도 카메라를 검토할 수 있으나, GPU 비용과 FOV/pose 일치 검증이 필요하며
이번에는 추가하지 않았다.

적용: 현재 teleop 정상 종료 → 입력 서버 정상 재시작 → 아래 teleop 실행 → Quest 페이지
새로고침/새 PIN 페어링/VR 진입. 기록하지 않는 화질 확인 명령:
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/server.py \
  --host 192.168.10.116 --port 8765 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab/logs/quest_teleop
```
별도 터미널:
```bash
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers
```
REC 실기 확인이 필요한 경우 위 teleop을 정상 종료한 뒤 아래를 대신 실행한다(중복 실행 금지).
```bash
QUEST_REC="B001_rec_status_$(date +%Y%m%d_%H%M%S)"
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers \
  --record-dir "/workspace/cyclo_lab/datasets/quest_tests/$QUEST_REC" \
  --record-seconds 8
```
WAITING NO REC → 양 squeeze 해제 후 X → 실제 기록 시작 후 빨간 REC → A 또는 8초 종료 후
NO REC. 새 테스트 폴더에만 저장하며 기존 기록은 유지한다. 실제 REC/Quest 확인은 사용자가 수행한다.

### practice-timing-7: 제한 있는 연습 범위와 양쪽 그리퍼 테스트 기록

이번 기능은 실제 토스트 연습을 위한 코드 준비 단계다. Quest 양팔/그리퍼 접촉, 확장 범위의
IK 도달성, 새 VR 에피소드의 물리 replay는 아직 미검증이다. CPU 검증을 GPU 실기 검증으로
해석하면 안 된다. 기존 시나리오·physics dt .01/decimation4/control dt .04/render_interval4,
학습/기록 카메라 해상도·FOV·관측과 15D action 형식은 유지한다.

조사 시 최신 `B001_rec_status_20261103_194138/dataset.hdf5`는 writer lock이 잡혀 있었다.
원본 lock을 우회하거나 파일을 수정하지 않고, 크기/mtime이 복사 전후 안정적인 별도 스냅샷을
읽었다. `logs/quest_diagnostics/practice_audit/latest_record_report.json` 기준 demo_0..8:
50/51/6/50/50/50/50/50/49 = 406프레임, demo_2만 manual_stop, 나머지 short_test_duration.
앱 exit_reason은 없고 sidecar는 아직 초기 값이므로 앱 정상 종료/종료코드는 확인되지 않았다.
HDF5의 에피소드 export와 프로그램 종료는 별개다. 원본을 최종 확인하려면 사용자 터미널에서
정상 종료한 뒤 읽어야 한다. 기존 기록의 양 그리퍼 명령은 모두 +1(열림)이었다.

8초 제한은 time.monotonic 기반 wall time이다. 이 실행의 8초 에피소드는 약 49~51 control
steps = 1.96~2.04 simulation seconds, 대략 0.24배속이었다. 새 --record-seconds 0은 A/원래
환경 종료 조건까지 기록한다. 기본값8은 보존한다. 원래 240 simulation-second timeout도 유지한다.

성능 표본은 WAITING과 RUNNING을 구분한다. 실시간 WAITING 8초 표본은 40 preview frames,
median 생성간격200ms, render-only step17.3ms, encode0.91ms, Quest fetch+decode31.9ms,
decode2.7ms, frame age206ms였다. 기존 RUNNING 기록의 0.24배속과 혼동하지 않는다.
기존 로그만으로 physics/render/관측의 분담이나 Quest photon latency는 알 수 없다.
새 PerformanceProbe는 추가 physics/render/GPU synchronization 없이 원래 호출을 한 번씩
위임하고 wall time을 측정한다. 렌더/physics/관측은 GPU 비동기 처리 때문에 inclusive CPU
시간이며 합산 GPU profile이 아니다. 수신→process_action/첫 apply_action/첫 physics 진입을
같은 host monotonic clock으로 기록한다. Quest→서버 단방향 지연은 시계 동기화가 없어 미측정이다.

표시 개선: producer 상한을 --preview-hz 15(1~25 조절)로, 브라우저 poll을100ms로 변경했다.
실제 속도는 env.step/네트워크에 제한된다. 더 느린 step에서는 15FPS를 보장하지 않는다.
보이지 않는 overview CPU 읽기/복사는 생략하지만 센서와 설정은 보존한다. WAITING 렌더는
프리뷰가 필요한 때만 실행한다. RUNNING의 physics/render/관측 계산은 생략하지 않는다.
현재 스냅샷은 pose를 읽은 뒤 제어 직전에 다시 읽어 오래된 reset 전 입력을 쓰지 않는다.
기존250ms 입력/1s 영상/250ms loop-gap 차단과 source 교체 재해제 요구는 유지한다.

연습 프리셋(`--control-profile practice`):
- 초기 손목 기준 구형 이동 범위 .55m / 회전120도, 위치 배율 .5 / 회전 배율 .75.
- 고정 workspace(로봇 root 좌표) x=[.1,.85], y=[-.85,.85], z=[1.02,1.8]m.
- 목표는 측정 손목보다 최대4cm/15도만 앞서도록 추가 제한. 기존8cm 추종 오류 종료도 유지.
- action 보정 속도 .10m/simulation-second, .8rad/simulation-second. wall 속도는 sim 배속에 비례.
- --max-translation(.01~.75), --max-rotation-deg(1~180), --position-scale(.05~1),
  --rotation-scale(.05~1.5), --linear-speed(.01~.15), --angular-speed(.05~1.5)로 조절 가능.
- 기본 diagnostic 프리셋은 기존5cm/15도/.25/.5와 속도를 유지한다. 무제한 옵션은 없다.

B001 초기 오른손목은 기록 obs에서 (.36094,-.39541,1.44191)m, 빵 중심은
약(.45,-.46~-.31,1.0932)m이다. 손목~중심 거리 .360~.369m, 왼손 미러 기준은 .795~.929m다.
이 수치는 grasp offset이나 IK 충돌 해법을 증명하지 않는다. .55m 범위는 오른손 접근과 중앙
handover를 위한 범위이며 왼손이 선반의 빵까지 직접 닿는 범위가 아니다. 오른손으로 접근·집기,
중앙에서 왼손 인계 후 토스터 접근을 연습한다. WORKSPACE_RESET 로그는 매 reset의 실제
양손목·빵 중심 root 좌표와 거리를 남긴다. 목표 제한 도달과 IK 추종 오차는 diagnostic log로 구분한다.

기록의 gripper 금지는 최초 진단용 validate_recording_args 제한이었으며 물리/action 제약이
아니었다. 이를 제거했다(--preview-only 기록은 여전히 금지). 현재 trigger0..1은 gripper
+1..-1로, action index12/13에 독립 저장된다. CoupledGripperPositionAction은 +1→joint0,
-1→joint1.10의 연속 개방량을 사용한다. squeeze 활성 중에만 변경되고 해제 시 마지막 목표를 유지한다.
실제 DiagnosticRecorder + vendored HDF5 writer/loader + get_next_action + 실제 task의
그리퍼 분리/처리 메서드를 사용한 21프레임 CPU 시험이 통과했다. 결과는
`logs/quest_diagnostics/practice_audit/gripper_contract/`이며 synthetic CPU fixture다.
물리 replay용 데이터가 아니므로 실제 demo로 제출하지 않는다. 새 실제 데이터는 기존과 같이
quest_tests의 diagnostic 데이터이며 success=False, task_success_observed를 별도로 보존한다.

적용: 기존 teleop을 해당 터미널 Ctrl+C로 정상 종료하고 종료코드를 확인한다. 다른 작업은 종료하지
않는다. 입력 서버도 기존 터미널에서 정상 종료 후 아래를 실행한다. 별도 cert/key가 있으면 유지한다.
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/server.py \
  --host 192.168.10.116 --port 8765 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab/logs/quest_teleop
```
무기록 연습(별도 터미널, 이전 teleop 종료 후 하나만 실행):
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
QUEST_RUN="practice_$(date +%Y%m%d_%H%M%S)"
mkdir -p "logs/quest_diagnostics/$QUEST_RUN"
set -o pipefail
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers --control-profile practice --preview-hz 15 \
  --diagnostic-log "/workspace/cyclo_lab/logs/quest_diagnostics/$QUEST_RUN/decisions.jsonl" \
  2>&1 | tee "logs/quest_diagnostics/$QUEST_RUN/teleop.log"
QUEST_EXIT=${PIPESTATUS[0]}
echo "DOCKER_EXEC_EXIT=$QUEST_EXIT"
```
실제 양팔/그리퍼 테스트 기록(위 연습 종료 후 대신 실행; 새 디렉터리):
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
QUEST_RECORD="B001_practice_$(date +%Y%m%d_%H%M%S)"
mkdir -p "logs/quest_diagnostics/$QUEST_RECORD"
set -o pipefail
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers --control-profile practice --preview-hz 15 \
  --record-dir "/workspace/cyclo_lab/datasets/quest_tests/$QUEST_RECORD" --record-seconds 0 \
  --diagnostic-log "/workspace/cyclo_lab/logs/quest_diagnostics/$QUEST_RECORD/decisions.jsonl" \
  2>&1 | tee "logs/quest_diagnostics/$QUEST_RECORD/teleop.log"
QUEST_EXIT=${PIPESTATUS[0]}
echo "DOCKER_EXEC_EXIT=$QUEST_EXIT"
```
Quest 기본 HTTPS 주소 새로고침→새 PIN→VR. 양 squeeze를 놓고 정면을 본 상태에서 X.
오른쪽 squeeze를 누르고 작은 이동부터 확인한다. trigger 해제=열기, 누름=닫기(squeeze 활성 중).
입력/영상 손실 후 양 squeeze를 놓고 재입력한다. A는 물리 진행 중지·WAITING(기록 중이면 저장).
X는 같은 시나리오 reset 후 새 에피소드이며 resume이 아니다. 첫 새 기록은 5~10초 동작 후 A로
마감해 action replay를 먼저 검증한다. 실제 잡기/인계 성공은 별도 실기 확인이다.

RUNNING 중 별도 PC 터미널에서 read-only 측정:
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/sample_performance.py \
  --bridge-dir logs/quest_teleop --seconds 15 \
  --output "logs/quest_diagnostics/performance_$(date +%Y%m%d_%H%M%S).json"
```
기록한 teleop을 정상 종료한 뒤 같은 터미널의 QUEST_RECORD 변수로 replay한다.
```bash
set -o pipefail
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_checked.py \
  --dataset_file "/workspace/cyclo_lab/datasets/quest_tests/$QUEST_RECORD/dataset.hdf5" \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episode_names demo_0 --validate_states --headless --enable_cameras \
  2>&1 | tee "logs/quest_diagnostics/$QUEST_RECORD/replay.log"
QUEST_REPLAY_EXIT=${PIPESTATUS[0]}
echo "DOCKER_EXEC_EXIT=$QUEST_REPLAY_EXIT"
```
EOF の代わりに終了コード0・checked=expected・mismatched=0を確認する。許容差0.01や
接皿フィールド除外は変更していない。実機GPUでこの新記録を再生する検証は未実施。

### practice-response-8: 선택 가능한 제한과 해제 시 목표 취소

이 절은 이전 practice 프리셋 설명을 대체한다. HEAD/WRIST/연결/REC 배치는 그대로다.
원본 scenario/physics dt/관절·actuator/IK/camera/학습 관측/HDF5 형식은 변경하지 않았다.
GPU 접근은 현재 도구의 Docker socket 권한 거부로 불가했다. 기존 GPU 실행 로그는 분석했지만
새 코드의 GPU 응답/무접촉 개도/실기 기록/replay는 수행하지 못했다. CPU 검증을 대체 증거로
쓰지 않는다. 다른 프로젝트 작업이나 실행 중인 서버/teleop은 종료하지 않았다.

`logs/quest_diagnostics/practice_20261103_202046/decisions.jsonl` RUNNING만 분석:
510단계, 유효 인접 구간 simulation20.24s/wall85.23s=0.23747배속. 중앙값 step164.22ms,
physics_call61.47ms, apply_action30.62ms, render_call22.06ms, observations9.65ms,
scene_update10.32ms, process_action4.83ms. 비동기 GPU 비용이 뒤 호출에 나타날 수 있는
inclusive CPU wall timing이며 GPU 전용 프로파일이 아니다. 무기록 실행이므로 실제 기록 비용은
미측정이다(이번 버전은 recorder pre/post/export hook 시간도 추가 계측).

수신→process27.71ms/첫 apply33.34ms/첫 physics 진입43.81ms. preview167.68ms,
readback0.72ms, encode0.87ms, Quest fetch+decode36.4ms(그중decode2.7ms), frame age157.67ms.
Quest clock과 host clock은 동기화하지 않았으므로 단방향 네트워크/입력→광자 지연은 알 수 없다.
이 로그의 active 제어 샘플은0이었다. 유효 source의 squeeze는 모두0, 대부분 나머지는
hand source 제외/기준 대기였다. 따라서 속도 포화율·active 추종오차·그리퍼 실제 응답을
계산할 자료가 없다. 이것은 사용자가 다른 시점에 조작하지 않았다는 뜻이 아니다.
결과는 `logs/quest_diagnostics/response_v8/before.json`에 보존했다.

기존 speed cap은 목표 생성 속도가 아니라 action()에서 `오차를 speed*simulation_dt로 절단`
하는 보정 제한이었다. .10m/sim-second × .237배속 ≈ .0237m/wall-second다.
기존 practice는 squeeze 해제 후에도 남은 목표를 action()으로 계속 추종했다.
새 practice는 release/중간 squeeze/무효입력/영상만료/loop-gap/source교체 시 목표를 현재 측정
자세로 갱신하고 팔 Cartesian action을0으로 보낸다. 실제 물리 관성이나 기존 null-space 자세
보정까지 순간 정지시킨다는 뜻은 아니다. 재clutch 첫 프레임도 측정 자세 기준으로 anchor를
잡아 과거 목표를 되살리지 않는다. diagnostic의 기존 목표 유지 동작은 보존했다.

새 옵션(새 제한 해제 옵션은 practice에서만 허용; diagnostic 사용 시 오류):
- --no-home-limits: 초기 기준 .55m/120도 한계만 제거. --max-translation/--max-rotation-deg와 중복 금지.
- --no-speed-limits: teleop 선속도/각속도 action 보정 cap 제거. --linear-speed/--angular-speed와 중복 금지.
- --workspace off: 임의의 table box를 사용하지 않음. 기본table은 이전 box 유지.
- --no-target-lead: 병진/회전 선행 cap 제거. 첫 실기 비교에서는 권장하지 않으며 선행값 옵션과 중복 금지.
- --max-target-lead .01~.5m(기본 .12), --max-angular-lead-deg 1~120(기본45).
- --position-scale .05~1(기본 practice1/diagnostic.25), --rotation-scale .05~1.5(기본 practice1/diagnostic.5).
- 유한 home 옵션 .01~.75m / 1~180도; 유한 speed 옵션 .01~.15m/sim-second / .05~1.5rad/sim-second.
- --tracking-stall-seconds .5~10 wall seconds, 기본2.

practice의 추종오차는 >8cm 또는 >30도여도 즉시 종료하지 않는다. 목표가 약2cm/5도 이내로
유지되고, 오차 결합척도(distance + .1*angle)가2mm 이상 줄어들지 않는 상태가 지정 wall time과
최소5제어샘플 동안 지속되면 해당 에피소드를 마감하고 WAITING으로 전환한다. 계속 진전하는
정상 지연과 구분한다. >.6m 또는 >170도는 큰 불연속으로 해당 목표를 IK에 보내기 전에 중지한다.
A는 즉시 WAITING, 새 X는 reset이다. 250ms 입력/loop-gap, 영상 freshness, Touch Plus 판정,
재연결 squeeze 재해제, 관절·구동 한계, IK는 유지한다. 유효한 목표가 무한정 도달 가능하다는 뜻이 아니다.

그리퍼는 기존 CoupledGripperPositionAction으로 연속 제어다. trigger 0/.25/.5/.75/1 →
action +1/+.5/0/-.5/-1 → 각 linkage joint 목표0/.275/.55/.825/1.10rad.
master 설정: 속도2.2rad/s, effort30, stiffness100, damping4.
slave 설정: effort20, task에서 stiffness100/damping4로 설정. slave velocity_limit_sim=None을
무한대나 특정 PhysX 속도로 해석하지 않는다. 시작 로그 GRIPPER_CONFIGURATION에 runtime
joint velocity limit buffer와 설정을 구분해 남긴다. 물리 속도/접촉은 그대로다.
squeeze 해제 중 마지막 gripper 목표 유지. practice 재clutch에서는 현재 trigger를 첫 프레임에
반영한다(이전 버전은 첫 anchor 다음 프레임). action 의미/학습·replay index는 바꾸지 않는다.

진단에는 최대2Hz로 양쪽8관절 실제각/목표각/속도를 한 번에 읽는다. 매 프레임 새 GPU 동기화를
추가하지 않는다. 이는 관절 기반 개도이며 mm 단위 손가락 간격 측정이 아니다. trace의 기존
측정 손목과 새 measured_sample_monotonic, target_generated_monotonic, action, limits_hit로
명령/측정 시점을 비교할 수 있다. recorder hook 시간도 추가했다. CPU action/기록/로더
21프레임 왕복은 `logs/quest_diagnostics/response_v8/gripper_contract/`에 있으며 synthetic fixture다.
GPU demonstration으로 제출하지 않는다.

적용 시 기존 teleop·서버를 각각 해당 터미널에서 Ctrl+C로 정상 종료한다. 아래 GPU 명령은
동시에 실행하지 않는다. 다른 프로젝트는 유지한다.

입력 서버:
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
python3 scripts/quest_diagnostic/server.py \
  --host 192.168.10.116 --port 8765 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab/logs/quest_teleop
```
무기록 연습:
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
QUEST_RUN="response_$(date +%Y%m%d_%H%M%S)"
mkdir -p "logs/quest_diagnostics/$QUEST_RUN"
set -o pipefail
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers --control-profile practice \
  --position-scale 1 --rotation-scale 1 --no-home-limits --no-speed-limits --workspace off \
  --max-target-lead 0.12 --max-angular-lead-deg 45 --tracking-stall-seconds 2 --preview-hz 15 \
  --diagnostic-log "/workspace/cyclo_lab/logs/quest_diagnostics/$QUEST_RUN/decisions.jsonl" \
  2>&1 | tee "logs/quest_diagnostics/$QUEST_RUN/teleop.log"
QUEST_EXIT=${PIPESTATUS[0]}
echo "DOCKER_EXEC_EXIT=$QUEST_EXIT"
```
짧은 테스트 기록(위 실행 종료 후 새 경로):
```bash
cd /home/mj/nrf_humanoid/cyclo_lab
QUEST_RECORD="B001_response_$(date +%Y%m%d_%H%M%S)"
mkdir -p "logs/quest_diagnostics/$QUEST_RECORD"
set -o pipefail
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers --control-profile practice \
  --position-scale 1 --rotation-scale 1 --no-home-limits --no-speed-limits --workspace off \
  --max-target-lead 0.12 --max-angular-lead-deg 45 --tracking-stall-seconds 2 --preview-hz 15 \
  --record-dir "/workspace/cyclo_lab/datasets/quest_tests/$QUEST_RECORD" --record-seconds 0 \
  --diagnostic-log "/workspace/cyclo_lab/logs/quest_diagnostics/$QUEST_RECORD/decisions.jsonl" \
  2>&1 | tee "logs/quest_diagnostics/$QUEST_RECORD/teleop.log"
QUEST_EXIT=${PIPESTATUS[0]}
echo "DOCKER_EXEC_EXIT=$QUEST_EXIT"
```
Quest 기본주소 https://192.168.10.116:8765/ 새로고침→새 PIN→VR. 양쪽 grip(squeeze)을 놓고
정면에서 X. 한쪽씩 squeeze를 누른 채2~3cm 이동→놓고2초→다른 위치에서 재clutch→양쪽 반복.
오류가 없을 때10~20cm 이동으로 확장. 물체와 접촉하지 않는 위치에서 trigger를 단계적으로
눌러 중간값을2초 유지하고 squeeze 해제/재입력도 확인. 정확한5개 raw값 시험은 CPU만 통과했다.
VR을 잠시 종료해 입력 만료 후 복구 시 재해제가 필요한지 확인. A로 종료·저장, Ctrl+C로 앱 종료.
중간 목표가 남아 뒤늦게 이동하는지와 실제 개도는 이 실기 결과로 확인해야 한다.

실행이 끝난 trace 분석(무기록이면 QUEST_RECORD 대신 QUEST_RUN):
```bash
python3 scripts/quest_diagnostic/analyze_response.py \
  --log "logs/quest_diagnostics/$QUEST_RECORD/decisions.jsonl" \
  --output "logs/quest_diagnostics/$QUEST_RECORD/analysis.json"
```
teleop/HDF5 종료 후 실제 action replay:
```bash
set -o pipefail
docker exec -it -w /workspace/cyclo_lab cyclo_lab /isaac-sim/python.sh \
  scripts/imitation_learning/isaaclab_recorder/replay_checked.py \
  --dataset_file "/workspace/cyclo_lab/datasets/quest_tests/$QUEST_RECORD/dataset.hdf5" \
  --task Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2 \
  --num_envs 1 --select_episode_names demo_0 --headless --enable_cameras --validate_states \
  2>&1 | tee "logs/quest_diagnostics/$QUEST_RECORD/replay.log"
QUEST_REPLAY_EXIT=${PIPESTATUS[0]}
echo "DOCKER_EXEC_EXIT=$QUEST_REPLAY_EXIT"
```
실측 before/after 비교와 checked=expected/mismatched=0/종료코드0은 아직 충족되지 않았다.
