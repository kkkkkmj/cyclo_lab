# Scenario Design

물체 배치 변화에 따른 토스트 작업 시연을 수집하기 위한 새 100개 배치다.
아래 수치는 현재 [생성기](../scripts/tools/generate_current_toast_scenarios.py),
[생성 설정](generation_config.json), [manifest](manifest.json)을 대조한 값이다.

## 좌표와 배치 구성

환경 원점에 대한 pose를 사용한다. 고정 로봇 기준 +X는 테이블 쪽 전방, +Y는 로봇 왼쪽,
−Y는 오른쪽, +Z는 위다. 순서는 **+Y → −Y(로봇 왼쪽 → 오른쪽)**로 읽는다.
관찰 카메라의 화면 좌우와 혼동하지 않는다. 다중 환경의 월드 위치에는 env origin이 더해진다.
거리 단위 m, quaternion은 **wxyz**다. 생성기 yaw jitter 설정은 **도(°)**이며 내부에서 rad로 변환한다.

세 물체의 6개 순열을 사용한다. 각 순열에서 첫/둘째/셋째 물체의 Y 앵커는 +0.400/0/−0.400 m다.

| 물체 | 생성 X 앵커 | ΔX | ΔY | 고정 Z | 기준 yaw | Δyaw | scale |
|---|---:|---:|---:|---:|---:|---:|---|
| toaster | 0.550 | ±0.015 | ±0.015 | 1.081800 | 150° | ±5° | 1,1,1 |
| plate | 0.490 | ±0.010 | ±0.015 | 1.004222776 | 0° | ±5° | 1.5,1.5,0.22 |
| bread_shelf | 0.460 | ±0.015 | ±0.015 | 1.038200021 | −90° | ±5° | 1,1,1 |

Yaw 변화는 환경 Z축 회전 quaternion을 기준 자세에 왼쪽 곱한다. Z와 scale은 변동시키지 않는다.
종류별 9차원(X/Y/yaw × 세 물체) Latin hypercube 후보를 만들고 부적합 후보를 다시 뽑는다.

**환경 baseline과 생성 앵커는 다르다.** 거리 분포의 baseline displacement는 아래 원래 환경
pose와의 거리이며 위 생성 앵커에 대한 jitter 크기와 별도 지표다.

| 물체 | 환경 baseline XYZ (m) |
|---|---|
| toaster | (0.550, 0.230, 1.081800) |
| plate | (0.430, 0.035, 1.004222776) |
| bread_shelf | (약 0.450, −0.250, 약 1.038200021) |

## 생성·제외 기준과 검사 범위

| 검사 | 실제 적용 |
|---|---|
| 계획 테이블 범위 | X=[0.318999970,1.081000007], Y=[−1.336823260,1.136823257] m에서 가장자리 20 mm 여유 |
| 실제 추출 상판 | authored collision face 다각형에 20 mm 확장 footprint 포함 여부. 대략 X=[0.341857712,1.058142302], Y=[−1.318215319,1.118215316], 상판 Z=0.994051339 m. 정확한 꼭짓점은 manifest에 저장 |
| 형상 범위 | 현재 USD mesh의 보수적 convex XY footprint; 주 물체에 축별 1 mm 확장. 토스터 LED 형상 포함 |
| 물체 간격 | 토스터·접시·거치대+빵 묶음 footprint 간 **최소 60 mm**. 설정의 collision 30 mm보다 강한 approach 60 mm가 실제 거부 기준 |
| 빵끼리 | 네 빵 XY footprint 겹침/접촉(거리 ≤0) 제외 |
| 접시 | X>0.419 m |
| 모델 거리 제외 | 집기/삽입/추출/레버/서빙 probe 중 양팔 모두 shoulder lift 구간에서 링크 길이 상한 밖이면 제외 |
| 중복 | 새 100개 및 보존된 이전 입력의 pose signature SHA256과 중복 제외. 위치 소수 6자리·정규화 quaternion 7자리 기준 |
| 초기 rack/bread 관통 | 별도 CPU/USD 검사에서 authored rack 삼각형과 bread convex 형상 교차 검사. 모든 배치의 rack-local pose 동일성도 검사 |

거치대는 230×130×45 mm이며 네 빵을 독립적으로 랜덤 배치하지 않는다.
현재 거치대 local bread root XYZ는 아래와 같고, 공통 상대 quaternion은
(0.7071067812, 0, 0.7071067812, 0), 빵 scale은 (1,1,1)이다.

| ID | local X | local Y | local Z (m) |
|---|---:|---:|---:|
| bread_0 | 0.084392445 | 0.000249905 | 0.044351338865 |
| bread_1 | 0.024392445 | 0.000249905 | 0.044351338865 |
| bread_2 | −0.035607555 | 0.000249905 | 0.044351338865 |
| bread_3 | −0.095607555 | 0.000249905 | 0.044351338865 |

거치대의 baseline→새 pose rigid transform을 네 빵 위치·자세에 함께 적용한다.
거치대+네 빵 외곽을 하나의 hull로 묶어 다른 물체 및 테이블 여유를 검사한다.

