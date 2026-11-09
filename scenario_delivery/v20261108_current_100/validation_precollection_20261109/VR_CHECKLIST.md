# VR 수집 전 확인 대상

6종류 × 4그룹 대표 24개 + 그룹별 최장 거리/최소 간격/최대 yaw 변화. 중복 ID는 한 번만 실행한다. 거리의 의미는 휴리스틱 probe–리프트 어깨 구간 거리이며 도달성 증명이 아니다.

먼저 Ubuntu GUI 터미널:
```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
export DISPLAY=:1
export XAUTHORITY=/run/user/1000/gdm/Xauthority
```

Quest 전용 서버(별도 터미널, 기존 프로세스를 종료하지 않음; IP는 실제 PC 주소로 확인, 포트 점유 시 미사용 포트 사용):
```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
python3 scripts/quest_diagnostic/server.py --host 192.168.10.116 --port 8766 --bridge-dir /home/mj/nrf_humanoid/cyclo_lab_mj/logs/quest_precollection_v20261109
```
Quest에서 https://192.168.10.116:8766/ 접속 후 Pair. 이미 동일 bridge를 사용하는 시뮬레이션이 있으면 종료시키지 말고 별도 bridge를 지정한다. 아래 명령은 하나씩 실행한다.

## toast_v20261108_012 · operator_A_1 #5

operator_A_1 type 1 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 5
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 5 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_044 · operator_A_1 #6

operator_A_1 type 3 representative; operator_A_1 largest absolute yaw perturbation

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 6
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 6 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_055 · operator_A_1 #7

operator_A_1 type 4 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 7
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 7 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_024 · operator_A_1 #11

operator_A_1 type 2 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 11
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 11 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_075 · operator_A_1 #16

operator_A_1 narrowest surface-bound gap

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 16
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 16 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_096 · operator_A_1 #19

operator_A_1 type 6 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 19
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 19 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_013 · operator_A_1 #21

operator_A_1 farthest heuristic probe distance

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 21
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 21 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_079 · operator_A_1 #24

operator_A_1 type 5 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 24
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_1 --group_index 24 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_087 · operator_A_2 #1

operator_A_2 type 6 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 1
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 1 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_082 · operator_A_2 #3

operator_A_2 type 5 representative; operator_A_2 largest absolute yaw perturbation

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 3
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 3 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_046 · operator_A_2 #4

operator_A_2 type 3 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 4
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 4 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_030 · operator_A_2 #5

operator_A_2 farthest heuristic probe distance

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 5
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 5 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_053 · operator_A_2 #6

operator_A_2 type 4 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 6
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 6 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_015 · operator_A_2 #15

operator_A_2 type 1 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 15
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 15 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_032 · operator_A_2 #19

operator_A_2 type 2 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 19
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 19 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_063 · operator_A_2 #24

operator_A_2 narrowest surface-bound gap

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 24
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_A_2 --group_index 24 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_095 · operator_B_1 #2

operator_B_1 type 6 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 2
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 2 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_002 · operator_B_1 #3

operator_B_1 type 1 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 3
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 3 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_049 · operator_B_1 #10

operator_B_1 type 3 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 10
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 10 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_006 · operator_B_1 #13

operator_B_1 farthest heuristic probe distance

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 13
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 13 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_065 · operator_B_1 #14

operator_B_1 type 4 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 14
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 14 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_027 · operator_B_1 #18

operator_B_1 largest absolute yaw perturbation

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 18
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 18 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_057 · operator_B_1 #20

operator_B_1 narrowest surface-bound gap

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 20
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 20 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_072 · operator_B_1 #22

operator_B_1 type 5 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 22
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 22 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_033 · operator_B_1 #24

operator_B_1 type 2 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 24
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_1 --group_index 24 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_011 · operator_B_2 #1

operator_B_2 type 1 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 1
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 1 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_010 · operator_B_2 #10

operator_B_2 farthest heuristic probe distance

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 10
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 10 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_071 · operator_B_2 #11

operator_B_2 type 5 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 11
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 11 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_051 · operator_B_2 #12

operator_B_2 type 4 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 12
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 12 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_034 · operator_B_2 #15

operator_B_2 type 3 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 15
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 15 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_023 · operator_B_2 #16

operator_B_2 type 2 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 16
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 16 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_054 · operator_B_2 #20

operator_B_2 narrowest surface-bound gap

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 20
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 20 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_098 · operator_B_2 #22

operator_B_2 type 6 representative

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 22
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 22 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지

## toast_v20261108_007 · operator_B_2 #24

operator_B_2 largest absolute yaw perturbation

```bash
bash scripts/run_mj.sh --gui scripts/tools/view_make_toast_scenario.py --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 24
bash scripts/run_mj.sh --gui scripts/quest_diagnostic/teleop_toast.py --bridge-dir /workspace/cyclo_lab/logs/quest_precollection_v20261109 --scenario_manifest scenario_delivery/v20261108_current_100/manifest.json --scenario_group operator_B_2 --group_index 24 --enable-grippers --keep-open
```

- [ ] 초기 빵 4개 지지·테이블 여유·로봇 대기 확인; 시험한 bread ID와 사용 손/슬롯 기록
- [ ] 빵 집기: 손가락 접근·접촉·안정 집기 확인
- [ ] 토스터 삽입: 주변 물체/로봇 충돌 없이 정상 적재 확인
- [ ] 레버 90% 진입 시 실제 cycle 시작·LED ON
- [ ] 하강 완료 후 4초 가열·상승 시작 LED OFF·복귀 완료
- [ ] 같은 가열 완료 빵을 접시에 배치(중심20mm/높이/기울기/속도)
- [ ] 양 그리퍼 열림·양팔 standby·리프트 복귀 후 실제 success 확인
- [ ] reset 후 pose·LED·가열 기록 초기화 및 재시도
- [ ] 영상/기록 경로, 성공/실패, 실패 단계 기록. 미시험 빵은 UNVERIFIED 유지
