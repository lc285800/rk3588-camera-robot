# M06 Camera Smoke Recovery

## Goal

Continue M06 by confirming current device availability and replacing fragile inline topic-rate checks with repeatable package code.

## Device Check

- `192.168.2.100` responded to ping.
- `192.168.2.120` responded to ping.
- WSL SSH port `2222` was open.
- RK SSH port `22` was open.
- SSH public key authentication was configured for both WSL and RK.
- BatchMode SSH login now works for both WSL and RK.

## Code Changes

- Added `image_rate_probe`, a lightweight `sensor_data` QoS subscriber for `/camera/image_raw`.
- Added publisher-side frame statistics to `camera_publisher` through `stats_interval_sec`.
- Added `lubanvision_camera_cpp` with a C++ V4L2 YUYV camera publisher and C++ image-rate probe.
- Corrected `config/platforms/lubancat5.yaml` to use the verified USB camera device `/dev/video1`.

## Local Verification

- `python3 -m compileall -q tools ros2_ws/src/lubanvision_vision/lubanvision_vision`: pass.
- `bash -n scripts/build.sh`: pass.
- `bash -n scripts/test.sh`: pass.
- `git diff --check`: pass.

## RK Verification

- `colcon build --symlink-install --packages-select lubanvision_vision`: pass.
- `colcon build --symlink-install --packages-select lubanvision_camera_cpp`: pass.
- `colcon test --packages-select lubanvision_vision`: pass after removing macOS AppleDouble `._*` files generated during tar transfer.
- `colcon test --packages-select lubanvision_vision lubanvision_camera_cpp`: pass.
- `colcon test-result --verbose`: 3 tests, 0 errors, 0 failures, 0 skipped.
- SIGINT shutdown regression: pass, no Python traceback and no duplicate shutdown error in camera logs.

## Camera Probe Results

- 15 FPS command: publisher reported about 3.71-6.75 FPS; probe received 5 frames in a 20 second run.
- 5 FPS command: publisher stabilized at 5 FPS; probe received 2 frames in 15 seconds.
- 5 FPS longer run: publisher stabilized at 5 FPS; probe received 4 frames in 40 seconds.
- V4L2 direct capture remained healthy at about 30 FPS.
- OpenCV direct read and read plus `tobytes()` remained about 28 FPS.
- Python `sensor_msgs/Image.data` assignment for a 921600 byte image measured about 6.9 msg/s, explaining the Python raw image ceiling.
- C++ V4L2 publisher with reliable QoS passed M06: run 1 published 15 FPS and received 224 frames in 14.87s (15.06 FPS), run 2 published 15 FPS and received 225 frames in 14.91s (15.09 FPS), with `bad_frames=0`.

## Current Blocker

M06 is complete. M07 should run the same C++ publisher/probe path for 30 minutes and add CPU/memory/resource sampling.

## Remaining M06 Regression

Run these after SSH authentication is available on RK:

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=20
cd /root/lubanvision/ros2_ws
colcon build --symlink-install --packages-select lubanvision_vision
source install/setup.bash
ros2 run lubanvision_vision camera_publisher --ros-args \
  -p video_device:=/dev/video1 \
  -p image_width:=640 \
  -p image_height:=480 \
  -p frame_rate:=15.0 \
  -p pixel_format:=MJPG \
  -p stats_interval_sec:=5.0
```

In another sourced ROS shell:

```bash
ros2 run lubanvision_vision image_rate_probe --ros-args \
  -p topic:=/camera/image_raw \
  -p duration_sec:=20.0 \
  -p expected_width:=640 \
  -p expected_height:=480 \
  -p expected_encoding:=bgr8
```

M06 passed. Continue with M07 30 minute camera stability testing.
