#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DURATION_SEC="${1:-20}"
ARM_TIMEOUT_SEC="${2:-30}"
RUN_DIR="${3:-$PROJECT_ROOT/artifacts/$(date +%Y%m%d)/M17-live-acceptance-run}"
HALF_RANGE_DEG="${4:-5}"
KP="${M17_KP:-4.0}"
OUTPUT_LIMIT="${M17_OUTPUT_LIMIT:-3.0}"
DELTA_LIMIT="${M17_DELTA_LIMIT:-0.5}"
DIRECTION="${M17_DIRECTION:--1.0}"
ROS_SETUP="/opt/ros/humble/setup.bash"
WORKSPACE_SETUP="$PROJECT_ROOT/ros2_ws/install/setup.bash"
PWM_PATH="/sys/class/pwm/pwmchip3/pwm0"
PROCESS_GROUPS=()

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run this acceptance script as root on the LubanCat-5." >&2
  exit 2
fi
if [[ ! "$DURATION_SEC" =~ ^[1-9][0-9]*$ ]] || \
   [[ ! "$ARM_TIMEOUT_SEC" =~ ^[1-9][0-9]*$ ]] || \
   [[ ! "$HALF_RANGE_DEG" =~ ^[1-9][0-9]*$ ]] || \
   (( HALF_RANGE_DEG > 30 )); then
  echo "Durations and half range must be positive integers; half range <= 30." >&2
  exit 2
fi
if [[ ! -f "$ROS_SETUP" || ! -f "$WORKSPACE_SETUP" ]]; then
  echo "ROS 2 or the built LubanVision workspace is missing." >&2
  exit 2
fi
if [[ ! -e /dev/video1 || ! -d /sys/class/pwm/pwmchip3 ]]; then
  echo "Camera /dev/video1 or pwmchip3 is unavailable." >&2
  exit 2
fi
if [[ -e "$PWM_PATH" ]]; then
  echo "PWM channel is already exported; refusing to take ownership." >&2
  exit 2
fi
if ps -eo args= | grep -E \
  'ros2 run lubanvision_(camera_cpp|vision|hardware)' | grep -v grep >/dev/null; then
  echo "A LubanVision runtime process is already active; stop it first." >&2
  exit 2
fi

set +u
# shellcheck disable=SC1090
source "$ROS_SETUP"
# shellcheck disable=SC1090
source "$WORKSPACE_SETUP"
set -u
export ROS_DOMAIN_ID=20
MIN_ANGLE_DEG=$((90 - HALF_RANGE_DEG))
MAX_ANGLE_DEG=$((90 + HALF_RANGE_DEG))
MIN_PULSE_NS=$((1900000 - HALF_RANGE_DEG * 10000))
MAX_PULSE_NS=$((1900000 + HALF_RANGE_DEG * 10000))
mkdir -p "$RUN_DIR/logs"

stop_group() {
  local group_pid="$1"
  kill -INT -- "-$group_pid" 2>/dev/null || true
}

