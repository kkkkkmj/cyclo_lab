> 현재 실행 진입점: [README_TOAST_QUEST.md](README_TOAST_QUEST.md). 아래 단계별 작업·측정 기록의 과거 값은 당시 설정입니다. 현재 v2 상승 목표/상한은 +35 mm이며 하한은 -45 mm입니다. 기록 속 PC IP·호스트 절대 경로·컨테이너 이름은 실행 환경에 맞게 설정해야 합니다. 최신 문서의 변수 기반 명령을 사용하세요.

현재 gain은 이후 변경으로 v2 좌우 slave 100.0/4.0이다.
이 문서의 2.0/0.5는 거치대 교체 당시 보존한 값이다.
현재 설정은 [README_GRIPPER_GAINS.md](README_GRIPPER_GAINS.md) 참조.

# bread_slot 거치대 교체 기록 — 2026-11-08

수정 저장소는 `/home/mj/nrf_humanoid/cyclo_lab_mj`만이다. 별도 원본
`/home/mj/nrf_humanoid/cyclo_lab`에는 쓰기 작업을 하지 않았다. 실행 중인 학습/시뮬레이션을
종료·재시작하지 않았으며 commit/push도 하지 않았다.

## 교체 대상과 asset

- 교체 대상: 토스트 전 빵 네 장을 보관하는 `scene.bread_shelf`.
- scene prim: `{ENV_REGEX_NS}/BreadShelf` (단일 환경 `/World/envs/env_0/BreadShelf`).
- 기존: `source/cyclo_lab/data/objects/robodojo_make_toast/bread_shelf/object.usdz`.
- 새 원본: `source/cyclo_lab/data/objects/bread_slot/bread_slot.usdz`.
- 실제 로드: `source/cyclo_lab/data/objects/bread_slot/rack.usda`.
- 새 충돌 prim: `/World/envs/env_0/BreadShelf/Model/Body1`.
- `/home/mj/Downloads/bread_slot.usdz`에서 복사했으며 원본과 SHA256이 동일하다:
  `338eb23d759224c0686857b3e793070b2bf03f9c7fe25f872a3c598bd67330d8`.
- 기존 asset 파일은 보존하지만 새 scene에서 참조하지 않는다. 새 wrapper의 충돌 Mesh는
  정확히 하나다. 토스터 본체·레버·캐리지 asset과 동작 코드는 변경하지 않았다.

## 단위, 형상, 배치, 충돌

로컬 파일에서 내부 `bread_slot.usdc`, `/bread_slot/Body1` 단일 Mesh와 재질,
`metersPerUnit=0.001`, `upAxis=Y`, 관절/강체/충돌 API 없음이 확인되었다.
Body1에는 **내부 10배 transform**이 있다. 이것까지 반영한 실제 크기는
**230 × 130 × 45 mm**이다. wrapper에서 mm→m 0.001배를 한 번 적용하고
X축 +90°로 Y-up→Z-up을 변환했다. 추가 형상 확대·비균일 변형은 없다.
기존 양팔 환경의 `(2,1,1)` 거치대 확대를 `(1,1,1)`로 바꿨다. 빵 크기는 그대로다.

기본 양팔 scene의 기준점 `(0.45,-0.25,1.0382)`와 yaw −90°를 유지했다.
wrapper 안에서 Z를 `−0.044148661134795 m` 이동하여 바닥을 기존 manifest의 실제
추출 상판 높이 `0.994051338865205 m`에 맞췄다. 상단은 약 `1.039051339 m`이다.
시나리오별 XY·yaw·기준점은 기존과 같으며, 새 빵 자세도 동일한 변환을 따른다.