현재 생성 결과는 후보 100개/채택 100개, 거부 0개, 이전 pose 중복 0개이며
최소 물체 간격은 약 **138.99 mm**다. 거리 필터는 제외 검사일 뿐 **로봇 도달 가능성 검증이 아니다**.
IK, 충돌 없는 경로, grasp, 전 과정 성공, cooked PhysX 접촉, 전체100개 동적 안정성은 미검증이다.
별도 정적 검사에서 초기 관통 없음/1 mm 내 접촉을 확인했지만 안정 지지를 증명하지 않는다.
첫 배치의 실제 내려앉음이 기록돼 있으며 정상 안착/관통 여부는 아직 확정하지 않았다.

## 작업자 배정

A/B 각 50개, 하위 그룹 각 25개다. T=toaster, P=plate, S=bread_shelf.

| +Y → −Y 순서 | A_1 | A_2 | B_1 | B_2 | 합계 |
|---|---:|---:|---:|---:|---:|
| T>P>S | 5 | 4 | 4 | 4 | 17 |
| T>S>P | 4 | 4 | 5 | 4 | 17 |
| P>T>S | 4 | 5 | 4 | 4 | 17 |
| P>S>T | 4 | 4 | 4 | 5 | 17 |
| S>T>P | 4 | 4 | 4 | 4 | 16 |
| S>P>T | 4 | 4 | 4 | 4 | 16 |
| 합계 | 25 | 25 | 25 | 25 | 100 |

종류별 고정 quota를 유지하면서 같은 종류 안에서 그룹 label을 최대 50,000회 교환한다.
특성은 물체별 signed ΔX/ΔY/Δyaw, 절대 yaw, XY jitter 크기, baseline 이동 거리,
로봇 원점까지 3D/XY 거리, probe–shoulder lift 구간 거리의 최댓값이다.

각 특성을 표준화하고 제곱값(가중치 0.35), 25/50/75% 분위수 초과 지표(가중치 1.5)를
이어 붙인다. 중심화한 그룹별 합의 제곱합을 줄이며 온도는 2에서 최소 0.01로 낮춘다.
저장된 목적함수 값은 3655.088→670.205다. 마지막에 종류별 목록을 섞어 교차 순서로 배정한다.
이는 **위치·회전·거리 분포의 균형**이며 실제 작업자의 조작 난이도가 같다는 보장이 아니다.
[distribution.json](distribution.json)에 그룹별 원 지표 통계를 보존한다.

## 재현과 선택

생성 seed **20261108**, 배정 seed **20261109**(생성 seed+1).
설치는 [Changes](../CHANGES.md)를 따른다. numpy/scipy/torch/pxr가 설치된
Python 실행 파일을 `TOAST_PYTHON`으로 지정하고 checkout 루트에서 실행한다.

```bash
export TOAST_PYTHON=python3
MJ_SCENARIO_OUTPUT=$(mktemp -d /tmp/toast-scenarios-rebuild.XXXXXX)
"$TOAST_PYTHON" scripts/tools/generate_current_toast_scenarios.py \
  --seed 20261108 \
  --evidence scenario_delivery/inputs/geometry_evidence.json \
  --output "$MJ_SCENARIO_OUTPUT"
"$TOAST_PYTHON" scripts/tools/test_current_toast_delivery.py
```

기존 출력은 덮어쓰지 않는다. 현 환경 baseline/asset 및 저장된 형상 증거를 검사한 뒤 생성한다. 이전 목록을 다시 포함하지 않고
`inputs/generation_history.json`의 원래 pose 서명 SHA256과 원본 입력 해시를 사용한다.
저장 manifest의 소스 해시는 생성 당시 +15 mm 소스를 기록하므로 현재 +35 mm 소스로 재생성하면
provenance 해시는 달라진다. 폴더 이동 전 manifest는 바이트 그대로 유지했으며, 경로를 수정한
현재 소스 해시는 [별도 기록](../docs/toast_quest/SCENARIO_RELOCATION.json)으로 검증한다. 과거 manifest를 최신 해시로 덮어쓰지 않으며 pose/배정 재현과
파일 전체 바이트 재현을 구분한다.

| 식별자 | 관계 |
|---|---|
| scenario_id | `toast_v20261108_000`~`099`, 생성 순서의 고유 ID. 배정 순번과 다름 |
| scenario_group/group_index | operator_A_1/A_2/B_1/B_2, 각 1~25 |
| operator/operator_index | operator_A/B, 각 1~50. 그룹1은 index 그대로, 그룹2는 index+25 |

예: `--scenario_group operator_A_2 --group_index 1`은
`--operator operator_A --scenario_index 26`과 같고 ID는 `toast_v20261108_087`이다.
기본 manifest는 `scenario_delivery/manifest.json`이며,
`--scenario_manifest scenario_delivery/manifest.json`으로 명시해도 같은 목록을 선택한다. ID/그룹/상위 operator 선택은 혼용하지 않는다. GUI·Quest 전체 명령은 [시나리오 README](README.md)를 따른다.

[Manifest](manifest.json) · [CSV 배정표](assignments.csv) · [읽기용 배정표](ASSIGNMENTS.md) ·
[700개 물체 pose CSV](poses.csv) · [카드형 100개 배치도](overview_cards.html) · [SVG 배치도](overview.svg)
