# M17 documentation synchronization

The repository overview, quick start, design, progress status, issue log, test
plan, execution playbook, and platform YAML were reviewed against the final M17
evidence.

Current documents now agree that:

- M17 basic single-axis visual tracking is complete.
- Physical direction is `-1`, established by stationary-target A/B data.
- The final guided run recorded 533 detections, mean absolute X error 0.0555,
  final error 0.0341, no fault, and complete PWM/process cleanup.
- The conservative 1.85-1.95ms default remains distinct from the explicitly
  validated 70-110 degree live-test profile.
- M15-M16 retain power-duration and protractor limitations.
- M18 hardware fault injection is the next and only implementation task.

Historical partial M17 rows remain for traceability but are explicitly marked
as superseded by the final guided acceptance.
