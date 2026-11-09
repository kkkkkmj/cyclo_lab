토스트 상승 노출 높이 측정 — bread_0 / v2
작성일: 2026-11-09
작업 checkout: /home/mj/nrf_humanoid/cyclo_lab_mj
task: Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2

현재 상태
---------
PhysX 실측 미실행. 이 세션의 nvidia-smi는 드라이버 통신 실패,
/dev/nvidia* 장치 없음, Docker API는 /var/run/docker.sock permission denied.
따라서 ③ 완료 시점 및 ⑤ 완료 1초 후의 노출 높이/비율은 미측정이다.
추정값, 과거 로그의 값, 정적 asset 높이를 실측값으로 채우지 않았다.
정적 USD 읽기와 수학 검증만 성공했다. 전체 실행/RGB는 Ubuntu GPU 실행이 필요하다.

현재 코드에서 확인한 동작
------------------------
source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/
  toast_cycle.py / bimanual_env.py / bimanual_env_cfg.py / scene.py

phase 0: 대기. 레버 누름 비율 >=0.90의 상승 에지, 적재된 빵이 하나 이상이면 phase 1.
phase 1: smoothstep으로 0 -> -0.045 m 하강, 명목 시간 0.60 s.
  가열 진입은 elapsed >=0.60 s AND |q+0.045|<0.0015 m AND |qd|<0.01 m/s.
phase 2: 하강 완료 시 elapsed=0부터 4.0 s 가열, 캐리지 목표 -0.045 m.
  elapsed >=4.0 s일 때 phase 3, elapsed=0.
phase 3: 0.80 s smoothstep으로 -0.045 -> +0.015 m 상승.
  v2의 toast_popup_extra_height=0.015 m; 상승 총 목표 이동량은 60 mm.
  phase 4 진입: elapsed >=0.80+0.12 s AND |q-0.015|<0.0015 m.
  상승 완료에는 속도 조건이 없다. 실제 진입 시간은 제어 스텝/물리에 따라 결정된다.
phase 4: 캐리지 목표 +0.015 m 유지.
캐리지 위치 q는 관절 변위이며 월드 높이 또는 빵 노출 높이가 아니다.
가열 도중 슬롯에서 이탈한 빵은 heating_present가 해제되고 그 사이클의 가열 증거를 잃는다.

기존 설정: carriage drive stiffness=8000, damping=120, effort_limit=40 N,
velocity_limit=0.12 m/s, carriage mass=0.15 kg, v2 관절 범위 [-0.045,+0.015] m.
실행 스크립트는 이 값들과 success/termination 함수를 변경하지 않는다.
v2 성공 조건은 가열된 빵의 접시 배치, 접시 자세/위치, phase 4와 레버 복귀,
로봇 standby/그리퍼/리프트 조건을 포함한다. 이 진단은 성공 조건을 우회하지 않으며
로봇 집기나 접시 서빙의 성공 검증도 아니다.

중요: 기존 scripts/tools/check_toast_cycle.py의 고정 높이 노출식이나 출력의
heating_seconds=5 리터럴은 본 측정에 사용하지 않았다. 실제 ToastCycle은 4.0 s이다.

윗면과 시각 형상 기준
--------------------
토스터 asset: source/cyclo_lab/data/objects/robodojo_make_toast/toaster/object.usdz
실제 면: /root/base/visuals/base_body_30/World/mesh, face index 0..13 (0부터 시작).
이는 두 슬롯 개구부 주변의 상판 삼각형이며, 토스터 AABB나 레버가 아니다.
슬롯0 개구부의 asset Y 범위는 대략 [-0.0394083,-0.0135015] m,
슬롯1은 [0.0124051,0.0383120] m. rim_faces_static.svg에서 면 번호와 개구부 확인 가능.
asset base 좌표의 평면은 거의 z=0.08023290336 m이며,
static_geometry_audit.json에 면별 정점과 평면 계수/잔차/asset SHA256을 기록했다.
이 숫자는 월드 실측 z_rim이나 노출 높이가 아니다.

런타임에는 위 상판 정점을 현재 PhysX base link pose로 변환하여 평면을 맞춘다.
현재 bread visual world AABB 중심의 XY를 평면식에 대입한 Z가 z_rim이다.
슬롯 개구부에는 면이 없으므로, 둘레 상판 평면을 개구부 위로 연장하는 정의이다.
이는 평면 적합/연장 근사이며, 현재 asset의 평면 잔차는 수치 오차 수준이다.
기울어진 토스터도 최고점이 아닌 빵 중심 XY에서의 평면 높이를 사용한다.
면들이 0.01 mm 이내의 평면이 아니면 임의 근사로 진행하지 않고 실패한다.

빵 asset: source/cyclo_lab/data/objects/robodojo_make_toast/bread/object.usdz
시각 prim /World/visual (46487 vertices, subdivisionScheme=none).
collision/비가시/guide/proxy mesh를 제외하고 모든 실제 시각 mesh 정점을 읽는다.
런타임 composed USD의 계층 변환 및 root 포함 스케일을 rigid-body frame에 반영하고,
매 샘플의 실제 PhysX bread root pose를 모든 정점에 적용한다.
따라서 stale USD 월드 pose, root Z만의 추정, 고정 bread 높이, AABB 코너 대신
실제 시각 mesh 정점으로 world min/max Z를 구한다. 기울어짐도 그대로 반영된다.

H=z_top-z_bottom
E=clamp(z_top-z_rim,0,H)
노출률=100*E/H
이것은 월드 Z 수직 높이 비율이며 면적/부피/카메라 픽셀 노출률이 아니다.

