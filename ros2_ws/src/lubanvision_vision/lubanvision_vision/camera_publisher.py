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

"""Publish V4L2 camera frames without depending on cv_bridge."""

import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class CameraPublisher(Node):
    """Read a V4L2 camera and publish BGR image messages."""

    def __init__(self):
        super().__init__("camera_publisher")
        self.declare_parameter("video_device", "/dev/video1")
        self.declare_parameter("image_width", 640)
        self.declare_parameter("image_height", 480)
        self.declare_parameter("frame_rate", 30.0)
        self.declare_parameter("pixel_format", "MJPG")
        self.declare_parameter("frame_id", "camera_link")

        device = self.get_parameter("video_device").value
        width = self.get_parameter("image_width").value
        height = self.get_parameter("image_height").value
        frame_rate = self.get_parameter("frame_rate").value
        pixel_format = self.get_parameter("pixel_format").value

        self._frame_id = self.get_parameter("frame_id").value
        self._capture = cv2.VideoCapture(device, cv2.CAP_V4L2)
        self._capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*pixel_format))
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._capture.set(cv2.CAP_PROP_FPS, frame_rate)
        if not self._capture.isOpened():
            raise RuntimeError(f"Unable to open camera {device}")

        actual_width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_rate = self._capture.get(cv2.CAP_PROP_FPS)
        self._publisher = self.create_publisher(
            Image, "/camera/image_raw", qos_profile_sensor_data
        )
        self._timer = self.create_timer(1.0 / frame_rate, self._publish_frame)
        self.get_logger().info(
            f"Camera {device}: {actual_width}x{actual_height} at {actual_rate:.2f} FPS"
        )

    def _publish_frame(self):
        ok, frame = self._capture.read()
        if not ok:
            self.get_logger().error("Camera frame read failed", throttle_duration_sec=2.0)
            return

        message = Image()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = self._frame_id
        message.height, message.width = frame.shape[:2]
        message.encoding = "bgr8"
        message.is_bigendian = False
        message.step = message.width * 3
        message.data = frame.tobytes()
        self._publisher.publish(message)

    def destroy_node(self):
        self._capture.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = CameraPublisher()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
