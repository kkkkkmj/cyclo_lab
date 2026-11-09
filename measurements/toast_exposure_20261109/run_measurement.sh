#!/usr/bin/env bash
set -euo pipefail
EXPOSURE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd "$EXPOSURE_ROOT"
mkdir -p measurements/toast_exposure_20261109/runs
EXPOSURE_RUN="$(mktemp -d measurements/toast_exposure_20261109/runs/run_$(date +%Y%m%d_%H%M%S)_XXXXXX)"
printf 'New exposure output: %s/%s\n' "$EXPOSURE_ROOT" "$EXPOSURE_RUN"
bash scripts/run_mj.sh measurements/toast_exposure_20261109/measure_exposure.py \
  --headless --device cuda:0 --output "$EXPOSURE_RUN/results" \
  2>&1 | tee "$EXPOSURE_RUN/launcher.log"
