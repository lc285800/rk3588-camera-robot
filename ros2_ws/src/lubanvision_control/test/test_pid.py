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

"""Tests for the ROS-independent PID controller."""

import math

import pytest

from lubanvision_control.pid import PidConfig, PidController


def test_direction_matches_pan_error_convention():
    """A target right of center produces a negative Pan increment."""
    controller = PidController(PidConfig(kp=2.0, direction=-1.0))

    assert controller.update(0.25, 0.1) == pytest.approx(-0.5)
    controller.reset()
    assert controller.update(-0.25, 0.1) == pytest.approx(0.5)


def test_deadband_commands_zero_without_integrating():
    """Small image errors settle toward zero and do not wind up."""
    controller = PidController(
        PidConfig(kp=1.0, ki=1.0, deadband=0.05, delta_limit=0.2)
    )

    assert controller.update(0.04, 0.1) == 0.0
    assert controller.integral == 0.0


def test_integral_is_bounded_in_both_directions():
    """Persistent error cannot grow the integral beyond its limit."""
    controller = PidController(
        PidConfig(kp=0.0, ki=1.0, direction=1.0, integral_limit=0.3)
    )

    for _ in range(10):
        controller.update(1.0, 0.1)
    assert controller.integral == pytest.approx(0.3)

    controller.reset()
    for _ in range(10):
        controller.update(-1.0, 0.1)
    assert controller.integral == pytest.approx(-0.3)


def test_output_and_per_cycle_delta_are_limited():
    """Large gains obey both absolute and slew limits."""
    controller = PidController(
        PidConfig(
            kp=100.0,
            direction=1.0,
            output_limit=1.0,
            delta_limit=0.25,
        )
    )

    outputs = [controller.update(1.0, 0.1) for _ in range(5)]

    assert outputs == pytest.approx([0.25, 0.5, 0.75, 1.0, 1.0])


def test_reset_clears_all_history():
    """Reset removes integral, derivative, and slew state."""
    controller = PidController(
        PidConfig(
            kp=1.0,
            ki=1.0,
            kd=1.0,
            direction=1.0,
            integral_limit=1.0,
        )
    )
    controller.update(0.5, 0.1)
    controller.update(0.25, 0.1)

    controller.reset()

    assert controller.integral == 0.0
    assert controller.output == 0.0
    assert controller.update(0.25, 0.1) == pytest.approx(0.275)


@pytest.mark.parametrize(
    ("error", "dt"),
    [(math.nan, 0.1), (math.inf, 0.1), (0.1, 0.0), (0.1, -1.0),
     (0.1, math.nan), (0.1, math.inf)],
)
def test_invalid_runtime_inputs_are_rejected(error, dt):
    """Non-finite errors and invalid time steps fail explicitly."""
    controller = PidController(PidConfig(kp=1.0))

    with pytest.raises(ValueError):
        controller.update(error, dt)


@pytest.mark.parametrize(
    "config",
    [
        PidConfig,
    ],
)
def test_config_type_is_available(config):
    """The public configuration type remains importable."""
    assert config is PidConfig


def test_invalid_configuration_is_rejected():
    """Unsafe sign and limit semantics cannot be constructed."""
    with pytest.raises(ValueError, match="direction"):
        PidConfig(kp=1.0, direction=0.0)
    with pytest.raises(ValueError, match="positive"):
        PidConfig(kp=1.0, output_limit=0.0)
    with pytest.raises(ValueError, match="non-negative"):
        PidConfig(kp=1.0, deadband=-0.1)
