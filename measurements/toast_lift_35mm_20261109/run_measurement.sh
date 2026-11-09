#!/usr/bin/env bash
set -euo pipefail
LIFT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd "$LIFT_ROOT"
mkdir -p measurements/toast_lift_35mm_20261109/runs
LIFT_RUN="$(mktemp -d measurements/toast_lift_35mm_20261109/runs/run_$(date +%Y%m%d_%H%M%S)_XXXXXX)"
printf 'New +35 mm measurement folder: %s/%s\n' "$LIFT_ROOT" "$LIFT_RUN"
bash scripts/run_mj.sh measurements/toast_exposure_20261109/measure_exposure.py \
  --headless --device cuda:0 --output "$LIFT_RUN/results" \
  2>&1 | tee "$LIFT_RUN/launcher.log"
