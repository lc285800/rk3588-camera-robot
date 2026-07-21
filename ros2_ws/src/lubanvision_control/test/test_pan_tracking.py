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

"""Tests for the single-axis visual tracking coordinator."""

import pytest

from lubanvision_control.pan_tracking import (
    PanTrackingConfig,
    PanTrackingController,
)
from lubanvision_control.pid import PidConfig
from lubanvision_control.tracking_state import TrackingState


def make_controller(**config):
    """Create a deterministic controller with simple proportional action."""
    return PanTrackingController(
        PanTrackingConfig(**config),
        PidConfig(
            kp=2.0,
            direction=-1.0,
            deadband=0.05,
            output_limit=4.0,
            delta_limit=4.0,
        ),
    )


def test_valid_target_moves_in_expected_direction_and_stays_bounded():
    """A right-side target moves Pan left without crossing its limit."""
    controller = make_controller()
    controller.set_observation(23, True, 1.0, 0.0)

    outputs = [controller.update(index * 0.1, 0.1) for index in range(60)]

    assert outputs[0].state is TrackingState.TRACKING
    assert outputs[0].angle_deg < 90.0
    assert min(output.angle_deg for output in outputs) >= 85.0


def test_wrong_target_and_stale_observation_do_not_drive_pid():
    """Wrong IDs and expired samples remain non-actionable."""
    controller = make_controller(observation_timeout_sec=0.2)
    controller.set_observation(7, True, 1.0, 0.0)
    wrong = controller.update(0.1, 0.1)
    controller.set_observation(23, True, 1.0, 0.0)
    stale = controller.update(0.3, 0.1)

    assert not wrong.observation_fresh
    assert not stale.observation_fresh
    assert wrong.angle_deg == 90.0
    assert stale.angle_deg == 90.0


def test_loss_holds_then_returns_to_center_at_limited_rate():
    """Target loss preserves position briefly before a slow return."""
    controller = make_controller(
        observation_timeout_sec=0.2,
        hold_timeout_sec=0.5,
        return_rate_deg_sec=1.0,
    )
    controller.set_observation(23, True, 1.0, 0.0)
    tracked = controller.update(0.1, 0.1)
    held = controller.update(0.4, 0.1)
    returned = controller.update(0.9, 0.1)

    assert tracked.angle_deg == pytest.approx(89.8)
    assert held.state is TrackingState.HOLDING
    assert held.angle_deg == tracked.angle_deg
    assert returned.state is TrackingState.RETURNING
    assert returned.angle_deg == pytest.approx(89.9)


def test_reacquisition_resets_pid_history():
    """A newly reacquired target cannot reuse derivative history."""
    controller = PanTrackingController(
        PanTrackingConfig(observation_timeout_sec=0.1),
        PidConfig(kp=0.0, kd=1.0, direction=1.0),
    )
    controller.set_observation(23, True, 0.5, 0.0)
    controller.update(0.0, 0.1)
    controller.update(0.2, 0.1)
    controller.set_observation(23, True, -0.5, 0.2)

    output = controller.update(0.2, 0.1)

    assert output.angle_deg == 90.0


@pytest.mark.parametrize(
    "values",
    [
        (23, True, float("nan"), 0.0),
        (23, True, 0.0, -1.0),
        (23, 1, 0.0, 0.0),
    ],
)
def test_invalid_observation_is_rejected(values):
    """Malformed observations fail before reaching the controller."""
    with pytest.raises((TypeError, ValueError)):
        make_controller().set_observation(*values)


def test_future_observation_is_rejected():
    """A source time ahead of the control clock cannot drive motion."""
    controller = make_controller()
    controller.set_observation(23, True, 0.5, 2.0)

    with pytest.raises(ValueError, match="future"):
        controller.update(1.0, 0.1)
