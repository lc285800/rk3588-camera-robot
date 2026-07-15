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

"""ROS-independent ArUco target detection."""

from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np


Corner = Tuple[float, float]


@dataclass(frozen=True)
class DetectionResult:
    """Describe one requested marker detection in image coordinates."""

    visible: bool
    target_id: int
    corners: Tuple[Corner, ...]
    center_x_px: float
    center_y_px: float
    error_x_px: float
    error_y_px: float
    error_x_norm: float
    error_y_norm: float
    area_px2: float
    confidence: float


def _not_visible() -> DetectionResult:
    """Return the safe result used when the requested target is absent."""
    return DetectionResult(
        visible=False,
        target_id=-1,
        corners=(),
        center_x_px=0.0,
        center_y_px=0.0,
        error_x_px=0.0,
        error_y_px=0.0,
        error_x_norm=0.0,
        error_y_norm=0.0,
        area_px2=0.0,
        confidence=0.0,
    )


def _dictionary(dictionary_name: str):
    """Resolve an OpenCV predefined ArUco dictionary by name."""
    dictionary_id = getattr(cv2.aruco, dictionary_name, None)
    if dictionary_id is None or not dictionary_name.startswith("DICT_"):
        raise ValueError(f"Unsupported ArUco dictionary: {dictionary_name}")
    return cv2.aruco.getPredefinedDictionary(dictionary_id)


def detect_target(
    image: np.ndarray,
    target_id: int,
    dictionary_name: str = "DICT_4X4_50",
) -> DetectionResult:
    """Detect one marker ID and calculate its center and image-center error."""
    if image is None or image.size == 0:
        raise ValueError("image must be a non-empty array")
    if image.ndim not in (2, 3):
        raise ValueError("image must be grayscale or color")

    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = cv2.aruco.detectMarkers(gray, _dictionary(dictionary_name))
    if ids is None:
        return _not_visible()

    matched_index: Optional[int] = None
    for index, marker_id in enumerate(ids.flatten()):
        if int(marker_id) == target_id:
            matched_index = index
            break
    if matched_index is None:
        return _not_visible()

    points = corners[matched_index].reshape(4, 2).astype(np.float64)
    center = points.mean(axis=0)
    area = abs(float(cv2.contourArea(points.astype(np.float32))))
    height, width = gray.shape[:2]
    error_x = float(center[0] - width / 2.0)
    error_y = float(center[1] - height / 2.0)

    return DetectionResult(
        visible=True,
        target_id=target_id,
        corners=tuple((float(x), float(y)) for x, y in points),
        center_x_px=float(center[0]),
        center_y_px=float(center[1]),
        error_x_px=error_x,
        error_y_px=error_y,
        error_x_norm=error_x / (width / 2.0),
        error_y_norm=error_y / (height / 2.0),
        area_px2=area,
        confidence=1.0,
    )
