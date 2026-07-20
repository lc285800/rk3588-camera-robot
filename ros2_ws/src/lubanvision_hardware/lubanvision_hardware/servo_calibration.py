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

"""Provisional angle mapping for the M16 three-point servo range."""

from dataclasses import dataclass
import math

from .sysfs_pwm import ServoPwmConfig


@dataclass(frozen=True)
class ServoCalibration:
    """Map a deliberately narrow nominal angle range to tested pulses."""

    min_angle_deg: float = 85.0
    center_angle_deg: float = 90.0
    max_angle_deg: float = 95.0
    pulse_per_degree_ns: float = 10_000.0
    increasing_pulse_direction: str = "right"

    def __post_init__(self):
        """Reject non-finite, unordered, or ambiguous calibration values."""
        values = (
            self.min_angle_deg,
            self.center_angle_deg,
            self.max_angle_deg,
            self.pulse_per_degree_ns,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("calibration values must be finite")
        if not self.min_angle_deg < self.center_angle_deg < self.max_angle_deg:
            raise ValueError("angle bounds must strictly contain the center")
        if self.pulse_per_degree_ns <= 0.0:
            raise ValueError("pulse_per_degree_ns must be positive")
        if self.increasing_pulse_direction not in ("left", "right"):
            raise ValueError("increasing pulse direction must be left or right")

    def angle_to_pulse_ns(self, angle_deg, pwm_config=None):
        """Convert one bounded nominal angle to a validated integer pulse."""
        if isinstance(angle_deg, bool) or not isinstance(angle_deg, (int, float)):
            raise TypeError("angle_deg must be a number")
        if not math.isfinite(angle_deg):
            raise ValueError("angle_deg must be finite")
        if not self.min_angle_deg <= angle_deg <= self.max_angle_deg:
            raise ValueError(
                f"angle_deg must be within {self.min_angle_deg}.."
                f"{self.max_angle_deg}"
            )
        pwm_config = pwm_config or ServoPwmConfig()
        pulse_ns = round(
            pwm_config.center_ns
            + (angle_deg - self.center_angle_deg) * self.pulse_per_degree_ns
        )
        return pwm_config.validate_pulse(pulse_ns)

    def pulse_ns_to_angle(self, pulse_ns, pwm_config=None):
        """Convert one validated pulse to its nominal calibration angle."""
        pwm_config = pwm_config or ServoPwmConfig()
        pulse_ns = pwm_config.validate_pulse(pulse_ns)
        return (
            self.center_angle_deg
            + (pulse_ns - pwm_config.center_ns) / self.pulse_per_degree_ns
        )
