# M18 Hardware Fault Injection

M18 passed on the LubanCat-5 on 2026-07-22. All tests used the conservative
90-degree center. The observation-loss case published zero horizontal error, so
the servo command remained at the 1.90 ms center pulse.

## Results

- Observation producer exit: after fresh ID 23 observations stopped, the
  controller transitioned through `tracking`, `holding`, and `returning`.
  Every recorded command was 1,900,000 ns, faults were empty, and explicit
  disable released PWM.
- Camera disconnect: unbinding only USB interface `6-1:1.0` caused the running
  publisher to report `VIDIOC_DQBUF failed: No such device` and exit with code
  1. Rebinding restored `/dev/video1`; the restarted publisher delivered 15
  frames per one-second window at about 15 FPS with zero misses.
- Existing PWM consumer: an externally exported but disabled `pwm0` caused the
  tracking node to remain disabled and publish `PWM channel is already exported
  by another owner`. Ten repeated enable messages per second caused exactly one
  acquisition attempt. The foreign channel stayed disabled and was never
  taken over.

After the tests, `/dev/video1`, NVMe, and Ethernet were online; no LubanVision
runtime process remained; `/sys/class/pwm/pwmchip3/pwm0` did not exist.

## Code changes

- The C++ camera publisher now treats unrecoverable V4L2 errors as fatal and
  has a one-second no-frame watchdog with an explicit reconnect/restart message.
- The Pan tracking node latches enable requests and attempts hardware acquisition
  only once per false-to-true edge, preventing high-rate retry loops.

Raw logs and machine-readable state captures are in `logs/`.
