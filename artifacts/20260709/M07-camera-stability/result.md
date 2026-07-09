# M07 Camera Stability Partial Run

## Status

Paused by user request on 2026-07-09 before the planned 30 minute duration completed. The camera path was healthy before pause, and the user later confirmed this result should be accepted as M07 passing.

## Setup

- Host: RK LubanCat-5.
- Topic: `/camera/image_raw`.
- Publisher: `lubanvision_camera_cpp v4l2_camera_publisher`.
- Probe: `lubanvision_camera_cpp image_rate_probe`.
- Image: 640x480 `bgr8`.
- Rate: 15 FPS.
- QoS: reliable.
- Remote artifact path: `/root/lubanvision/artifacts/20260709/M07-camera-stability/`.

## Observed Result Before Pause

- Camera log reached `total=11700` frames with `missed=0`.
- Every logged 30 second window reported 450 frames and about 15.00 FPS.
- Corrected resource sampler showed camera CPU about 17.1%, camera memory about 0.6%, probe CPU about 1.1%, probe memory about 0.5%.
- Board temperature stayed around 37.0-38.8 C.
- No process remained after pause; `/dev/video1` was released.

## Conclusion

Partial run was normal. Per user acceptance on 2026-07-09, M07 is treated as passed and the project moves on to M08 cross-machine image validation.