실행 시나리오와 시각 정의
------------------------
1. 원래 v2 기본 layout, num_envs=1. scenario manifest를 적용하지 않는다.
   다른 빵은 원래 거치대에 남기고 bread_0 한 개만 슬롯0으로 초기 배치한다.
   bread_0 root를 toaster local [-0.003,slot_y+0.0056,0.14] m,
   상대 quaternion wxyz=[sqrt(0.5),sqrt(0.5),0,0]로 한 번 쓴다.
   slot_y는 슬롯0 -0.026455 m, 슬롯1 +0.0253585 m.
2. 1.2 s 물리 적재/자유 안정화. 최근 0.2 s 동안 기존 bread_in_slot 조건,
   다른 빵의 슬롯 부재, bread 속도<0.15 m/s, phase 0인지 확인한다.
   loaded_check 실제 RGB도 저장한다. 실패하면 정상 결과 없이 종료한다.
3. 레버 joint_1만 상한 위치로 한 번 입력하여 기존 래치를 트리거한다.
   캐리지 state/target은 측정 코드에서 덮어쓰지 않는다.
   이후 bread pose를 다시 쓰지 않고 기존 env.step과 ToastCycle.update를 진행한다.
   제로 relative IK와 기존 형식의 열린 그리퍼 action을 보낸다.
4. 기존 cycle.update 호출 직후 phase 변화가 일어난 그 순간을 기록한다.
   cycle.update는 env.step 내부의 물리 진행 전에 호출되므로 ③는 다음 물리 스텝 전
   최초 phase 4 상태이다. RGB도 그 시각에서 render만 갱신하고 물리를 전진시키지 않는다.
   ①는 phase 2->3 갱신 직전 상태, ②는 갱신 직후 상태. 두 기록은 같은 물리 시각과
   빵 pose를 가질 수 있으며 timer/phase만 달라진다.
5. 원래 scene.update 후마다 원래 physics dt로 샘플한다. ④/⑤는 ③부터
   정확히 0.5/1.0 s 후 물리 샘플이다. physics dt가 이를 표현하지 못하면 중단한다.
   시간 0은 각 슬롯 env.reset 후 진단 초기화 시점이며 초기 적재 대기 시간을 포함한다.
6. ②~⑤의 모든 물리 샘플/phase 경계에서 노출률 변화 및 샘플 최대값을 기록한다.
   연속 시간 전체의 해석적 최대값이라고 단정하지 않는다.
7. 사이클 시작 이후 슬롯 조건 위반, 다른 빵의 진입, 가열 증거 부재 또는 기존
   termination 발생 시 실행을 INVALID/FAILED로 취급하고 정상 요약값으로 집계하지 않는다.
   슬롯0이 정상 종료된 경우에만 env.reset하여 bread_0을 슬롯1에서 같은 방법으로 검사한다.
   bread_1..3의 노출률을 검사하거나 같은 결과로 일반화하지 않는다.

저장 파일
---------
실행별 새 디렉터리 results/에 status.json, provenance.json(코드/asset SHA256),
resolved_config.txt와 bread_0_slot_0/, bread_0_slot_1/을 만든다.
각 슬롯:
  trace.csv             초기 적재 포함 모든 물리 샘플 및 phase 전환
  rise_trace.csv        상승 시작부터 완료+1초까지 변화
  summary.csv/.txt/.json ①~⑤의 표, 주요 ③/⑤ 및 샘플 최대값
  events.json           초기 적재, 사이클 시작, 주요 이벤트 (실패 시에도 보존)
  geometry.json         사용 prim/면/변환/평면 정의
  body_vertices.npz     변환된 rigid-body local 시각 정점
  fixture.json, lever_input.json  진단 입력 기록
  03_first_phase4.rgb.png / 05_complete_plus_1p0s.rgb.png 실제 측면 RGB
  같은 이름의 .annotated.png 별도 설명 이미지 (윗면 평면선/빵 최고·최저 Z)
  .camera.json          카메라 투영 및 선의 월드/픽셀 좌표
  .world_vertices.npz  주요 시점 실제 world 정점

가려진 빵 하단에도 기하학적 높이선을 표시한다. 이것은 RGB에 보이는 실루엣 검출이 아니다.
raw RGB는 주석을 덧씌우지 않고 보존한다. 렌더 실패 시 성공한 이미지로 가장하지 않는다.

Ubuntu 터미널 전체 명령
----------------------
cd /home/mj/nrf_humanoid/cyclo_lab_mj
bash measurements/toast_exposure_20261109/run_measurement.sh

기존 scripts/run_mj.sh를 사용해 cyclo_lab_mj 프로젝트의 별도 transient container에서
실행한다. 원본 cyclo_lab 또는 기존 프로세스에 exec/stop/kill하지 않는다.
환경 설정 파일, task 소스, 기존 로그, commit/push는 변경하지 않는다.
렌더용 카메라 추가와 단일 env 실행 외에 물리/타이밍/성공 조건을 변경하지 않는다.
launch 로그도 measurements/toast_exposure_20261109/runs/ 아래 새 폴더에만 저장한다.
Docker/GPU 사용 권한이 있는 Ubuntu 터미널에서 실행해야 한다.

검증
----
verify_geometry.py를 실제 pinned USD에 실행하여 정점/상판 면을 확인했다.
임의 기울어진 pose와 독립 Gf 변환 비교, 비균일 root scale 및 child transform,
기울어진 평면의 중심 XY 평가, clamp 0/100% 검증 통과.
Python 구문 검사 통과. PhysX, 적재 성공, phase 도달 및 RGB 캡처는 아직 미검증.
