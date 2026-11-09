# 원본 비교 기록

비교 대상은 문서 통합 직전 `87d971f1cf8ec5799c672f0ee8038c4319f1ab8d`다.
기준은 `badajhong/cyclo_lab`의 **`5f5086d11f664494119086de30a9e925b12022ad`**
(`add readme of toast`, author/committer badajhong, 2026-11-02)로 고정한다.

## 기준 근거와 한계

- 최초 작업 커밋 `761c8ac77ccbe7841966e535fa7202d7be83c7a1`의 직접 부모가 이 기준 커밋이다.
- 로컬 `toast-scenarios-100` reflog의 최초 항목은 `5f5086d branch: Created from HEAD`다.
  이후 기존 시나리오 작업을 거쳐 `29c04a5`, Quest 정리 `87d971f`로 이어진다.
- 로컬 `upstream`은 `https://github.com/badajhong/cyclo_lab.git`이다.
  현재 로컬 upstream/main 및 merge-base도 같은 커밋이나, 이 가변 ref를 비교 정의로 사용하지 않는다.
- 별도 연구실 작업 디렉터리는 읽거나 수정하지 않았다. 제공 당시 미커밋 파일의 존재/내용,
  원격 저장소의 현재 main 상태는 이 증거로 확정할 수 없다.

재확인 명령(네트워크 불필요):

```bash
git show -s --format=fuller 5f5086d11f664494119086de30a9e925b12022ad
git show -s --format='%H %P %s' 761c8ac77ccbe7841966e535fa7202d7be83c7a1
git diff --name-status 5f5086d11f664494119086de30a9e925b12022ad 87d971f1cf8ec5799c672f0ee8038c4319f1ab8d
```

## 기존 README 보존

| 파일 | 기준 대비 통합 전 상태 | 이번 통합 |
|---|---|---|
| README.md | Git blob 동일, 변경 없음 | 수정/삭제하지 않음 |
| README_TOAST.md | 113줄 추가, 삭제 없음. Quest 진입 안내 및 시나리오 실행 등 추가 | 현재는 삭제, 실행 안내는 Changes/시나리오 안내로 통합 |

현재 공유 진입점은 [Changes](../../CHANGES.md)와 [시나리오 안내](../../scenario_delivery/README.md)다.
루트 README_TOAST.md 및 README_TOAST_QUEST.md는 삭제하며 안내용 stub을 남기지 않는다.
과거 6개 세부 README의 측정 기록은 history에 보존한다.

## README 외 실제 변경 분야

통합 전 기준 diff는 **추가 218개, 수정 15개, 삭제 0개**다.
README.md는 동일하고 수정 15개 중 README_TOAST.md가 1개다.
전체 파일별 상태는 [BASELINE_FILES.csv](BASELINE_FILES.csv)에 보존한다.

| 분야 | 주요 파일 및 실제 변화 |
|---|---|
| 환경·성공 판정 | `config/ffw_bg2/{assets,bimanual_env,bimanual_env_cfg,bimanual_mdp,bread_geometry,env_cfg,mdp,scene,toast_cycle}.py` 수정. 새 rack pose/참조, 90% 진입·4초 가열, +35 mm, 동일 빵 ID 성공·20 mm 중심 판정, master 속도. `lever_indicator.py`, `toast_parameters.py` 추가 |
| 시나리오 | `config/ffw_bg2/scenarios.py`, `scripts/tools/view_make_toast_scenario.py` 및 생성·배치도·검증 도구 추가. `scenario_delivery/`의 기존 100개와 새 `v20261108_current_100/` 데이터·배정·설계·진단 보고서 추가 |
| Quest | `scripts/quest_diagnostic/`의 server.py/input.js/index.html/teleop_toast.py/control.py/hud.js 및 상태·미리보기·기록·접촉/성능 검사 도구 추가 |
| 기록·재생 | `scripts/imitation_learning/isaaclab_recorder/replay_demos.py`, `replay_video.py` 수정. 시나리오/가열 상태 복원, 검증·audit·gain 비교 도구 추가 |
| Asset | `source/cyclo_lab/data/objects/bread_slot/{rack.usda,bread_slot.usdz}` 추가. 원본 robot USD·공용 FFW_BG2.py 변경 없음. 기존 외부 물체 다운로더/asset manifest는 원본부터 존재 |
| 실행·저장소 | `docker/compose.mj.yaml`, `scripts/run_mj.sh`, `scripts/tools/mj_python.py` 추가. `.gitattributes`/`.gitignore` 수정. 기존 Dockerfile/기본 compose는 변경 없음 |
| 측정·검사 | `measurements/toast_exposure_20261109/`, `toast_lift_35mm_20261109/`의 도구·과거 보고서 추가. `scripts/tools/check_toast_cycle.py`의 가열 시간 참조 수정 및 CPU 테스트 추가 |
| 누락 의존 소스 복원 | `third_party/IsaacLab/source/isaaclab/isaaclab/utils/datasets/`의 `__init__.py`, `dataset_file_handler_base.py`, `episode_data.py`, `hdf5_dataset_file_handler.py` 추가. 기본 Git tree는 submodule gitlink 없이 소스를 포함 |

**정정:** 원본 v2는 상위 bimanual 설정에서 slave 100/4를 상속한다. 현재 v2의 추가 명시는
수치 변화가 아니다. 과거 README의 중간 soft-gain 2/0.5, 레버 기반 LED 실험은 원본 상태와 구분한다.
원본 cycle은 두 빵이 서로 다른 슬롯에 있어야 시작하며 LED 모듈은 없었다.

이번 커밋은 위 환경 기능을 다시 수정하지 않는다. 문서 이동·통합·링크와 비교 근거만 변경한다.