cleanup() {
  local group_pid
  set +e
  timeout 3s ros2 topic pub -r 5 -t 3 -w 1 \
    /tracking/enabled std_msgs/msg/Bool \
    '{data: false}' >/dev/null 2>&1 || true
  sleep 1
  for group_pid in "${PROCESS_GROUPS[@]}"; do
    stop_group "$group_pid"
  done
  for group_pid in "${PROCESS_GROUPS[@]}"; do
    wait "$group_pid" 2>/dev/null || true
  done
  if [[ -e "$PWM_PATH" ]]; then
    echo 0 > "$PWM_PATH/enable" 2>/dev/null || true
    echo 0 > /sys/class/pwm/pwmchip3/unexport 2>/dev/null || true
  fi
  if [[ -e "$PWM_PATH" ]]; then
    echo "WARNING: PWM cleanup requires manual inspection." >&2
  else
    echo "PWM cleanup: OK"
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

setsid ros2 run lubanvision_camera_cpp v4l2_camera_publisher --ros-args \
  -p device:=/dev/video1 -p width:=640 -p height:=480 \
  -p fps:=15.0 -p reliability:=reliable \
  >"$RUN_DIR/logs/camera.txt" 2>&1 &
PROCESS_GROUPS+=("$!")

setsid ros2 run lubanvision_vision aruco_detector --ros-args \
  -p target_id:=23 -p publish_debug_image:=true \
  -p debug_image_every_n:=15 \
  >"$RUN_DIR/logs/aruco.txt" 2>&1 &
PROCESS_GROUPS+=("$!")

setsid ros2 run lubanvision_hardware pan_tracking --ros-args \
  -p min_angle_deg:="${MIN_ANGLE_DEG}.0" \
  -p center_angle_deg:=90.0 \
  -p max_angle_deg:="${MAX_ANGLE_DEG}.0" \
  -p min_pulse_ns:="$MIN_PULSE_NS" \
  -p center_pulse_ns:=1900000 \
  -p max_pulse_ns:="$MAX_PULSE_NS" \
  -p kp:="$KP" \
  -p output_limit:="$OUTPUT_LIMIT" \
  -p delta_limit:="$DELTA_LIMIT" \
  -p direction:="$DIRECTION" \
  >"$RUN_DIR/logs/tracking.txt" 2>&1 &
PROCESS_GROUPS+=("$!")

setsid ros2 bag record -o "$RUN_DIR/rosbag" \
  /camera/image_raw /target/observation /target/debug_image \
  /tracking/enabled /gimbal/state \
  >"$RUN_DIR/logs/rosbag.txt" 2>&1 &
BAG_GROUP="$!"
PROCESS_GROUPS+=("$BAG_GROUP")

sleep 3
echo "Waiting up to ${ARM_TIMEOUT_SEC}s for five consecutive ID 23 detections."
echo "Keep the marker visible and remove hands/cables from the gimbal path."
echo "Tracking range: ${MIN_ANGLE_DEG}-${MAX_ANGLE_DEG} degrees."
echo "Control: kp=${KP}, output_limit=${OUTPUT_LIMIT}deg/s, delta_limit=${DELTA_LIMIT}."
echo "Direction: ${DIRECTION}."

python3 - "$ARM_TIMEOUT_SEC" <<'PY'
import sys
import time

import rclpy
from lubanvision_interfaces.msg import TargetObservation

timeout_sec = float(sys.argv[1])
rclpy.init()
node = rclpy.create_node("m17_arming_gate")
consecutive = 0

def callback(message):
    global consecutive
    valid = (
        message.target_id == 23
        and message.status == TargetObservation.STATUS_DETECTED
    )
    consecutive = consecutive + 1 if valid else 0

node.create_subscription(TargetObservation, "/target/observation", callback, 10)
deadline = time.monotonic() + timeout_sec
while consecutive < 5 and time.monotonic() < deadline:
    rclpy.spin_once(node, timeout_sec=0.2)
node.destroy_node()
rclpy.shutdown()
if consecutive < 5:
    raise SystemExit("arming failed: five consecutive detections not received")
print("Arming gate: OK")
PY

setsid python3 - "$DURATION_SEC" <<'PY' \
  >"$RUN_DIR/logs/metrics.json" 2>"$RUN_DIR/logs/metrics-error.txt" &
import json
import math
import statistics
import sys
import time

import rclpy
from lubanvision_interfaces.msg import TargetObservation
from std_msgs.msg import String

duration_sec = float(sys.argv[1])
rclpy.init()
node = rclpy.create_node("m17_acceptance_metrics")
errors = []
states = []
pulses = []
faults = []

def on_observation(message):
    if (message.target_id == 23
            and message.status == TargetObservation.STATUS_DETECTED
            and math.isfinite(message.error_x_norm)):
        errors.append(float(message.error_x_norm))

def on_state(message):
    state = json.loads(message.data)
    states.append(state["state"])
    if state["pulse_ns"] is not None:
        pulses.append(int(state["pulse_ns"]))
    if state["fault"]:
        faults.append(state["fault"])

node.create_subscription(
    TargetObservation, "/target/observation", on_observation, 10
)
node.create_subscription(String, "/gimbal/state", on_state, 10)
deadline = time.monotonic() + duration_sec
while time.monotonic() < deadline:
    rclpy.spin_once(node, timeout_sec=0.1)
result = {
    "detected_samples": len(errors),
    "mean_abs_error_x_norm": (
        statistics.fmean(abs(error) for error in errors) if errors else None
    ),
    "max_abs_error_x_norm": (
        max(abs(error) for error in errors) if errors else None
    ),
    "min_error_x_norm": min(errors) if errors else None,
    "max_error_x_norm": max(errors) if errors else None,
    "initial_mean_error_x_norm": (
        statistics.fmean(errors[:10]) if errors else None
    ),
    "final_mean_error_x_norm": (
        statistics.fmean(errors[-10:]) if errors else None
    ),
    "initial_mean_abs_error_x_norm": (
        statistics.fmean(abs(error) for error in errors[:10])
        if errors else None
    ),
    "final_mean_abs_error_x_norm": (
        statistics.fmean(abs(error) for error in errors[-10:])
        if errors else None
    ),
    "states": sorted(set(states)),
    "pulse_min_ns": min(pulses) if pulses else None,
    "pulse_max_ns": max(pulses) if pulses else None,
    "faults": sorted(set(faults)),
}
print(json.dumps(result, indent=2, sort_keys=True))
node.destroy_node()
rclpy.shutdown()
PY
METRICS_GROUP="$!"
PROCESS_GROUPS+=("$METRICS_GROUP")

ros2 topic pub -r 5 -t 5 -w 2 \
  /tracking/enabled std_msgs/msg/Bool '{data: true}'
python3 - <<'PY'
import json
import time

import rclpy
from std_msgs.msg import String

rclpy.init()
node = rclpy.create_node("m17_enable_confirmation")
enabled = False

def callback(message):
    global enabled
    enabled = enabled or bool(json.loads(message.data)["enabled"])

node.create_subscription(String, "/gimbal/state", callback, 10)
deadline = time.monotonic() + 3.0
while not enabled and time.monotonic() < deadline:
    rclpy.spin_once(node, timeout_sec=0.1)
node.destroy_node()
rclpy.shutdown()
if not enabled:
    raise SystemExit("tracking enable confirmation timed out")
print("Tracking enable confirmation: OK")
PY
echo "Tracking enabled for ${DURATION_SEC}s. Move ID 23 slowly left and right."
sleep "$DURATION_SEC"
ros2 topic pub -r 5 -t 3 -w 1 \
  /tracking/enabled std_msgs/msg/Bool '{data: false}'
wait "$METRICS_GROUP" || true
sleep 1
test ! -e "$PWM_PATH"
stop_group "$BAG_GROUP"
wait "$BAG_GROUP" 2>/dev/null || true
ros2 bag info "$RUN_DIR/rosbag" > "$RUN_DIR/logs/rosbag-info.txt"
echo "Acceptance capture complete: $RUN_DIR"
