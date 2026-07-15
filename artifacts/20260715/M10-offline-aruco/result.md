# M10 Offline ArUco Detection Result

## Objective

Implement a ROS-independent detector and verify target ID, four corners, geometry, blank input,
non-target markers, and partial occlusion with reproducible static images.

## Steps and results

1. Checked the clean `main` branch and both target devices.
2. Verified OpenCV 4.5.4 and `cv2.aruco` on WSL x86_64 and RK aarch64.
3. Added `aruco_detector.py` with dictionary validation, target-ID selection, center, pixel error,
   normalized error, polygon area, and a safe not-visible result.
4. Added generated 640x480 tests for marker ID 23, blank input, marker ID 7, 50% occlusion, empty
   input, and an invalid dictionary name.
5. Built and tested on both target architectures.

WSL result:

```text
collected 8 items
test/test_aruco_detector.py .....
8 passed, 2 warnings in 1.02s
Summary: 8 tests, 0 errors, 0 failures, 0 skipped
```

RK result:

```text
collected 8 items
test/test_aruco_detector.py .....
8 passed, 2 warnings in 1.36s
Summary: 8 tests, 0 errors, 0 failures, 0 skipped
```

The detector and test files had identical SHA-256 values on Mac, WSL, and RK:

```text
aruco_detector.py       71f5191459e9ee43c9e9a4667a06dbfc6326cb677fe679eb013a2c307e695c0f
test_aruco_detector.py  82a152e0dac9c2693cc82bec70998c1653133649a98b6bf74150d8123f1100b4
```

## Issues and decisions

- Mac did not have `cv2`. This is not blocking because the documented architecture assigns ROS 2
  builds and tests to WSL and RK; no Mac package installation was performed.
- Both targets emitted two `SelectableGroups` deprecation warnings from Flake8 dependency metadata.
  All static checks passed; this is external tooling output and requires no project-code change.
- OpenCV ArUco 4.5.4 does not expose a calibrated detection probability. M10 uses confidence `1.0`
  for an accepted target and `0.0` otherwise. A future calibrated confidence metric must be defined
  separately before consumers interpret intermediate values.

## Conclusion

PASS. M10 is complete. T-VIS-01 passed; the static portions of T-VIS-02 passed. Motion blur and
continuous-control behavior remain for ROS-stream validation. The next task is M11.
