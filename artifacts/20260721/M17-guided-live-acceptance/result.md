# M17 guided live tracking acceptance

## Outcome

Basic single-axis visual tracking passed. The phone marker was aligned using a
detection-only preview, tracking enable was explicitly confirmed from gimbal
state, and the user moved the marker only in response to timed instructions.

## Metrics

- 533 valid ID 23 detections during the guided control window.
- Mean absolute normalized X error: 0.05546.
- Final mean absolute normalized X error: 0.03414.
- Maximum absolute normalized X error during movement: 0.57891.
- PWM range: 1,836,836-1,900,000ns.
- States observed: disabled, tracking, holding, returning.
- Reported faults: none.
- Rosbag: 53.2 seconds, 2,524 messages, 664.6MiB on the RK.

The user confirmed that physical direction was correct and described the basic
following behavior as acceptable, while noting that response clarity still has
room for tuning. Response comfort is therefore deferred to the longer M20
stability/tuning work rather than overstating this result.

## Safety

The script published repeated disable messages, the tracking node reported PWM
release, the sysfs PWM channel was absent afterward, and no camera, detector,
tracker, metrics, or rosbag process remained.