네 홈 중심 X는 거치대 좌표에서 `+90,+30,−30,−90 mm`이다. 홈 폭은 약 25 mm,
평평한 내부 바닥은 모델 바닥에서 15 mm 위, 상단은 45 mm 위이다.
양끝은 둥근 턱으로 이어진다. 고정 Mesh에 `PhysicsCollisionAPI` 및
`PhysicsMeshCollisionAPI(approximation="none")`를 적용했다. 강체 API는 없다.
따라서 단일 convex hull로 홈을 메우지 않고 원래의 삼각형 표면을 충돌에 사용한다.
scene의 기존 contact_offset=1 mm, rest_offset=0 설정을 유지했다.
실제 PhysX cooking 결과는 실행 제한 때문에 확인하지 못했다.

## 빵 초기 배치와 성공 판정

`bread_0,1`은 작업용, `bread_2,3`은 성공 시 거치대에 남아야 하는 예비 빵이다.
빵의 기존 convex collider 및 크기 약 116.95 × 116.06 × 11.80 mm를 유지했다.
빵 폭 때문에 새 홈의 평평한 바닥까지 내려가지 않고 **둥근 양끝 턱에 지지되는 배치**다.
삼각형-볼록 다면체 clipping으로 초기 관통이 없고 1 mm 아래에서 접촉함을 확인했다.
초기 틈은 접촉 여유 약 0.3 mm를 의도한 것이며 중력 정착 후의 실제 자세는 미검증이다.

기본 양팔 환경의 빵 root 위치(m), 순서는 bread_0부터 bread_3:

| 항목 | 이전 | 이후 |
|---|---|---|
| 공통 X | 0.443000 | 0.450250 |
| Y | −0.320, −0.270, −0.220, −0.172 | −0.334392, −0.274392, −0.214392, −0.154392 |
| 공통 Z | 1.093200 | 1.082551 |
| quaternion wxyz | 약 (0.5,0.5,0.5,−0.5) | 동일 |

새 shelf-local 빵 root offsets는
`(홈 중심 X −0.005607555, +0.000249905, +0.044351338865205)` m이다.
이는 비대칭인 빵 root와 실제 두께 중심을 보정한다. 빵은 거치대 위로 약 102 mm 노출되고,
이웃 빵 사이의 명목 두께 간격은 약 48 mm이다. 이는 형상 치수이며 로봇 집기 검증은 아니다.

예비 빵 판정은 기존 shelf-local `|X|<170 mm, |Y|<60 mm, 15<Z<160 mm`와
기립 조건에서, **각자의 새 홈 초기 root 대비 X±5 mm, Y±3 mm, Z±6 mm** 및
기존 기립 조건 + 홈 방향과 빵 두께축 정렬 조건(`|R[0,2]|>.94`)으로 변경했다.
조건을 삭제하거나 허용 범위를 넓히지 않았다. 토스트 완료·접시·팔·그리퍼 등
거치대와 무관한 성공 조건은 수정하지 않았다. 동적 정착 결과에 대한 이 범위의
적합성은 PhysX smoke에서 추가 확인해야 한다.

## 100개 시나리오와 reset

기존 `scenario_delivery/manifest.json`, `assignments.csv`는 변경하지 않았다.
`manifest_bread_slot.json`을 파생 생성하여 새 기본 manifest로 연결했다.
100개 ID·순서·A/B 각 50개 배정, 토스터·접시·거치대의 position/quaternion은 같다.
바뀐 것은 거치대 scale과 네 빵의 위치/자세, 관련 기록 메타데이터다.
이전 거치대 기준 검증 필드는 `legacy_rack_evidence`로 분리하여 새 검증처럼 표시하지 않는다.
이전 기록의 manifest는 당시 asset 형상과 함께 재생해야 하며 새 형상으로 동일 재생이 보장되지 않는다.

양팔 reset은 기존 default_root_state 복원 방식 그대로다. 단팔 기본 task의 빵 Y±8 mm
랜덤 이동은 새 홈 끝벽 관통을 유발할 수 있어 제거하고 설정된 초기 자세를 복원한다.
CPU fake scene I/O 테스트에서 실제 reset/predicate 함수 본문을 실행해 100개 시나리오,
반복 reset, 환경 origin 변환, 정상 예비 빵 수락 및 들어올림/홈 이탈/눕힘 거부를 검사했다.

