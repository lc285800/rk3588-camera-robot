#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 -m compileall -q "$ROOT/tools"
for script in "$ROOT"/scripts/*.sh; do
  bash -n "$script"
done
if command -v colcon >/dev/null && [[ -d "$ROOT/ros2_ws/src" ]] && \
   find "$ROOT/ros2_ws/src" -name package.xml -print -quit | grep -q .; then
  cd "$ROOT/ros2_ws"; colcon test; colcon test-result --verbose
fi
