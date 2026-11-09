# 과거 측정·검증 참고 자료

현재 설정·설치·명령은 [Changes](../../CHANGES.md) 한 곳을 따른다.
아래 보고서는 당시 설정과 결과를 보존한 근거이며 최신 실행 안내가 아니다.

| 자료 | 범위 |
|---|---|
| [원본 비교](BASELINE.md) | 고정 원본 커밋, 분야별 변화, 기존 README 보존 |
| [검증 기록](VALIDATION.json) | 문서 통합 이전 CPU·파일 추출·재생성 결과 |
| [거치대 진단](https://github.com/kkkkkmj/cyclo_lab/blob/a18eb900aea6d6110dedb45f3f616411f7750c42/scenario_delivery/v20261108_current_100/rack_diagnosis_20261109/README.md) | 약 18.5 mm 내려앉음과 cooked contact 미확인 |
| [거치대 교체 당시 기록](history/BREAD_SLOT.md) | 형상/초기 pose/과거 정적 판단 |
| [gain 당시 기록](history/GRIPPER_GAINS.md) / [속도 당시 기록](history/GRIPPER_SPEED.md) | 2/0.5 비교값과 100/4, master 상한 변경·CPU/readback 한계 |
| [Quest 작업 기록](history/QUEST.md) | HUD·입력·기록·재생·응답 실험의 당시 결과 |
| [LED 당시 기록](history/TOASTER_LED.md) / [성공 조건 당시 기록](history/TOAST_SUCCESS.md) | 단계별 로직 변경과 당시 테스트 |

history의 코드·호스트 경로·개인 로그 위치는 과거 기록으로 남겼다. 현재 공유 실행을 위해 복사할
파일 목록이 아니며, 과거 gain 설명은 [고정 기준 비교](BASELINE.md)의 정정과 함께 읽는다.
CPU 검사, 과거 +15 mm PhysX 측정, 현재 +35 mm/VR 미검증 상태는 서로 구분한다.

상승 목표 +15 → +35 mm의 현재 설정은 [Changes](../../CHANGES.md#③-현재-최종-설정과-성공-조건)를 따른다.
개인 측정 원본과 도구는 로컬 백업으로 이동했으며 공유 실행의 의존 파일이 아니다.
