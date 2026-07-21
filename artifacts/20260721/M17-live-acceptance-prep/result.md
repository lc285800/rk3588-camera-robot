# M17 live acceptance preparation

## Outcome

- Generated a deterministic 1000x1000 PNG for `DICT_4X4_50` marker ID 23.
  OpenCV detected exactly ID 23 when the generated asset was read back.
- Captured the current real camera view. The image is visibly sideways/upward,
  so the camera horizontal image axis should be aligned with the mechanical Pan
  axis before enabling the visual loop.
- Added a root-only RK acceptance script that starts camera, detector, tracking,
  metrics, and rosbag in exact process groups. It refuses an already-exported
  PWM channel and requires five consecutive detections before enabling motion.
- The no-marker test timed out after three seconds as designed. Tracking was
  never enabled, every started process exited, and PWM remained unexported.

## Remaining M17 action

Mount the camera upright relative to the Pan axis, display or print the supplied
ID 23 marker, then run `scripts/m17_live_acceptance.sh 20 30` on the RK. Move the
marker slowly left and right during the 20-second enabled window. The output
directory will contain the rosbag, node logs, and JSON error/PWM metrics needed
for final M17 acceptance.