## 변경 파일

아래 config 파일 경로의 공통 prefix는
`source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/`이다.

| 파일 | 이유 |
|---|---|
| assets.py | 새 asset 경로 및 실제 홈에 맞춘 BREAD_OFFSETS |
| env_cfg.py | 고정 삼각형 충돌체에서 불필요한 rigid_props 제거 |
| bimanual_env_cfg.py | 기존 2배 확대 제거, 새 빵 offset 그대로 적용 |
| bimanual_mdp.py | 새 홈 기준 예비 빵 판정 |
| mdp.py | 공통 거치대 판정 사용, 빵 reset의 위험한 Y jitter 제거 |
| scenarios.py | 새 파생 manifest를 기본으로 사용 |
| source/cyclo_lab/data/objects/bread_slot/{bread_slot.usdz,rack.usda} | 보존 원본과 물리 wrapper |
| scenario_delivery/manifest_bread_slot.json | 기존 목록을 보존한 새 빵 초기 자세 |
| scripts/tools/{toast_recording_metadata,view_make_toast_scenario}.py | 기록/선택 기본 manifest 연결 및 안내 |
| scripts/tools/test_toast_scenario_runtime.py | 저장소 이름 변경 테스트에 새 manifest 포함 |
| scripts/tools/{build_bread_slot_asset,update_bread_slot_manifest}.py | 변환 및 파생 manifest 재생성 도구 |
| scripts/tools/{check_bread_slot_geometry,test_bread_slot_logic}.py | 형상/판정/reset 검증 |
| docker/compose.mj.yaml, scripts/run_mj.sh, scripts/tools/mj_python.py | 수정본 전용 실행 및 import 경로 검사 |
| README_BREAD_SLOT.md | 이 작업의 결과와 실행 방법 |

작업 전 존재하던 README_TOAST·replay 스크립트 변경과 Quest 파일은 덮어쓰지 않았다.
Quest 입력 매핑/서버/teleop 코드는 수정하지 않았다. v2의 좌우 slave joint2·3·4
stiffness=2.0, damping=0.5와 master joint1/팔 설정을 유지했다.

## 실행 경로 확인

기존 README_QUEST의 여러 명령은 이름 변경 전의 host `/home/mj/nrf_humanoid/cyclo_lab`을
가리키므로 이번 수정본 실행에는 아래 명령을 사용한다. 과거 문서를 일괄 치환하지 않았다.
기존 Docker 컨테이너의 실제 mount 및 이미지 내 editable install은 Docker 소켓 접근 거부로
조회할 수 없었다. 공유 설치를 변경하지 않고 별도 Compose project `cyclo_lab_mj`를 만들었다.

`docker compose config`에서 host mount가 `/home/mj/nrf_humanoid/cyclo_lab_mj`이고
컨테이너 target은 `/workspace/cyclo_lab`임을 확인했다. 컨테이너 내부 target 이름이
cyclo_lab인 것은 원본 host 저장소를 사용한다는 뜻이 아니다. cache/log/data volumes도
`cyclo_lab_mj_*`로 분리된다. 기존 container를 stop/recreate하지 않는다.
PYTHONPATH와 mj_python.py가 수정본 source 및 동봉 IsaacLab을 앞세우고
`cyclo_lab` spec 경로를 검사한다. host에서는 수정본 code/asset 경로 출력까지 통과했다.
실제 컨테이너 import/asset load는 미검증이다.
유일한 얕은 symlink `third_party/IsaacLab/_isaac_sim -> /isaac-sim`은 컨테이너용이며 유지했다.
호스트 `/home/mj/IsaacLab/.venv/bin/python`은 과거 `/home/rllab/...` 대상이 없어 사용할 수 없었다.
USD 검사는 작동하는 `/home/mj/hand-sim-conda/bin/python`으로 수행했다. 설치 변경은 없다.

