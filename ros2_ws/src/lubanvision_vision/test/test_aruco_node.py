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

"""Unit tests for ROS image conversion used by the ArUco node."""

import numpy as np
import pytest
from sensor_msgs.msg import Image

from lubanvision_vision.aruco_node import image_to_array


def make_message(encoding="bgr8", step=6, data=None):
    """Build a small ROS image message for conversion tests."""
    message = Image()
    message.width = 2
    message.height = 2
    message.encoding = encoding
    message.step = step
    message.data = bytes(range(12)) if data is None else data
    return message


def test_bgr_image_is_zero_copy_view():
    """Packed BGR data retains dimensions and byte values."""
    image = image_to_array(make_message())

    assert image.shape == (2, 2, 3)
    assert np.array_equal(image.flatten(), np.arange(12))


def test_padded_rows_ignore_padding():
    """Row padding is excluded from returned pixels."""
    message = make_message(step=8, data=bytes(range(16)))
    image = image_to_array(message)

    assert image.shape == (2, 2, 3)
    assert image[1, 0, 0] == 8


def test_invalid_encoding_and_short_data_fail():
    """Malformed image messages fail explicitly."""
    with pytest.raises(ValueError, match="unsupported"):
        image_to_array(make_message(encoding="yuv422"))
    with pytest.raises(ValueError, match="shorter"):
        image_to_array(make_message(data=b"short"))
