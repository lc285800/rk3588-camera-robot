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

"""Tests for target loss and reacquisition behavior."""

import math

import pytest

from lubanvision_control.tracking_state import (
    TrackingState,
    TrackingStateMachine,
)


def test_visible_target_enters_tracking_and_requests_pid_reset():
    """Initial acquisition starts tracking with clean PID history."""
    machine = TrackingStateMachine(hold_timeout=1.0)

    decision = machine.update(True, 10.0)

    assert decision.state is TrackingState.TRACKING
    assert decision.use_pid
    assert decision.reset_pid


def test_short_loss_holds_then_returns_at_timeout():
    """Loss first holds the current angle and later requests centering."""
    machine = TrackingStateMachine(hold_timeout=1.0)
    machine.update(True, 10.0)

    holding = machine.update(False, 10.0)
    still_holding = machine.update(False, 10.999)
    returning = machine.update(False, 11.0)

    assert holding.hold_position
    assert still_holding.state is TrackingState.HOLDING
    assert returning.state is TrackingState.RETURNING
    assert returning.return_to_center


def test_reacquisition_from_hold_or_return_resets_pid():
    """Any lost-target recovery clears stale controller history."""
    machine = TrackingStateMachine(hold_timeout=0.5)
    machine.update(True, 1.0)
    machine.update(False, 1.0)

    from_hold = machine.update(True, 1.2)
    machine.update(False, 2.0)
    machine.update(False, 2.5)
    from_return = machine.update(True, 3.0)

    assert from_hold.reset_pid
    assert from_return.reset_pid


def test_continuous_tracking_does_not_repeatedly_reset_pid():
    """Stable visibility preserves PID state after acquisition."""
    machine = TrackingStateMachine(hold_timeout=1.0)

    assert machine.update(True, 1.0).reset_pid
    assert not machine.update(True, 1.1).reset_pid


def test_zero_hold_timeout_returns_immediately():
    """A zero timeout disables holding without enabling scanning."""
    machine = TrackingStateMachine(hold_timeout=0.0)

    decision = machine.update(False, 2.0)

    assert decision.state is TrackingState.RETURNING
    assert not decision.use_pid
    assert not decision.hold_position


def test_reset_restores_safe_holding_state():
    """Reset forgets target history and commands no active motion."""
    machine = TrackingStateMachine(hold_timeout=1.0)
    machine.update(True, 1.0)

    machine.reset()

    assert machine.state is TrackingState.HOLDING


@pytest.mark.parametrize("now", [-1.0, math.nan, math.inf])
def test_invalid_time_is_rejected(now):
    """Invalid monotonic timestamps fail explicitly."""
    machine = TrackingStateMachine(hold_timeout=1.0)

    with pytest.raises(ValueError, match="now"):
        machine.update(False, now)


def test_backwards_time_is_rejected_during_loss():
    """Clock regressions cannot shorten or extend the hold silently."""
    machine = TrackingStateMachine(hold_timeout=1.0)
    machine.update(True, 2.0)
    machine.update(False, 2.0)

    with pytest.raises(ValueError, match="backwards"):
        machine.update(False, 1.9)


def test_invalid_configuration_and_visibility_are_rejected():
    """Ambiguous timeout and visibility inputs are rejected."""
    with pytest.raises(ValueError, match="hold_timeout"):
        TrackingStateMachine(-1.0)
    machine = TrackingStateMachine(1.0)
    with pytest.raises(ValueError, match="bool"):
        machine.update(1, 0.0)
