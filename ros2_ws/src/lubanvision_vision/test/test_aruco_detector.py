# Copyright 2026 lc285800
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the ROS-independent ArUco detector."""

import cv2
import numpy as np
import pytest

from lubanvision_vision.aruco_detector import detect_target


MARKER_ID = 23
MARKER_SIZE = 160
TOP = 120
LEFT = 360


def make_scene(marker_id=MARKER_ID):
    """Create a reproducible 640x480 image containing one marker."""
    scene = np.full((480, 640, 3), 255, dtype=np.uint8)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.drawMarker(dictionary, marker_id, MARKER_SIZE)
    scene[TOP:TOP + MARKER_SIZE, LEFT:LEFT + MARKER_SIZE] = cv2.cvtColor(
        marker, cv2.COLOR_GRAY2BGR
    )
    return scene


def test_detects_target_id_corners_and_errors():
    """The requested marker exposes correct geometry and error direction."""
    result = detect_target(make_scene(), MARKER_ID)

    assert result.visible
    assert result.target_id == MARKER_ID
    assert len(result.corners) == 4
    assert result.center_x_px == pytest.approx(439.5, abs=1.0)
    assert result.center_y_px == pytest.approx(199.5, abs=1.0)
    assert result.error_x_px > 0.0
    assert result.error_y_px < 0.0
    assert result.error_x_norm == pytest.approx(
        result.error_x_px / 320.0
    )
    assert result.error_y_norm == pytest.approx(
        result.error_y_px / 240.0
    )
    assert result.area_px2 > 24000.0
    assert result.confidence == 1.0


def test_blank_image_is_not_visible():
    """A blank frame must not produce a target."""
    result = detect_target(np.full((480, 640), 255, dtype=np.uint8), MARKER_ID)

    assert not result.visible
    assert result.target_id == -1
    assert result.confidence == 0.0


def test_non_target_id_is_not_visible():
    """A valid marker with another ID must not select the target."""
    result = detect_target(make_scene(marker_id=7), MARKER_ID)

    assert not result.visible
    assert result.target_id == -1


def test_half_occluded_target_is_not_visible():
    """A marker with half its payload hidden must not drive tracking."""
    scene = make_scene()
    scene[TOP:TOP + MARKER_SIZE, LEFT:LEFT + MARKER_SIZE // 2] = 255

    result = detect_target(scene, MARKER_ID)

    assert not result.visible
    assert result.target_id == -1


def test_rejects_invalid_input_and_dictionary():
    """Invalid inputs fail explicitly instead of becoming false detections."""
    with pytest.raises(ValueError, match="non-empty"):
        detect_target(np.array([], dtype=np.uint8), MARKER_ID)
    with pytest.raises(ValueError, match="Unsupported"):
        detect_target(make_scene(), MARKER_ID, "DICT_NOT_REAL")
