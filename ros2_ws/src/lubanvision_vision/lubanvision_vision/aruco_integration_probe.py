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

"""Publish deterministic ArUco images and validate M11 ROS outputs."""

import time

import cv2
from lubanvision_interfaces.msg import TargetObservation
import numpy as np
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import Image

from .aruco_node import ArucoNode, IMAGE_QOS


class IntegrationProbe(Node):
    """Exercise the detector through serialized ROS image messages."""

    def __init__(self):
        super().__init__("aruco_integration_probe")
        self._sequence = 0
        self._observations = 0
        self._debug_images = 0
        self._bad = 0
        self._observation_stamps = set()
        self._debug_stamps = set()
        self._started = time.monotonic()
        self._image = self._make_image()
        self._publisher = self.create_publisher(
            Image, "/camera/image_raw", IMAGE_QOS
        )
        self.create_subscription(
            TargetObservation, "/target/observation", self._on_observation, 10
        )
        self.create_subscription(
            Image,
            "/target/debug_image",
            self._on_debug_image,
            IMAGE_QOS,
        )
        self.create_timer(1.0 / 15.0, self._publish)
        self.create_timer(0.1, self._check_done)
        self.done = False

    @staticmethod
    def _make_image():
        image = np.full((480, 640, 3), 255, dtype=np.uint8)
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        marker = cv2.aruco.drawMarker(dictionary, 23, 160)
        image[120:280, 360:520] = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
        return image

    def _publish(self):
        message = Image()
        message.header.stamp.sec = 123
        message.header.stamp.nanosec = self._sequence
        message.header.frame_id = "m11_test_camera"
        message.height = 480
        message.width = 640
        message.encoding = "bgr8"
        message.step = 1920
        message.data = self._image.tobytes()
        self._publisher.publish(message)
        self._sequence += 1

    def _on_observation(self, message):
        self._observations += 1
        valid = (
            message.header.stamp.sec == 123
            and message.header.stamp.nanosec < self._sequence
            and message.header.stamp.nanosec not in self._observation_stamps
            and message.header.frame_id == "m11_test_camera"
            and message.target_id == 23
            and message.status == TargetObservation.STATUS_DETECTED
            and message.error_x_px > 0.0
            and message.error_y_px < 0.0
        )
        self._observation_stamps.add(message.header.stamp.nanosec)
        self._bad += int(not valid)

    def _on_debug_image(self, message):
        self._debug_images += 1
        valid = (
            message.header.stamp.sec == 123
            and message.header.stamp.nanosec < self._sequence
            and message.header.stamp.nanosec not in self._debug_stamps
            and message.header.frame_id == "m11_test_camera"
            and message.width == 640
            and message.height == 480
            and message.encoding == "bgr8"
        )
        self._debug_stamps.add(message.header.stamp.nanosec)
        self._bad += int(not valid)

    def _check_done(self):
        elapsed = time.monotonic() - self._started
        if self._observations >= 60 and self._debug_images >= 4:
            self.done = True
        elif elapsed > 12.0:
            self._bad += 1
            self.done = True

    def report(self):
        """Return a stable result line and whether all assertions passed."""
        elapsed = time.monotonic() - self._started
        passed = self.done and self._bad == 0
        return (
            passed,
            f"integration passed={passed} published={self._sequence} "
            f"observations={self._observations} debug={self._debug_images} "
            f"bad={self._bad} elapsed_sec={elapsed:.2f}",
        )


def main(args=None):
    """Run the deterministic M11 integration probe."""
    rclpy.init(args=args)
    detector = ArucoNode()
    probe = IntegrationProbe()
    executor = SingleThreadedExecutor()
    executor.add_node(detector)
    executor.add_node(probe)
    while rclpy.ok() and not probe.done:
        executor.spin_once(timeout_sec=0.1)
    passed, report = probe.report()
    print(report, flush=True)
    executor.remove_node(probe)
    executor.remove_node(detector)
    probe.destroy_node()
    detector.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
