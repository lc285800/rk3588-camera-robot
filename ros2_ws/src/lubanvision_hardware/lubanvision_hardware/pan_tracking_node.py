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

"""ROS 2 single-axis visual tracker backed by the bounded sysfs PWM core."""

import json
import math
import time

from lubanvision_control.pan_tracking import (
    PanTrackingConfig,
    PanTrackingController,
)
from lubanvision_control.pid import PidConfig
from lubanvision_interfaces.msg import TargetObservation
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Bool, String

from .servo_calibration import ServoCalibration
from .sysfs_pwm import ServoPwmConfig, SysfsPwmChannel


class PanTrackingNode(Node):
    """Drive one provisional Pan servo only after explicit ROS enable."""

    def __init__(self):
        super().__init__("pan_tracking")
        self._declare_parameters()
        self._pwm_config = ServoPwmConfig(
            pwmchip=int(self.get_parameter("pwmchip").value),
            channel=int(self.get_parameter("pwm_channel").value),
            period_ns=int(self.get_parameter("period_ns").value),
            center_ns=int(self.get_parameter("center_pulse_ns").value),
            min_pulse_ns=int(self.get_parameter("min_pulse_ns").value),
            max_pulse_ns=int(self.get_parameter("max_pulse_ns").value),
        )
        self._calibration = ServoCalibration(
            min_angle_deg=float(self.get_parameter("min_angle_deg").value),
            center_angle_deg=float(
                self.get_parameter("center_angle_deg").value
            ),
            max_angle_deg=float(self.get_parameter("max_angle_deg").value),
            pulse_per_degree_ns=float(
                self.get_parameter("pulse_per_degree_ns").value
            ),
        )
        observation_timeout = float(
            self.get_parameter("observation_timeout_sec").value
        )
        self._controller = PanTrackingController(
            PanTrackingConfig(
                target_id=int(self.get_parameter("target_id").value),
                center_angle_deg=self._calibration.center_angle_deg,
                min_angle_deg=self._calibration.min_angle_deg,
                max_angle_deg=self._calibration.max_angle_deg,
                observation_timeout_sec=observation_timeout,
                hold_timeout_sec=float(
                    self.get_parameter("hold_timeout_sec").value
                ),
                return_rate_deg_sec=float(
                    self.get_parameter("return_rate_deg_sec").value
                ),
            ),
            PidConfig(
                kp=float(self.get_parameter("kp").value),
                ki=float(self.get_parameter("ki").value),
                kd=float(self.get_parameter("kd").value),
                direction=float(self.get_parameter("direction").value),
                deadband=float(self.get_parameter("deadband").value),
                integral_limit=float(
                    self.get_parameter("integral_limit").value
                ),
                output_limit=float(self.get_parameter("output_limit").value),
                delta_limit=float(self.get_parameter("delta_limit").value),
            ),
        )
        self._observation_timeout = observation_timeout
        self._channel = None
        self._enabled = False
        self._enable_requested = False
        self._fault = ""
        self._last_tick = time.monotonic()
        self._last_pulse = None

        self._state_publisher = self.create_publisher(
            String,
            self.get_parameter("state_topic").value,
            10,
        )
        self.create_subscription(
            TargetObservation,
            self.get_parameter("observation_topic").value,
            self._on_observation,
            10,
        )
        self.create_subscription(
            Bool,
            self.get_parameter("enable_topic").value,
            self._on_enable,
            10,
        )
        update_rate = float(self.get_parameter("update_rate_hz").value)
        if not math.isfinite(update_rate) or update_rate <= 0.0:
            raise ValueError("update_rate_hz must be finite and positive")
        self.create_timer(1.0 / update_rate, self._update)
        self.get_logger().info(
            "ready disabled; publish true on /tracking/enabled to move"
        )

    def _declare_parameters(self):
        """Declare conservative M17 defaults."""
        parameters = {
            "observation_topic": "/target/observation",
            "enable_topic": "/tracking/enabled",
            "state_topic": "/gimbal/state",
            "target_id": 23,
            "update_rate_hz": 20.0,
            "observation_timeout_sec": 0.35,
            "hold_timeout_sec": 0.75,
            "return_rate_deg_sec": 2.0,
            "kp": 4.0,
            "ki": 0.0,
            "kd": 0.15,
            "direction": -1.0,
            "deadband": 0.03,
            "integral_limit": 0.0,
            "output_limit": 3.0,
            "delta_limit": 0.5,
            "pwmchip": 3,
            "pwm_channel": 0,
            "period_ns": 20_000_000,
            "center_pulse_ns": 1_900_000,
            "min_pulse_ns": 1_850_000,
            "max_pulse_ns": 1_950_000,
            "min_angle_deg": 85.0,
            "center_angle_deg": 90.0,
            "max_angle_deg": 95.0,
            "pulse_per_degree_ns": 10_000.0,
        }
        for name, value in parameters.items():
            self.declare_parameter(name, value)

    def _on_observation(self, message):
        """Validate source age before accepting a detector observation."""
        stamp_ns = message.header.stamp.sec * 1_000_000_000
        stamp_ns += message.header.stamp.nanosec
        age_sec = (self.get_clock().now().nanoseconds - stamp_ns) / 1e9
        if stamp_ns <= 0 or age_sec < -0.1 or age_sec > self._observation_timeout:
            return
        try:
            self._controller.set_observation(
                int(message.target_id),
                message.status == TargetObservation.STATUS_DETECTED,
                float(message.error_x_norm),
                time.monotonic(),
            )
        except (TypeError, ValueError) as error:
            self.get_logger().warning(f"ignored invalid observation: {error}")

    def _on_enable(self, message):
        """Act once per enable edge so a fault cannot cause a retry loop."""
        requested = bool(message.data)
        if requested and not self._enable_requested:
            self._enable_requested = True
            self._enable_hardware()
        elif not requested and self._enable_requested:
            self._enable_requested = False
            if self._enabled or self._channel is not None:
                self._disable_hardware()

    def _enable_hardware(self):
        """Acquire PWM and enable it at center, failing closed."""
        channel = SysfsPwmChannel(self._pwm_config)
        try:
            channel.open()
            channel.enable_center()
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            try:
                channel.close()
            except OSError:
                pass
            self._fault = str(error)
            self.get_logger().error(f"tracking enable failed: {error}")
            return
        self._channel = channel
        self._controller.reset()
        self._last_tick = time.monotonic()
        self._last_pulse = self._pwm_config.center_ns
        self._fault = ""
        self._enabled = True
        self.get_logger().info("tracking enabled at provisional center")

    def _disable_hardware(self):
        """Request center and release PWM, preserving cleanup errors."""
        channel = self._channel
        self._channel = None
        self._enabled = False
        self._controller.reset()
        if channel is None:
            return
        try:
            channel.set_pulse_ns(self._pwm_config.center_ns)
            time.sleep(0.2)
            channel.close()
            self.get_logger().info("tracking disabled and PWM released")
        except (OSError, RuntimeError, ValueError) as error:
            self._fault = str(error)
            self.get_logger().error(f"PWM cleanup failed: {error}")
            try:
                channel.close()
            except OSError:
                pass

    def _update(self):
        """Run one bounded control tick and publish compact diagnostics."""
        if not self._enabled:
            self._publish_state(
                "disabled",
                self._calibration.center_angle_deg,
                None,
                False,
            )
            return
        now = time.monotonic()
        dt = max(0.001, min(0.1, now - self._last_tick))
        self._last_tick = now
        try:
            output = self._controller.update(now, dt)
            pulse = self._calibration.angle_to_pulse_ns(
                output.angle_deg,
                self._pwm_config,
            )
            if pulse != self._last_pulse:
                self._channel.set_pulse_ns(pulse)
                self._last_pulse = pulse
            self._publish_state(
                output.state.value,
                output.angle_deg,
                pulse,
                output.observation_fresh,
            )
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            self._fault = str(error)
            self.get_logger().error(f"tracking stopped after fault: {error}")
            self._disable_hardware()

    def _publish_state(self, state, angle_deg, pulse_ns, fresh):
        """Publish machine-readable state until a custom message is added."""
        message = String()
        message.data = json.dumps(
            {
                "enabled": self._enabled,
                "enable_requested": self._enable_requested,
                "state": state,
                "angle_deg": round(angle_deg, 4),
                "pulse_ns": pulse_ns,
                "observation_fresh": fresh,
                "fault": self._fault,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        self._state_publisher.publish(message)

    def destroy_node(self):
        """Release an owned PWM channel before destroying ROS resources."""
        if self._enabled or self._channel is not None:
            self._disable_hardware()
        return super().destroy_node()


def main(args=None):
    """Run the default-disabled single-axis tracking node."""
    rclpy.init(args=args)
    node = PanTrackingNode()
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
