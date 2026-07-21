# M17 single-axis control result

## Goal

Connect target validation, PID, target-loss state handling, provisional angle
mapping, and the bounded RK3588 PWM driver without expanding the M16 range.

## Results

- Mac, WSL, and RK were reachable after the RK was powered on. The RK exposed
  ROS 2 Humble, colcon, `/dev/video1`, and `pwmchip3`.
- The new controller rejects invalid, wrong-target, stale, and future samples;
  clamps nominal angle to 85-95 degrees; holds after loss; then returns slowly.
- The ROS hardware node starts disabled and did not export PWM during its
  default-disabled smoke test. Motion requires an explicit Boolean enable.
- WSL and RK full-workspace builds and tests each completed with 90 tests,
  0 errors, 0 failures, and 0 skipped tests.
- The bounded synthetic hardware run produced 143 state samples covering
  `tracking`, `holding`, `returning`, and `disabled`. Pulse range was
  1,463,998-1,500,000ns, reported faults were empty, the final command was
  centered/disabled, and PWM was unexported.
- The real camera and ArUco chain processed 900 frames at approximately 15 FPS
  with zero processing errors. The current scene contained no ID 23 marker, so
  the dynamic real-target portion of T-END-01 remains pending.

## Conclusion

M17 is in progress with the software and bounded hardware function chain
passed. The next and only M17 acceptance step is to place an ID 23 marker in
view, move it through the horizontal field, and record error statistics and
video. Long-duration servo operation and wider pulse limits remain outside this
short functional test until the power and mechanical-boundary work is closed.
