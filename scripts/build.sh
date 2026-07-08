#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/humble/setup.bash
if [[ ! -d "$ROOT/ros2_ws/src" ]] || ! find "$ROOT/ros2_ws/src" -name package.xml -print -quit | grep -q .; then
  echo "LubanVision ROS 2 packages have not been created yet."
  exit 0
fi
cd "$ROOT/ros2_ws"
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo
