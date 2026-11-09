# toast_v20261108_000 거치대 진단

## 결론과 현재 한계

확인된 문제는 기존 정적 검사에서 **1mm 내 접촉을 안정 지지로 해석한 것**이다. 초기 빵을 1mm 낮췄을 때 실제 접촉 패치는 거치대 +Y 어깨 한쪽에만 있다. 바닥에서 안정적으로 받치는 배치가 아니므로 그 검사만으로 물리 안정성을 보장할 수 없다.

기록된 최종 상태는 홈 바닥에 내려앉는 설명과 맞지만, **PhysX cooked collider/접촉 상대가 이전 로그에 없어 정상 안착으로 확정하지 않았다.** 관통 문제로 단정할 근거도 부족하다. 새 진단 실행이 필요하다. 따라서 rack asset, 빵 기본 pose, manifest, 물리 허용오차는 변경하지 않았다. 정상 종료와 안정성을 확인하지 못해 전체100개로 확대하지 않았다.

## 사용한 기존 기록 (읽기만 함)

- `logs/toast_worker_debug_20261109_003408/toast_v20261108_000.json`: 5초×2 상세 결과, reset PASS
- 같은 폴더의 `toast_v20261108_000.run1.jsonl.gz`, `.run2.jsonl.gz`: 초기/중간/최종 pose
- `logs/toast_worker_debug_20261109_002946/toast_v20261108_000.json`: inference tensor를 inference_mode 밖 reset에서 갱신한 실제 traceback
- `logs/toast_precollection_physx_20261109_002207`: 이전 batch 로그·첫 trace

새 분석: [샘플 CSV](trace_samples.csv), [상세 JSON](reconstruction/analysis.json), [형상 분석](geometry_analysis.txt).

두 trial에서 bread_0~3은 약 −18.499~−18.502mm 하강, XY 약4.72~4.80mm 이동, 약6.02~6.08° 회전한다. 최종 선속도는 사용자 관측과 일치하는 작은 값이다. robot 최대 관절 drift는 약5.26e−7, toaster/rack는 움직이지 않고 plate는 Z 약−6.29mm 정착한다. 종료 이벤트는 없다. 반복 결과는 거의 동일하다.

trace_samples.csv는 physics sample1/10/25/50/100/500을 포함한다. 구 trace에는 dt가 없어 현재 환경100Hz를 기준으로 시간 열을 계산했다. 새 trace에는 실제 physics_dt로 시간을 직접 저장한다.

로봇/다른 물체가 빵을 밀었다는 증거는 없다. 다른 주 물체와는 앞서 검사한 XY 분리 간격이 있고 로봇 관절도 거의 움직이지 않는다. **그러나 구 trace에는 접촉 힘/상대 body 기록이 없고 로봇 mesh와 빵의 연속 충돌 검사를 하지 않았으므로 밀지 않았다고 확정하지 않는다.**

## 형상과 지지 위치

| 항목 | 확인된 authored 설정 |
|---|---|
| rack | `bread_slot/rack.usda` → `bread_slot.usdz`, 230×130×45mm |
| rack collider | `/BreadSlot/Model/Body1`, collisionEnabled=true, approximation=none, static triangle mesh |
| 변환 | mm→m scale0.001 + X90° + localZ−0.0441486611m, root world scenario pose |
| bread | `/World/collision`, collisionEnabled=true, approximation=convexHull, scale1 |
| bread 원본 | visual과 collision의 점 범위는 일치; convexHull cooking 결과와 동일함을 뜻하지 않음 |
| rack local 최저 Z | −0.0441486611m |
| 홈 바닥 local Z | −0.0291486611m |
| table top world Z | 0.9940513389m |
| 홈 바닥 world Z | 약1.00905136m = table+15mm |
| 최종 bread convex 최저 Z | 약1.008827~1.008833m = table+14.78mm |