## 검증 결과 및 증거

- CPU 테스트 39개 통과: 시나리오/기록 14, slave gain 6, Quest control 14,
  binary trigger 4, 새 100개 시나리오 reset/predicate 통합 테스트 1.
- 새 USD 크기/축/단위/충돌 API 확인, 네 빵과 rack의 초기 교차 0, 1 mm 이내 지지면 확인.
- 100개 시나리오의 거치대+빵 footprint: 추출 상판 경계 최소 여유 31.70 mm.
  기존 토스터/접시 보수적 footprint와 최소 분리축 간격 133.13 mm.
  이는 평면 배치 검사이며 팔/손 swept collision 또는 IK 검증이 아니다.
- Python 21개 파일 구문 검사, shell 구문, git diff --check 통과.
- 시스템 python에서 binary-trigger 테스트는 torch 부재로 처음 실패했지만
  conda Python으로 재실행하여 4개 통과. py_compile은 기존 cache 디렉터리 권한으로
  실패하여 cache를 쓰지 않는 compile 검사로 21개 파일을 확인했다.
- Docker smoke 시도는 소켓 접근 거부로 **시뮬레이터 시작 전에 실패**했다.
  NVIDIA-SMI도 드라이버에 연결하지 못했다. 실행 중 작업의 GPU 사용량은 확인할 수 없었다.
- 따라서 **중력 아래 안정성, 실제 PhysX collision cooking, 실제 scene reset,
  시뮬레이터 화면, Quest 실기, 로봇 집기는 미검증**이다.

증거: `logs/bread_slot_validation/geometry_results.json`, `compose_resolved.yaml`,
`smoke_attempt.log`, `front.png`, `top.png`, `oblique.png`.
PNG는 실제 USD 표면/빵 convex collider를 그린 CPU 형상도이며 Isaac Sim 스크린샷이 아니다.

## 정확한 실행 명령

별도 컨테이너에서 짧은 viewer/reset smoke (기존 실행 작업을 종료하지 않음):

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
./scripts/run_mj.sh scripts/tools/view_make_toast_scenario.py \
  --operator operator_B --scenario_index 1 --headless --steps 100 --reset_every 50
```

Quest 서버를 새 포트 8766에서 수정본 전용 bridge에 연결하는 명령:

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
python3 scripts/quest_diagnostic/server.py --host 0.0.0.0 --port 8766 \
  --bridge-dir /home/mj/nrf_humanoid/cyclo_lab_mj/logs/quest_teleop
```

Quest에서는 해당 PC의 HTTPS 8766 주소에 접속한다. 기존 practice 입력 설정을 유지한 실행:

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
./scripts/run_mj.sh scripts/quest_diagnostic/teleop_toast.py \
  --bridge-dir /workspace/cyclo_lab/logs/quest_teleop \
  --operator operator_B --scenario_index 1 --seed 1 \
  --headless --keep-open --enable-grippers --control-profile practice \
  --position-scale 1 --rotation-scale 1 --no-home-limits --no-speed-limits --workspace off \
  --max-target-lead 0.12 --max-angular-lead-deg 45 --tracking-stall-seconds 2 --preview-hz 15
```

이 명령들은 호스트에서 Docker/GPU 접근이 가능해야 한다. 기존 공유 image
`robotis/cyclo-lab:latest`를 사용하며 editable install을 다시 하지 않는다.
`MJ_CHECKOUT`, `MJ_CODE`, `MJ_RACK` 출력으로 선택된 경로를 확인할 수 있다.

CPU 재검증:

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
/home/mj/hand-sim-conda/bin/python scripts/tools/check_bread_slot_geometry.py
/home/mj/hand-sim-conda/bin/python scripts/tools/test_bread_slot_logic.py
python3 -m unittest discover -s scripts/tools -p 'test_toast*py'
```
