#!/usr/bin/env bash
# A separate transient container, with checkout-relative mounts and source imports.
set -euo pipefail
MJ_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$MJ_ROOT"
MJ_DOCKER_OPTIONS=()
if [[ "${1:-}" == "--gui" ]]; then
  shift
  : "${DISPLAY:?Set DISPLAY to the active desktop display}"
  MJ_XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
  if [[ ! -f "$MJ_XAUTHORITY" ]]; then
    echo "Xauthority file not found: $MJ_XAUTHORITY; set XAUTHORITY to your desktop cookie file." >&2
    exit 1
  fi
  MJ_DOCKER_OPTIONS+=(--env "DISPLAY=$DISPLAY" --env XAUTHORITY=/tmp/mj.xauthority
    --env HEADLESS=0 --env LIVESTREAM=0
    --volume /tmp/.X11-unix:/tmp/.X11-unix:ro
    --volume "$MJ_XAUTHORITY:/tmp/mj.xauthority:ro")
fi
exec docker compose --project-name cyclo_lab_mj --env-file docker/.env.base \
  -f docker/docker-compose.yaml -f docker/compose.mj.yaml --profile base \
  run --rm --no-deps "${MJ_DOCKER_OPTIONS[@]}" -w /workspace/cyclo_lab cyclo_lab \
  /isaac-sim/python.sh scripts/tools/mj_python.py "$@"
