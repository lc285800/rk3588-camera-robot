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

"""A deterministic, ROS-independent PID controller."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PidConfig:
    """Validated PID gains and safety limits."""

    kp: float
    ki: float = 0.0
    kd: float = 0.0
    direction: float = -1.0
    deadband: float = 0.0
    integral_limit: float = 0.0
    output_limit: float = math.inf
    delta_limit: float = math.inf

    def __post_init__(self):
        """Reject ambiguous or unsafe controller parameters."""
        values = (
            self.kp,
            self.ki,
            self.kd,
            self.direction,
            self.deadband,
            self.integral_limit,
            self.output_limit,
            self.delta_limit,
        )
        if not all(math.isfinite(value) or value == math.inf for value in values):
            raise ValueError("PID parameters must be finite or a positive limit")
        if self.direction not in (-1.0, 1.0):
            raise ValueError("direction must be -1.0 or 1.0")
        if min(self.deadband, self.integral_limit) < 0.0:
            raise ValueError("deadband and integral_limit must be non-negative")
        if self.output_limit <= 0.0 or self.delta_limit <= 0.0:
            raise ValueError("output_limit and delta_limit must be positive")


class PidController:
    """Compute a safely limited control increment from normalized error."""

    def __init__(self, config):
        """Initialize a controller with no accumulated history."""
        self.config = config
        self.reset()

    @property
    def integral(self):
        """Return the current bounded integral state."""
        return self._integral

    @property
    def output(self):
        """Return the most recent limited output."""
        return self._output

    def reset(self):
        """Clear integral, derivative history, and output slew history."""
        self._integral = 0.0
        self._previous_error = None
        self._output = 0.0

    def update(self, error, dt):
        """Return the next limited output for a finite error and time step."""
        if not math.isfinite(error):
            raise ValueError("error must be finite")
        if not math.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt must be finite and positive")

        if abs(error) <= self.config.deadband:
            self._previous_error = error
            target = 0.0
        else:
            self._integral = self._clamp(
                self._integral + error * dt,
                self.config.integral_limit,
            )
            derivative = 0.0
            if self._previous_error is not None:
                derivative = (error - self._previous_error) / dt
            self._previous_error = error
            target = self.config.direction * (
                self.config.kp * error
                + self.config.ki * self._integral
                + self.config.kd * derivative
            )
            target = self._clamp(target, self.config.output_limit)

        change = self._clamp(target - self._output, self.config.delta_limit)
        self._output = self._clamp(
            self._output + change,
            self.config.output_limit,
        )
        return self._output

    @staticmethod
    def _clamp(value, limit):
        """Clamp a signed value to a symmetric positive limit."""
        if limit == math.inf:
            return value
        return max(-limit, min(limit, value))
