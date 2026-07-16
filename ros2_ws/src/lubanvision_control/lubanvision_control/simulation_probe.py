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

"""Generate reproducible M14 simulation data, metrics, and an SVG plot."""

import argparse
import csv
import json
from pathlib import Path

from .pid import PidConfig
from .simulation import SimulationConfig, simulate_step


def main():
    """Run positive and negative step simulations into an output directory."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pid_config = PidConfig(
        kp=1.5,
        ki=0.0,
        kd=0.12,
        direction=-1.0,
        deadband=0.003,
        integral_limit=0.0,
        output_limit=0.5,
        delta_limit=0.08,
    )
    simulation_config = SimulationConfig()
    responses = {
        "positive": simulate_step(0.6, pid_config, simulation_config),
        "negative": simulate_step(-0.6, pid_config, simulation_config),
    }

    _write_csv(output_dir / "step_response.csv", responses)
    _write_metrics(
        output_dir / "metrics.json",
        pid_config,
        simulation_config,
        responses,
    )
    _write_svg(output_dir / "step_response.svg", responses)
    for name, response in responses.items():
        metrics = response.metrics
        print(
            f"{name}: rise={metrics.rise_time_sec:.3f}s "
            f"settle={metrics.settling_time_sec:.3f}s "
            f"overshoot={metrics.overshoot_percent:.3f}% "
            f"steady={metrics.steady_state_error:.6f} "
            f"max_output={metrics.max_abs_output:.3f} "
            f"max_delta={metrics.max_output_delta:.3f}"
        )


def _write_csv(path, responses):
    """Write both signed responses in long-form CSV."""
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            (
                "scenario",
                "time_sec",
                "error_norm",
                "command_norm_per_sec",
                "actuator_rate_norm_per_sec",
            )
        )
        for name, response in responses.items():
            for sample in response.samples:
                writer.writerow(
                    (
                        name,
                        f"{sample.time_sec:.3f}",
                        f"{sample.error_norm:.9f}",
                        f"{sample.command_norm_per_sec:.9f}",
                        f"{sample.actuator_rate_norm_per_sec:.9f}",
                    )
                )


def _write_metrics(path, pid_config, simulation_config, responses):
    """Write configurations and metrics as stable JSON."""
    payload = {
        "pid_config": pid_config.__dict__,
        "simulation_config": simulation_config.__dict__,
        "responses": {
            name: response.metrics.as_dict()
            for name, response in responses.items()
        },
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_svg(path, responses):
    """Write a dependency-free SVG error curve."""
    width = 960
    height = 520
    left = 72
    right = 24
    top = 28
    bottom = 56
    plot_width = width - left - right
    plot_height = height - top - bottom
    duration = max(
        response.samples[-1].time_sec for response in responses.values()
    )
    error_limit = max(
        abs(sample.error_norm)
        for response in responses.values()
        for sample in response.samples
    ) * 1.08

    def x_value(time_sec):
        return left + time_sec / duration * plot_width

    def y_value(error):
        return top + (error_limit - error) / (2.0 * error_limit) * plot_height

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<g stroke="#d0d7de" stroke-width="1">',
    ]
    for second in range(int(duration) + 1):
        x = x_value(second)
        parts.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" '
            f'y2="{top + plot_height}"/>'
        )
    for ratio in (-1.0, -0.5, 0.0, 0.5, 1.0):
        y = y_value(error_limit * ratio)
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" '
            f'y2="{y:.2f}"/>'
        )
    parts.extend(
        [
            "</g>",
            '<g fill="#24292f" font-family="sans-serif" font-size="14">',
            f'<text x="{width / 2:.1f}" y="{height - 14}" '
            'text-anchor="middle">Time (s)</text>',
            f'<text x="18" y="{height / 2:.1f}" text-anchor="middle" '
            f'transform="rotate(-90 18 {height / 2:.1f})">'
            "Normalized image error</text>",
        ]
    )
    for second in range(int(duration) + 1):
        parts.append(
            f'<text x="{x_value(second):.2f}" y="{top + plot_height + 24}" '
            f'text-anchor="middle">{second}</text>'
        )
    for ratio in (-1.0, -0.5, 0.0, 0.5, 1.0):
        value = error_limit * ratio
        parts.append(
            f'<text x="{left - 10}" y="{y_value(value) + 5:.2f}" '
            f'text-anchor="end">{value:.2f}</text>'
        )
    parts.append("</g>")
    colors = {"positive": "#0969da", "negative": "#cf222e"}
    for name, response in responses.items():
        points = " ".join(
            f"{x_value(sample.time_sec):.2f},{y_value(sample.error_norm):.2f}"
            for sample in response.samples
        )
        parts.append(
            f'<polyline points="{points}" fill="none" '
            f'stroke="{colors[name]}" stroke-width="3"/>'
        )
    parts.extend(
        [
            '<g font-family="sans-serif" font-size="14" fill="#24292f">',
            f'<line x1="{left + 18}" y1="{top + 16}" '
            f'x2="{left + 54}" y2="{top + 16}" '
            f'stroke="{colors["positive"]}" stroke-width="3"/>',
            f'<text x="{left + 62}" y="{top + 21}">+0.6 step</text>',
            f'<line x1="{left + 150}" y1="{top + 16}" '
            f'x2="{left + 186}" y2="{top + 16}" '
            f'stroke="{colors["negative"]}" stroke-width="3"/>',
            f'<text x="{left + 194}" y="{top + 21}">-0.6 step</text>',
            "</g>",
            "</svg>",
        ]
    )
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
