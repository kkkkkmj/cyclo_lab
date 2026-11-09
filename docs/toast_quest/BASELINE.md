# Baseline Comparison Record

The compared revision is `87d971f1cf8ec5799c672f0ee8038c4319f1ab8d`, immediately before document consolidation.
The baseline is fixed at **`5f5086d11f664494119086de30a9e925b12022ad`** in `badajhong/cyclo_lab`
(`add readme of toast`, author/committer badajhong, 2026-11-02).

## Baseline Evidence and Limitations

- The direct parent of the first development commit, `761c8ac77ccbe7841966e535fa7202d7be83c7a1`, is this baseline commit.
- The first local `toast-scenarios-100` reflog entry is `5f5086d branch: Created from HEAD`.
  Subsequent scenario work led to `29c04a5`, followed by Quest consolidation at `87d971f`.
- Local `upstream` is `https://github.com/badajhong/cyclo_lab.git`.
  Local upstream/main and merge-base currently point to the same commit, but this mutable ref does not define the comparison.
- The separate lab working directory was neither read nor modified. These records cannot establish the existence/content
  of uncommitted files at delivery or the remote repository's current main state.

Commands to recheck (no network required):

```bash
git show -s --format=fuller 5f5086d11f664494119086de30a9e925b12022ad
git show -s --format='%H %P %s' 761c8ac77ccbe7841966e535fa7202d7be83c7a1
git diff --name-status 5f5086d11f664494119086de30a9e925b12022ad 87d971f1cf8ec5799c672f0ee8038c4319f1ab8d
```

## Preservation of Existing READMEs

| File | Pre-consolidation state relative to baseline | Consolidation outcome |
|---|---|---|
| README.md | Identical Git blob, unchanged | Not modified/deleted |
| README_TOAST.md | 113 lines added, none deleted; added Quest entry guidance, scenario execution, etc. | Now deleted; execution guidance consolidated into Changes/scenario guide |

The current shared entry points are [Changes](../../CHANGES.md) and the [scenario guide](../../scenario_delivery/README.md).
Root README_TOAST.md and README_TOAST_QUEST.md are removed without navigation stubs.
Measurement records from the 6 former detailed READMEs are preserved in history.

## Actual Changes Beyond READMEs

The pre-consolidation baseline diff contains **218 additions, 15 modifications, and 0 deletions**.
README.md is identical; README_TOAST.md accounts for 1 of the 15 modified files.
Per-file status is preserved in [BASELINE_FILES.csv](BASELINE_FILES.csv).

| Area | Main files and actual changes |
|---|---|
| Environment/success criteria | Modified `config/ffw_bg2/{assets,bimanual_env,bimanual_env_cfg,bimanual_mdp,bread_geometry,env_cfg,mdp,scene,toast_cycle}.py`: new rack pose/reference, 90% activation, 4-second heating, +35 mm, same-bread-ID success, 20 mm center check, master velocity. Added `lever_indicator.py`, `toast_parameters.py` |
| Scenarios | Added `config/ffw_bg2/scenarios.py`, `scripts/tools/view_make_toast_scenario.py`, and generation/layout/validation tools. Added data/assignments/design/diagnostics for the existing 100 scenarios in `scenario_delivery/` and new `v20261108_current_100/` |
| Quest | Added server.py/input.js/index.html/teleop_toast.py/control.py/hud.js and status/preview/recording/contact/performance tools in `scripts/quest_diagnostic/` |
| Recording/replay | Modified `scripts/imitation_learning/isaaclab_recorder/replay_demos.py`, `replay_video.py`. Added scenario/heating-state restoration, validation/audit/gain comparison tools |
| Assets | Added `source/cyclo_lab/data/objects/bread_slot/{rack.usda,bread_slot.usdz}`. Original robot USD/shared FFW_BG2.py unchanged. External object downloader/asset manifest already existed in the baseline |
| Execution/repository | Added `docker/compose.mj.yaml`, `scripts/run_mj.sh`, `scripts/tools/mj_python.py`. Modified `.gitattributes`/`.gitignore`. Existing Dockerfile/base compose unchanged |
| Measurement/validation | Bread exposure ratio/rising-height tools and historical reports moved to local backup. Updated heating-time reference in `scripts/tools/check_toast_cycle.py` and added CPU tests |
| Missing dependency sources restored | Added `__init__.py`, `dataset_file_handler_base.py`, `episode_data.py`, `hdf5_dataset_file_handler.py` under `third_party/IsaacLab/source/isaaclab/isaaclab/utils/datasets/`. The base Git tree includes sources without submodule gitlinks |

**Correction:** Original v2 inherits slave gains of 100/4 from the parent bimanual configuration. Explicitly specifying them
in current v2 is not a numerical change. Historical intermediate soft gains of 2/0.5 and lever-based LED experiments differ from the baseline.
The original cycle required two slices in separate slots for activation and had no LED module.

This consolidation commit does not modify those environment features again; it changes only document organization, links, and comparison evidence.
