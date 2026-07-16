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

"""Tests for the deterministic simulated gimbal loop."""

import math

import pytest

from lubanvision_control.pid import PidConfig
from lubanvision_control.simulation import SimulationConfig, simulate_step


def tuned_pid():
    """Return the M14 acceptance controller parameters."""
    return PidConfig(
        kp=1.5,
        ki=0.0,
        kd=0.12,
        direction=-1.0,
        deadband=0.003,
        integral_limit=0.0,
        output_limit=0.5,
        delta_limit=0.08,
    )


@pytest.mark.parametrize("initial_error", [0.6, -0.6])
def test_signed_steps_converge_with_bounded_response(initial_error):
    """Positive and negative target steps converge symmetrically."""
    response = simulate_step(initial_error, tuned_pid())
    metrics = response.metrics

    assert metrics.rise_time_sec < 3.0
    assert metrics.settling_time_sec < 5.0
    assert metrics.overshoot_percent < 5.0
    assert metrics.steady_state_error < 0.005
    assert abs(metrics.final_error) < 0.005


@pytest.mark.parametrize("initial_error", [0.6, -0.6])
def test_output_and_slew_limits_hold_in_closed_loop(initial_error):
    """The simulated loop never bypasses PID safety limits."""
    pid = tuned_pid()
    response = simulate_step(initial_error, pid)

    assert response.metrics.max_abs_output <= pid.output_limit + 1e-12
    assert response.metrics.max_output_delta <= pid.delta_limit + 1e-12


def test_signed_responses_are_mirror_symmetric():
    """The normalized plant produces equal opposite trajectories."""
    positive = simulate_step(0.6, tuned_pid())
    negative = simulate_step(-0.6, tuned_pid())

    for positive_sample, negative_sample in zip(
        positive.samples, negative.samples
    ):
        assert positive_sample.error_norm == pytest.approx(
            -negative_sample.error_norm
        )
        assert positive_sample.command_norm_per_sec == pytest.approx(
            -negative_sample.command_norm_per_sec
        )


def test_invalid_simulation_inputs_are_rejected():
    """Invalid steps, plant parameters, and PID types fail explicitly."""
    with pytest.raises(ValueError, match="initial_error"):
        simulate_step(0.0, tuned_pid())
    with pytest.raises(ValueError, match="initial_error"):
        simulate_step(math.nan, tuned_pid())
    with pytest.raises(ValueError, match="pid_config"):
        simulate_step(0.6, object())
    with pytest.raises(ValueError, match="positive"):
        SimulationConfig(dt=0.0)
    with pytest.raises(ValueError, match="exceed"):
        SimulationConfig(dt=2.0, duration=1.0)
    with pytest.raises(ValueError, match="steady_state_window"):
        SimulationConfig(duration=0.5, steady_state_window=1.0)
