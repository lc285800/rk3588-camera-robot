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

"""Tests for the provisional M16 servo angle mapping."""

import math

import pytest

from lubanvision_hardware.servo_calibration import ServoCalibration
from lubanvision_hardware.sysfs_pwm import ServoPwmConfig


def test_three_nominal_points_match_observed_pulses():
    """Map the M16 85/90/95 points to the three tested pulse values."""
    calibration = ServoCalibration()

    assert calibration.angle_to_pulse_ns(85.0) == 1_450_000
    assert calibration.angle_to_pulse_ns(90.0) == 1_500_000
    assert calibration.angle_to_pulse_ns(95.0) == 1_550_000


def test_default_direction_matches_physical_observation():
    """Record that larger pulses moved the installed servo to the right."""
    assert ServoCalibration().increasing_pulse_direction == "right"


def test_round_trip_preserves_in_range_angles():
    """Convert nominal angles to integer pulses and back deterministically."""
    calibration = ServoCalibration()

    for angle in (85.0, 87.5, 90.0, 92.5, 95.0):
        pulse = calibration.angle_to_pulse_ns(angle)
        assert calibration.pulse_ns_to_angle(pulse) == pytest.approx(angle)


@pytest.mark.parametrize("angle", [84.999, 95.001, math.inf, math.nan])
def test_invalid_runtime_angle_is_rejected(angle):
    """Reject non-finite and out-of-range nominal angle commands."""
    with pytest.raises(ValueError):
        ServoCalibration().angle_to_pulse_ns(angle)


@pytest.mark.parametrize("angle", [True, "90"])
def test_non_numeric_runtime_angle_is_rejected(angle):
    """Reject booleans and strings before computing a pulse."""
    with pytest.raises(TypeError):
        ServoCalibration().angle_to_pulse_ns(angle)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_angle_deg": 90.0},
        {"max_angle_deg": 90.0},
        {"pulse_per_degree_ns": 0.0},
        {"pulse_per_degree_ns": math.inf},
        {"increasing_pulse_direction": "unknown"},
    ],
)
def test_invalid_calibration_is_rejected(kwargs):
    """Reject unordered bounds, invalid scale, and ambiguous direction."""
    with pytest.raises(ValueError):
        ServoCalibration(**kwargs)


def test_pwm_limits_remain_authoritative():
    """Refuse a mapping that exceeds the independent PWM hard bounds."""
    narrow_pwm = ServoPwmConfig(
        min_pulse_ns=1_475_000,
        max_pulse_ns=1_525_000,
    )

    with pytest.raises(ValueError, match="pulse_ns"):
        ServoCalibration().angle_to_pulse_ns(85.0, narrow_pwm)