최종 authored bread 최저점은 홈 바닥보다 약0.22mm 낮고 테이블보다14.8mm 높다. 따라서 현재 기록+authored collider 기준으로는 **테이블에 직접 누워 지지된 상태와 맞지 않는다.** rack 바닥 부근의 접촉과 맞지만 cooked contact 확인 전까지 최종 지지 상대는 추정이다.

초기1mm 하강 접촉 패치(bread_0)의 rack-local 범위는 X87.97~91.87mm, Y57.50~57.97mm, Z−4.18~−2.16mm이다. 한쪽 어깨 접촉만 검출된다. 최종 authored convex와 rack triangle은 바닥 및 끝단에서 교차한다. 원래 clipper의 triangle 전체 bounds는 접촉 패치 크기가 아니므로 새 분석에서는 실제 clipped polygon bounds를 따로 계산했다.

원본 bread에는 convexDecomposition 관련 속성도 남아 있지만 활성 approximation은 convexHull이다. 해당 decomposition 속성만 보고 runtime 형상을 단정하지 않았다. rack의 수평 바닥 삼각형 normal은 위쪽이며 signed volume은 양수라 전역 winding 반전 증거는 없다.

**최종 pose를 단순 복사하거나18.5mm 일괄 낮추지 않았다.** 연구용 `reconstruction/seated_candidate_v1.json`에는 측정된 최종 orientation/XY와 authored convex 비관통을 위한 위쪽 탐색을 저장했지만, 끝단 간섭을 수직 이동만으로 해소하려면 약4.86~5.13mm가 필요했다. 이는 올바른 안착 초기값으로 승인할 수 없는 후보다. review=WITHHELD이며 기본 환경/manifest에는 적용하지 않는다. 새 접촉 및 composed collider 자료로 실제 불일치를 먼저 확인해야 한다.

## 화면 자료

- [초기 충돌 형상 재구성](reconstruction/initial_collision_reconstruction.png)
- [최종 충돌 형상 재구성](reconstruction/final_collision_reconstruction.png)

두 그림은 **기록된 PhysX pose + authored collision의 CPU 재구성**이며 실제 simulator screenshot이나 cooked shape 표시가 아니다. 실제 GUI 실행이 불가능해 새 스크린샷은 아직 없다. `--diagnostics` 실행 시 현재 환경 RGB 카메라의 초기·각 trial 최종 PNG를 저장한다. 카메라 시야가 거치대를 충분히 포함하지 않으면 GUI에서 확인해야 한다.

## 검사기 최소 수정

- env 생성, 초기/reset/5초×2 전체 검사 및 teardown을 torch.inference_mode 안에서 수행. 구 예외 기록 기능 유지.
- 매 trial 완료 직후 상세 JSON checkpoint. step 예외 시에도 수집된 trace를 finally에서 저장.
- 물리 결과 `.json`과 예외 `.exception.json`, 정리 `.lifecycle.json`, 부모 프로세스 `.process.json`을 분리.
- worker nonzero exit가 상세 JSON을 덮어쓰던 동작 제거. JSON 누락=MISSING, 손상=CORRUPT를 sidecar에 명시하고 손상 파일도 보존.
- 카메라 정리 전에 scene/manager의 strong reference를 유지하고 sensor callbacks 해제 → camera annotator.detach → registry 비우기 → env.close → app.close 순서. destructor가 다시 detach하지 않도록 처리. 정리 오류는 단계별 traceback으로 저장하며, 로그에 weakref 오류가 있으면 exit0이어도 process ERROR.
- 기존 카메라 구현은 `Camera.__del__`에서 annotator.detach, 환경 close는 scene/manager 삭제 후 sim을 정리한다. 이 순서와 weak proxy 수명을 피하도록 수정했다. **해당 weakref 오류의 전체 사용자 console traceback은 저장된 로그에서 찾지 못했으며 수정 후 실제 Isaac 정상 종료도 미검증이다.**
- `--scenario-id`를 physx batch 모드에서도 처리하여 정확히000 하나만 실행.
- `--diagnostics`: 실제 composed collider prim/활성/approximation/world matrix/points/physics 속성, RGB, PhysX contact header의 actor/collider 및 접촉 위치·normal·impulse 저장. contact report API는 보고 기능만 켜고 충돌 형상·질량·구동값은 바꾸지 않는다. callback 오류는 결과에 기록한다. composed USD는 cooked mesh가 아니며 그 차이를 파일에 명시한다.
- 전체100개는 `--gate-result`에 000의 physics PASS + reset PASS + 두 trial≥5초 + process PASS인 결과를 주어야 시작 가능. 실험 초기 pose 후보를 쓴 결과는 production manifest 검증으로 인정하지 않는다.

