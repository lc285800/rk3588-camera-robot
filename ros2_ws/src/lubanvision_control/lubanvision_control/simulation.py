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

"""Deterministic single-axis gimbal closed-loop simulation."""

from dataclasses import asdict, dataclass
import math

from .pid import PidConfig, PidController


@dataclass(frozen=True)
class SimulationConfig:
    """Parameters for a normalized image-error and gimbal model."""

    dt: float = 0.05
    duration: float = 8.0
    actuator_time_constant: float = 0.18
    plant_gain: float = 1.0
    settling_ratio: float = 0.02
    steady_state_window: float = 1.0

    def __post_init__(self):
        """Reject invalid timing and plant parameters."""
        values = (
            self.dt,
            self.duration,
            self.actuator_time_constant,
            self.plant_gain,
            self.settling_ratio,
            self.steady_state_window,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError("simulation parameters must be finite and positive")
        if self.dt > self.duration:
            raise ValueError("dt must not exceed duration")
        if self.steady_state_window > self.duration:
            raise ValueError("steady_state_window must not exceed duration")


@dataclass(frozen=True)
class SimulationSample:
    """One closed-loop simulation sample."""

    time_sec: float
    error_norm: float
    command_norm_per_sec: float
    actuator_rate_norm_per_sec: float


@dataclass(frozen=True)
class StepMetrics:
    """Metrics used to accept a simulated step response."""

    initial_error: float
    rise_time_sec: float
    settling_time_sec: float
    overshoot_percent: float
    steady_state_error: float
    max_abs_output: float
    max_output_delta: float
    final_error: float
    sample_count: int

    def as_dict(self):
        """Return a JSON-serializable metric mapping."""
        return asdict(self)


@dataclass(frozen=True)
class StepResponse:
    """Samples and metrics for one signed target step."""

    samples: tuple
    metrics: StepMetrics


def simulate_step(initial_error, pid_config, simulation_config=None):
    """Simulate one signed target step and calculate response metrics."""
    if not math.isfinite(initial_error) or initial_error == 0.0:
        raise ValueError("initial_error must be finite and non-zero")
    if not isinstance(pid_config, PidConfig):
        raise ValueError("pid_config must be a PidConfig")
    config = simulation_config or SimulationConfig()
    controller = PidController(pid_config)
    error = initial_error
    actuator_rate = 0.0
    samples = []
    step_count = int(round(config.duration / config.dt))

    for index in range(step_count + 1):
        now = index * config.dt
        command = controller.update(error, config.dt)
        samples.append(
            SimulationSample(
                time_sec=now,
                error_norm=error,
                command_norm_per_sec=command,
                actuator_rate_norm_per_sec=actuator_rate,
            )
        )
        actuator_rate += (
            command - actuator_rate
        ) * config.dt / config.actuator_time_constant
        error += actuator_rate * config.plant_gain * config.dt

    metrics = calculate_metrics(samples, initial_error, config)
    return StepResponse(samples=tuple(samples), metrics=metrics)


def calculate_metrics(samples, initial_error, config):
    """Calculate deterministic rise, settling, overshoot, and limit metrics."""
    initial_abs = abs(initial_error)
    rise_threshold = initial_abs * 0.1
    settle_threshold = initial_abs * config.settling_ratio
    rise_time = _first_time_within(samples, rise_threshold)
    settling_time = _settling_time(samples, settle_threshold)
    opposite_errors = [
        abs(sample.error_norm)
        for sample in samples
        if sample.error_norm * initial_error < 0.0
    ]
    overshoot = max(opposite_errors, default=0.0) / initial_abs * 100.0
    steady_start = config.duration - config.steady_state_window
    steady_errors = [
        abs(sample.error_norm)
        for sample in samples
        if sample.time_sec >= steady_start
    ]
    outputs = [sample.command_norm_per_sec for sample in samples]
    output_deltas = [
        abs(current - previous)
        for previous, current in zip(outputs, outputs[1:])
    ]
    return StepMetrics(
        initial_error=initial_error,
        rise_time_sec=rise_time,
        settling_time_sec=settling_time,
        overshoot_percent=overshoot,
        steady_state_error=sum(steady_errors) / len(steady_errors),
        max_abs_output=max(abs(output) for output in outputs),
        max_output_delta=max(output_deltas, default=0.0),
        final_error=samples[-1].error_norm,
        sample_count=len(samples),
    )


def _first_time_within(samples, threshold):
    """Return the first time the error magnitude reaches a threshold."""
    for sample in samples:
        if abs(sample.error_norm) <= threshold:
            return sample.time_sec
    return math.inf


def _settling_time(samples, threshold):
    """Return the first time after which all errors remain within a band."""
    for index, sample in enumerate(samples):
        if all(
            abs(candidate.error_norm) <= threshold
            for candidate in samples[index:]
        ):
            return sample.time_sec
    return math.inf
