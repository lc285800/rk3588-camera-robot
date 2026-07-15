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

"""ROS 2 node that publishes ArUco target observations and debug images."""

from collections import deque
import time

import cv2
from lubanvision_interfaces.msg import TargetObservation
import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image

from .aruco_detector import detect_target


IMAGE_QOS = QoSProfile(
    depth=10,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
)


def image_to_array(message):
    """Create an OpenCV-compatible view of a supported ROS image message."""
    channels = {"mono8": 1, "bgr8": 3, "rgb8": 3}.get(message.encoding)
    if channels is None:
        raise ValueError(f"unsupported image encoding: {message.encoding}")
    expected_step = message.width * channels
    if message.step < expected_step:
        raise ValueError("image step is smaller than its encoded row width")
    required = message.step * message.height
    if len(message.data) < required:
        raise ValueError("image data is shorter than height * step")

    rows = np.frombuffer(message.data, dtype=np.uint8, count=required).reshape(
        message.height, message.step
    )
    pixels = rows[:, :expected_step]
    if channels == 1:
        return pixels.reshape(message.height, message.width)
    image = pixels.reshape(message.height, message.width, channels)
    if message.encoding == "rgb8":
        return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    return image


class ArucoNode(Node):
    """Detect one configured ArUco marker from a ROS image stream."""

    def __init__(self):
        super().__init__("aruco_detector")
        self.declare_parameter("image_topic", "/camera/image_raw")
        self.declare_parameter("observation_topic", "/target/observation")
        self.declare_parameter("debug_image_topic", "/target/debug_image")
        self.declare_parameter("target_id", 23)
        self.declare_parameter("dictionary", "DICT_4X4_50")
        self.declare_parameter("publish_debug_image", True)
        self.declare_parameter("debug_image_every_n", 15)
        self.declare_parameter("stats_interval_sec", 5.0)

        self._target_id = int(self.get_parameter("target_id").value)
        self._dictionary = self.get_parameter("dictionary").value
        self._publish_debug = bool(
            self.get_parameter("publish_debug_image").value
        )
        self._debug_every_n = max(
            1, int(self.get_parameter("debug_image_every_n").value)
        )
        self._stats_interval = float(
            self.get_parameter("stats_interval_sec").value
        )
        self._frames = 0
        self._detections = 0
        self._errors = 0
        self._start = time.monotonic()
        self._latencies_ms = deque(maxlen=2048)

        observation_topic = self.get_parameter("observation_topic").value
        debug_topic = self.get_parameter("debug_image_topic").value
        self._observation_publisher = self.create_publisher(
            TargetObservation, observation_topic, 10
        )
        self._debug_publisher = self.create_publisher(
            Image, debug_topic, IMAGE_QOS
        )
        self.create_subscription(
            Image,
            self.get_parameter("image_topic").value,
            self._on_image,
            IMAGE_QOS,
        )
        self.create_timer(self._stats_interval, self._report_stats)

    def _on_image(self, message):
        started = time.perf_counter()
        try:
            image = image_to_array(message)
            result = detect_target(image, self._target_id, self._dictionary)
            observation = TargetObservation()
            observation.header = message.header
            observation.target_id = result.target_id
            observation.center_x_px = result.center_x_px
            observation.center_y_px = result.center_y_px
            observation.error_x_px = result.error_x_px
            observation.error_y_px = result.error_y_px
            observation.error_x_norm = result.error_x_norm
            observation.error_y_norm = result.error_y_norm
            observation.area_px2 = result.area_px2
            observation.confidence = result.confidence
            observation.status = (
                TargetObservation.STATUS_DETECTED
                if result.visible
                else TargetObservation.STATUS_NOT_VISIBLE
            )
            self._observation_publisher.publish(observation)
            self._frames += 1
            self._detections += int(result.visible)
            if self._publish_debug and self._frames % self._debug_every_n == 0:
                self._publish_debug_image(message, image, result)
        except (ValueError, cv2.error) as error:
            self._errors += 1
            self.get_logger().error(str(error))
        finally:
            self._latencies_ms.append((time.perf_counter() - started) * 1000.0)

    def _publish_debug_image(self, source, image, result):
        debug = image.copy()
        if result.visible:
            points = np.asarray(result.corners, dtype=np.int32).reshape(-1, 1, 2)
            cv2.polylines(debug, [points], True, (0, 255, 0), 2)
            cv2.circle(
                debug,
                (round(result.center_x_px), round(result.center_y_px)),
                4,
                (0, 0, 255),
                -1,
            )
        output = Image()
        output.header = source.header
        output.height, output.width = debug.shape[:2]
        output.encoding = "bgr8"
        output.is_bigendian = 0
        output.step = output.width * 3
        output.data = debug.tobytes()
        self._debug_publisher.publish(output)

    def _report_stats(self):
        elapsed = max(time.monotonic() - self._start, 1e-9)
        p95 = (
            float(np.percentile(self._latencies_ms, 95))
            if self._latencies_ms
            else 0.0
        )
        self.get_logger().info(
            f"stats frames={self._frames} detections={self._detections} "
            f"errors={self._errors} fps={self._frames / elapsed:.2f} "
            f"p95_ms={p95:.2f}"
        )


def main(args=None):
    """Run the ArUco ROS node."""
    rclpy.init(args=args)
    node = ArucoNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