변경 파일: `scripts/tools/validate_toast_collection.py`, 추가 `toast_audit_lifecycle.py`, `toast_rack_runtime_diagnostics.py`, `diagnose_rack_settling.py`, `test_toast_audit_lifecycle.py`. 기존 사용자 inference_mode/예외 기록 수정을 보존해 확장했다.

## Ubuntu에서 먼저 단일 시나리오 실행

이 세션의 실행 시도는 [launch_attempt.log](launch_attempt.log)에 기록한 Docker 소켓 permission denied로 실패했다. 기존 프로세스를 건드리지 않았다. 아래는 Docker/GPU가 동작하는 Ubuntu 터미널에서 실행한다.

```bash
cd /home/mj/nrf_humanoid/cyclo_lab_mj
MJ_RACK_RUN="logs/rack_pilot_$(date +%Y%m%d_%H%M%S)"
bash scripts/run_mj.sh scripts/tools/validate_toast_collection.py \
  --mode physx --headless --seconds 5 --diagnostics \
  --scenario-id toast_v20261108_000 \
  --manifest scenario_delivery/v20261108_current_100/manifest.json \
  --output "$MJ_RACK_RUN"

python3 -m json.tool "$MJ_RACK_RUN/toast_v20261108_000.json"
python3 -m json.tool "$MJ_RACK_RUN/toast_v20261108_000.process.json"
```

출력의 `.contacts.jsonl`에서 Bread와 rack collider 또는 table/Robot의 실제 접촉을 확인하고, `initial.colliders.json`과 `final_run*.colliders.json`에서 authored/local 분석과 runtime transform/approximation을 대조한다. lifecycle/exception도 확인한다. 현재 기본 배치는 수정하지 않았으므로 **기존 이동 FAIL이 재현될 수 있다.** 이 실행의 목적은 해결되지 않은 실제 지지/형상/종료 정보를 얻는 것이다.

GUI로 같은 검사를 하려면 위 명령의 `--headless`를 빼고 `scripts/run_mj.sh` 바로 뒤에 `--gui`를 넣는다. 먼저 `export DISPLAY=:1` 및 `export XAUTHORITY=/run/user/1000/gdm/Xauthority`를 현재 데스크톱 세션 값으로 설정한다.

안정성과 종료가 실제로 PASS하고 필요한 수정이 별도 manifest 버전으로 확정된 뒤에만 전체100개로 확대한다. **현재는 아래 명령을 실행할 단계가 아니며 gate가 거부해야 정상이다.**

```bash
bash scripts/run_mj.sh scripts/tools/validate_toast_collection.py \
  --mode physx --headless --seconds 5 \
  --gate-result "$MJ_RACK_RUN/toast_v20261108_000.json" \
  --manifest scenario_delivery/v20261108_current_100/manifest.json \
  --output "logs/rack_all100_$(date +%Y%m%d_%H%M%S)"
```

## 검증 및 보존

기존 audit CPU/모의7개 + lifecycle6개 =13개 통과. JSON nonzero 종료 보존, 누락·손상 분류, 정리 순서/정리 예외, 기존 reset/대기 동작 확인. 실제 PhysX 재실행 및 카메라 정상 종료는 미검증.

기존 로그·manifest·asset·gain·속도·VR·토스터 동작·성공 조건, 원본 cyclo_lab은 변경하지 않았다. 허용오차도 그대로다. commit/push하지 않았다.
