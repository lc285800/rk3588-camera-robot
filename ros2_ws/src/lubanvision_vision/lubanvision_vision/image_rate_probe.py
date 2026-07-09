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

"""Count incoming image frames with sensor-data QoS."""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class ImageRateProbe(Node):
    """Subscribe to an image topic and report lightweight receive statistics."""

    def __init__(self):
        super().__init__("image_rate_probe")
        self.declare_parameter("topic", "/camera/image_raw")
        self.declare_parameter("duration_sec", 10.0)
        self.declare_parameter("expected_width", 640)
        self.declare_parameter("expected_height", 480)
        self.declare_parameter("expected_encoding", "bgr8")

        self._topic = self.get_parameter("topic").value
        self._duration_sec = float(self.get_parameter("duration_sec").value)
        self._expected_width = int(self.get_parameter("expected_width").value)
        self._expected_height = int(self.get_parameter("expected_height").value)
        self._expected_encoding = self.get_parameter("expected_encoding").value
        self._frames = 0
        self._bad_frames = 0
        self._start_time = self.get_clock().now()
        self._first_time = None
        self._last_time = None
        self._done = False

        self.create_subscription(
            Image, self._topic, self._on_image, qos_profile_sensor_data
        )
        self.create_timer(0.2, self._maybe_finish)
        self.get_logger().info(
            f"Counting {self._topic} for {self._duration_sec:.1f}s"
        )

    @property
    def done(self):
        """Return whether the probe collected its requested sample window."""
        return self._done

    def _on_image(self, message):
        now = self.get_clock().now()
        if self._first_time is None:
            self._first_time = now
        self._last_time = now
        self._frames += 1

        if (
            message.width != self._expected_width
            or message.height != self._expected_height
            or message.encoding != self._expected_encoding
        ):
            self._bad_frames += 1

    def _maybe_finish(self):
        if self._done:
            return

        now = self.get_clock().now()
        elapsed = (now - self._start_time).nanoseconds / 1e9
        if elapsed < self._duration_sec:
            return

        sample_span = 0.0
        if self._first_time is not None and self._last_time is not None:
            sample_span = max(
                (self._last_time - self._first_time).nanoseconds / 1e9, 0.0
            )
        fps = self._frames / sample_span if sample_span > 0.0 else 0.0
        self.get_logger().info(
            f"Received {self._frames} frames in {sample_span:.2f}s "
            f"({fps:.2f} FPS), bad_frames={self._bad_frames}"
        )
        self._done = True


def main(args=None):
    rclpy.init(args=args)
    node = ImageRateProbe()
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
