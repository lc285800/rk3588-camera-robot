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

"""Target visibility state machine for safe gimbal behavior."""

from dataclasses import dataclass
from enum import Enum
import math


class TrackingState(Enum):
    """Externally visible tracking modes."""

    TRACKING = "tracking"
    HOLDING = "holding"
    RETURNING = "returning"


@dataclass(frozen=True)
class TrackingDecision:
    """State transition result consumed by a future ROS controller."""

    state: TrackingState
    use_pid: bool
    hold_position: bool
    return_to_center: bool
    reset_pid: bool


class TrackingStateMachine:
    """Switch between tracking, short hold, and return-to-center."""

    def __init__(self, hold_timeout):
        """Create a state machine with a non-negative hold duration."""
        if not math.isfinite(hold_timeout) or hold_timeout < 0.0:
            raise ValueError("hold_timeout must be finite and non-negative")
        self.hold_timeout = hold_timeout
        self.reset()

    @property
    def state(self):
        """Return the current tracking state."""
        return self._state

    def reset(self):
        """Return to safe holding state with no visibility history."""
        self._state = TrackingState.HOLDING
        self._lost_at = None

    def update(self, visible, now):
        """Advance the state machine using a monotonic timestamp."""
        if not isinstance(visible, bool):
            raise ValueError("visible must be a bool")
        if not math.isfinite(now) or now < 0.0:
            raise ValueError("now must be finite and non-negative")

        previous = self._state
        if visible:
            self._state = TrackingState.TRACKING
            self._lost_at = None
        else:
            if previous is TrackingState.TRACKING or self._lost_at is None:
                self._lost_at = now
            elapsed = now - self._lost_at
            if elapsed < 0.0:
                raise ValueError("now must not move backwards")
            if elapsed < self.hold_timeout:
                self._state = TrackingState.HOLDING
            else:
                self._state = TrackingState.RETURNING

        reacquired = (
            self._state is TrackingState.TRACKING
            and previous is not TrackingState.TRACKING
        )
        return TrackingDecision(
            state=self._state,
            use_pid=self._state is TrackingState.TRACKING,
            hold_position=self._state is TrackingState.HOLDING,
            return_to_center=self._state is TrackingState.RETURNING,
            reset_pid=reacquired,
        )
