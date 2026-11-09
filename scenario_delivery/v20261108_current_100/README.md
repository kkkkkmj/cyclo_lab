# 현재 시나리오 — v20261108_current_100

물체 배치 변화에 따른 토스트 시연 수집용 **100개 고유 배치**다.
현재 공유 실행은 [Changes](../../CHANGES.md), 생성 범위·seed·제외 기준·분포 균형화는
[Scenario Design](SCENARIO_DESIGN.md)을 따른다. 배치 데이터와 성공 시연은 다르다.

## 그룹과 순번

| 상위 작업자 | 하위 그룹 | 개수 | 그룹 내 순번 | 상위 순번 | 첫 ID |
|---|---|---:|---|---|---|
| operator_A (50) | operator_A_1 | 25 | 1~25 | 1~25 | toast_v20261108_097 |
| operator_A (50) | operator_A_2 | 25 | 1~25 | 26~50 | toast_v20261108_087 |
| operator_B (50) | operator_B_1 | 25 | 1~25 | 1~25 | toast_v20261108_041 |
| operator_B (50) | operator_B_2 | 25 | 1~25 | 26~50 | toast_v20261108_011 |

`scenario_id`는 생성 시 고유 ID를 유지한다. 번호 suffix는 그룹/상위 순번이 아니다.
그룹2의 상위 순번은 `group_index+25`, 그룹1은 `group_index`와 같다.
기존 `--operator operator_A/operator_B --scenario_index 1..50`도 현재 manifest와 함께 사용 가능하다.
공유 기본 예시는 `--scenario_group ... --group_index ...`다. 두 방식은 혼용하지 않는다.

## 자료와 선택

- [manifest.json](manifest.json): ID, operator, scenario_group, group_index, operator_index, 물체 pose.
- [assignments.csv](assignments.csv) / [읽기용 배정표](ASSIGNMENTS.md): manifest와 같은 배정·순번.
- [poses.csv](poses.csv): 100개 ID × 7개 물체 = 700행. ID로 manifest/배정표와 연결한다. 별도 그룹 열이 없어도 ID를 다시 배정하지 않는다.
- [overview_cards.html](overview_cards.html): 로컬 브라우저에서 열기. 전체/A/B/네 하위 그룹 필터, 기본 A_1. 카드에는 그룹 내 순번을 표시하며 내장 데이터의 상위 순번도 배정표와 일치한다.
- [overview.svg](overview.svg): 그룹·그룹 내 순번으로 정렬한 정적 100개 배치도.
- [generation_config.json](generation_config.json), [distribution.json](distribution.json): seed와 종류별 quota, 분포 통계.

GUI/Quest 명령에 아래 세 옵션을 함께 지정한다. 전체 복사 가능한 명령은 [Changes](../../CHANGES.md)에 있다.

```text
--scenario_manifest scenario_delivery/v20261108_current_100/manifest.json
--scenario_group operator_A_1
--group_index 1
```

그룹 선택을 먼저 해석해 기존 recorder API의 operator/scenario_index를 채운다.
진단 metadata에는 `scenario_id`, `scenario_group`, `group_index`, `operator_index`,
operator/scenario_index와 manifest SHA256이 함께 저장된다. 진단 HDF5는 성공 학습 데이터가 아니다.

## 6종 배정 — +Y → −Y

T=toaster, P=plate, S=bread_shelf. 로봇 왼쪽에서 오른쪽 순서다.

| 순서 | A_1 | A_2 | B_1 | B_2 | 합계 |
|---|---:|---:|---:|---:|---:|
| T>P>S | 5 | 4 | 4 | 4 | 17 |
| T>S>P | 4 | 4 | 5 | 4 | 17 |
| P>T>S | 4 | 5 | 4 | 4 | 17 |
| P>S>T | 4 | 4 | 4 | 5 | 17 |
| S>T>P | 4 | 4 | 4 | 4 | 16 |
| S>P>T | 4 | 4 | 4 | 4 | 16 |
| 합계 | 25 | 25 | 25 | 25 | 100 |

## 검증 범위와 재현

이번 안내 정리는 기존 ID·배정·pose·HTML 데이터·생성기를 변경하지 않는다.
그룹/상위 선택과 ID, pose CSV, 카드 내장 인덱스, 기록 metadata를 CPU에서 대조한다.
정적 거리·형상 검사는 도달 가능성·동일 조작 난이도·전체 PhysX 안정성을 보장하지 않는다.
거치대 내려앉음과 실제 VR 상태는 [Changes](../../CHANGES.md)의 제한사항을 따른다.

시나리오 재생성은 [설계 문서](SCENARIO_DESIGN.md)의 독립 입력·명령을 사용한다.
제공된 카드 HTML은 자체 포함이라 열 때 별도 파일이 필요 없다. 다만 **카드 HTML 재빌드 도구**
`build_toast_overview_cards.py`는 당시 Git 제외 로그의 `collision_geometry.json` snapshot을 요구한다.
따라서 깨끗한 clone에서 카드 재빌드까지 재현 가능하다고 주장하지 않는다. 시나리오 생성기와
카드 빌더는 다른 도구이며, 이번에는 어느 쪽도 실행하거나 산출물을 바꾸지 않았다.

[기존 생성·검증 기록](../../docs/toast_quest/history/SCENARIOS_CURRENT_DELIVERY.md) ·
[상위 버전 안내](../README.md) · [거치대 진단](rack_diagnosis_20261109/README.md)
