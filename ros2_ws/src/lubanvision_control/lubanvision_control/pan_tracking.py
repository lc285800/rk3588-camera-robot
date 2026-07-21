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

"""ROS-independent single-axis visual tracking coordinator."""

from dataclasses import dataclass
import math

from .pid import PidConfig, PidController
from .tracking_state import TrackingState, TrackingStateMachine


@dataclass(frozen=True)
class PanTrackingConfig:
    """Validated limits and timing for one provisional Pan axis."""

    target_id: int = 23
    center_angle_deg: float = 90.0
    min_angle_deg: float = 85.0
    max_angle_deg: float = 95.0
    observation_timeout_sec: float = 0.35
    hold_timeout_sec: float = 0.75
    return_rate_deg_sec: float = 2.0

    def __post_init__(self):
        """Reject unsafe angle ordering and timing values."""
        values = (
            self.center_angle_deg,
            self.min_angle_deg,
            self.max_angle_deg,
            self.observation_timeout_sec,
            self.hold_timeout_sec,
            self.return_rate_deg_sec,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("tracking configuration must be finite")
        if not self.min_angle_deg < self.center_angle_deg < self.max_angle_deg:
            raise ValueError("angle limits must strictly contain center")
        if self.observation_timeout_sec <= 0.0:
            raise ValueError("observation timeout must be positive")
        if self.hold_timeout_sec < 0.0:
            raise ValueError("hold timeout must be non-negative")
        if self.return_rate_deg_sec <= 0.0:
            raise ValueError("return rate must be positive")


@dataclass(frozen=True)
class PanTrackingOutput:
    """One bounded command and its diagnostic state."""

    angle_deg: float
    state: TrackingState
    observation_fresh: bool


class PanTrackingController:
    """Combine observation validation, target-loss behavior, and PID."""

    def __init__(self, config=None, pid_config=None):
        """Create a controller centered and disabled by default."""
        self.config = config or PanTrackingConfig()
        self.pid = PidController(pid_config or PidConfig(
            kp=4.0,
            kd=0.15,
            direction=-1.0,
            deadband=0.03,
            output_limit=3.0,
            delta_limit=0.5,
        ))
        self.state_machine = TrackingStateMachine(
            self.config.hold_timeout_sec
        )
        self.reset()

    @property
    def angle_deg(self):
        """Return the current bounded nominal command angle."""
        return self._angle_deg

    def reset(self):
        """Clear all observations and return the command to center."""
        self._angle_deg = self.config.center_angle_deg
        self._observation = None
        self.pid.reset()
        self.state_machine.reset()

    def set_observation(self, target_id, detected, error_x_norm, sample_time):
        """Store one validated observation using a monotonic sample time."""
        if isinstance(target_id, bool) or not isinstance(target_id, int):
            raise TypeError("target_id must be an integer")
        if not isinstance(detected, bool):
            raise TypeError("detected must be a bool")
        if not math.isfinite(error_x_norm):
            raise ValueError("error_x_norm must be finite")
        if not math.isfinite(sample_time) or sample_time < 0.0:
            raise ValueError("sample_time must be finite and non-negative")
        self._observation = (
            target_id,
            detected,
            max(-1.0, min(1.0, error_x_norm)),
            sample_time,
        )

    def update(self, now, dt):
        """Advance the controller and return one safely bounded command."""
        if not math.isfinite(now) or now < 0.0:
            raise ValueError("now must be finite and non-negative")
        if not math.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt must be finite and positive")

        fresh = False
        error = 0.0
        if self._observation is not None:
            target_id, detected, error, sample_time = self._observation
            age = now - sample_time
            if age < 0.0:
                raise ValueError("observation time must not be in the future")
            fresh = (
                detected
                and target_id == self.config.target_id
                and age <= self.config.observation_timeout_sec
            )

        decision = self.state_machine.update(fresh, now)
        if decision.reset_pid:
            self.pid.reset()
        if decision.use_pid:
            rate_deg_sec = self.pid.update(error, dt)
            self._angle_deg += rate_deg_sec * dt
        elif decision.return_to_center:
            self.pid.reset()
            maximum_step = self.config.return_rate_deg_sec * dt
            center_error = self.config.center_angle_deg - self._angle_deg
            self._angle_deg += max(-maximum_step, min(maximum_step, center_error))

        self._angle_deg = max(
            self.config.min_angle_deg,
            min(self.config.max_angle_deg, self._angle_deg),
        )
        return PanTrackingOutput(self._angle_deg, decision.state, fresh)
