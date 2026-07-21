# M16 extended handheld calibration

## Confirmed observations

| Pulse | User-observed position | Confidence |
|---:|---:|---|
| 1.00ms | approximately 0 degrees | visual, short hold |
| 1.90ms | approximately 90 degrees | isolated 8-second confirmation |
| 2.50ms | approximately 150 degrees | visual, short hold |

At 1.20ms, 1.80ms, 2.00ms, 2.20ms, and 2.40ms the servo continued to move
to distinct fixed positions, stopped, and returned when commanded. The user
reported no abnormal vibration at the incremental probes. This behavior
confirms a positional servo rather than a 360-degree continuous-rotation servo.

## Corrections

The earlier 1.45/1.50/1.55ms mapping established direction only; its
85/90/95-degree labels were not physical measurements. A later assumption that
1.75ms was 90 degrees was also rejected by observation. The isolated 1.90ms
test is the current center-angle fact.

No 180-degree position was measured. The tested maximum of 2.50ms appeared to
be about 150 degrees, so the device must not be documented as reaching 180
degrees under the tested command range.

## Operational decision

Automatic tracking remains deliberately narrow: 1.85-1.95ms, nominally
85-95 degrees around the observed 1.90ms center. The wider 1.00-2.50ms range is
evidence from short handheld calibration only and is not an automatic-motion
range. Exact angles and long-term endpoint safety still require a protractor,
the final power arrangement, and a mechanically mounted camera.

After updating the defaults and regression expectations, WSL and RK each
reported 90 tests, 0 errors, 0 failures, and 0 skipped tests. RK PWM was still
unexported after the regression.
