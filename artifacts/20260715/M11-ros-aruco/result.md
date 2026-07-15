# M11 ROS ArUco Result

## Outcome

PASS. The node publishes correct target observations and debug images, preserves source timestamps,
and processes the real RK camera stream at 15 FPS after DDS discovery completes.

## Functional verification

- Deterministic ROS integration published marker ID 23 at 640x480.
- Received 61 valid observations and 4 valid debug images in 10.63 seconds.
- Target ID, status, error direction, dimensions, encoding, frame ID, seconds, and unique nanosecond
  sequence checks passed; `bad=0`.
- WSL and RK each passed all 11 unit/static tests.

## Real camera performance

- C++ V4L2 publisher: 225 frames, 15 FPS, `missed=0`.
- After discovery, detector counters increased by 30 every 2 seconds: 15 FPS.
- No marker was placed in the real camera view: detections=0 and errors=0, so no false positive occurred.
- Peak sampled detector resources: 77.5% CPU, 4.1% memory, 167568 KiB RSS.
- P95 callback latency was about 162 ms because every fifteenth callback also creates and serializes a
  640x480 BGR debug image. Ordinary samples before debug-image effects showed P95 around 22-30 ms.

## Problems and resolution

The failed attempts are retained in `logs/failed-attempts.txt`. The final independent-process topology
uses a Fast DDS Discovery Server, a normal camera client, a SUPER_CLIENT detector, and Reliable image
QoS. Node shutdown now handles `ExternalShutdownException` and stops the publisher before the detector.

## Remaining test scope

T-VIS-03 and T-VIS-05 pass. T-VIS-04 rosbag repeatability remains open. Motion-blur behavior in
T-VIS-02 also remains open and is not claimed as passed by M11.
