# 시나리오 안내

**현재 공유 버전은 [v20261108_current_100/](v20261108_current_100/README.md)** 이다.
설치·GUI·Quest 전체 실행 순서는 [Changes](../CHANGES.md)를 따른다.
공유용 기본 선택은 네 하위 그룹 방식이며, 현재 manifest를 명시해야 한다.

| 상위 작업자 | 하위 그룹 | 개수 | 그룹 내 순번 | 상위 순번 |
|---|---|---:|---|---|
| operator_A (50개) | operator_A_1 | 25 | 1~25 | 1~25 |
| operator_A (50개) | operator_A_2 | 25 | 1~25 | 26~50 |
| operator_B (50개) | operator_B_1 | 25 | 1~25 | 1~25 |
| operator_B (50개) | operator_B_2 | 25 | 1~25 | 26~50 |

현재 ID는 `toast_v20261108_000`~`099`이며 ID 숫자는 배정 순번이 아니다.
[Manifest](v20261108_current_100/manifest.json) · [배정표](v20261108_current_100/ASSIGNMENTS.md) ·
[pose CSV](v20261108_current_100/poses.csv) · [카드 배치도](v20261108_current_100/overview_cards.html) ·
[Scenario Design](v20261108_current_100/SCENARIO_DESIGN.md)

## 선택 예시

설치를 마친 checkout에서 실행한다. `REPO`, `DISPLAY`, `XAUTHORITY`는 사용자 환경에 맞춘다.
GROUP은 위 네 값 중 하나, INDEX는 1~25다. Quest도 동일한 manifest/그룹 옵션을 사용한다.

```bash
export REPO=/path/to/cyclo_lab_toast_quest
cd "$REPO"
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
GROUP=operator_A_2
INDEX=1
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py \
  --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json \
  --scenario_group "$GROUP" --group_index "$INDEX"
```

위 선택은 `toast_v20261108_087`이다. 상위 호환 선택
`--operator operator_A --scenario_index 26`과 같다. 서로 다른 선택 방식을 한 명령에 섞지 않는다.
시나리오 선택만으로 학습 시연이 저장되지는 않는다.

## 과거 버전 — 원본 데이터 보존

| 자료 | 의미 |
|---|---|
| [manifest.json](manifest.json) | 이전 `batch02_toast_000`~`099` 배치 |
| [manifest_bread_slot.json](manifest_bread_slot.json) | 이전 ID/배정에 새 rack 상대 pose를 반영한 파생 목록 |
| [assignments.csv](assignments.csv), [배정표](ASSIGNMENTS.md) | 이전 operator_A/B 각 50개, 하위 그룹 없음 |
| [preview.html](preview.html) | 이전 목록의 배치도 |
| [이전 안내 보존본](../docs/toast_quest/history/SCENARIOS_BATCH02.md) | 당시 설계·실행·검증 기록 |

이전 A/B 표기를 현재 하위 그룹으로 바꾸거나 재배정하지 않았다. 기존 선택 기능과 기본 manifest도
호환성을 위해 그대로이므로, **현재 목록은 `--scenario_manifest`를 생략하지 않는다**.
이전 목록의 검증 결과를 현재 100개 PhysX 검증으로 해석하지 않는다.
