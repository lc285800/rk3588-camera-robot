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

"""A conservative Linux sysfs PWM channel for initial servo validation."""

from dataclasses import dataclass
import math
from pathlib import Path
import time


@dataclass(frozen=True)
class ServoPwmConfig:
    """Validated PWM mapping and provisional pulse limits."""

    pwmchip: int = 3
    channel: int = 0
    period_ns: int = 20_000_000
    center_ns: int = 1_500_000
    min_pulse_ns: int = 1_450_000
    max_pulse_ns: int = 1_550_000
    polarity: str = "normal"
    export_timeout_sec: float = 1.0

    def __post_init__(self):
        """Reject ambiguous mappings and unsafe pulse bounds."""
        integer_values = (
            self.pwmchip,
            self.channel,
            self.period_ns,
            self.center_ns,
            self.min_pulse_ns,
            self.max_pulse_ns,
        )
        if any(isinstance(value, bool) or not isinstance(value, int)
               for value in integer_values):
            raise TypeError("PWM identifiers and timing values must be integers")
        if self.pwmchip < 0 or self.channel < 0:
            raise ValueError("PWM identifiers must be non-negative")
        if not 0 < self.min_pulse_ns <= self.center_ns <= self.max_pulse_ns:
            raise ValueError("pulse bounds must contain the positive center pulse")
        if self.max_pulse_ns >= self.period_ns:
            raise ValueError("maximum pulse must be shorter than the period")
        if self.polarity not in ("normal", "inversed"):
            raise ValueError("polarity must be normal or inversed")
        if (not math.isfinite(self.export_timeout_sec)
                or self.export_timeout_sec <= 0.0):
            raise ValueError("export timeout must be finite and positive")

    def validate_pulse(self, pulse_ns):
        """Return a pulse inside the explicitly tested provisional bounds."""
        if isinstance(pulse_ns, bool) or not isinstance(pulse_ns, int):
            raise TypeError("pulse_ns must be an integer")
        if not self.min_pulse_ns <= pulse_ns <= self.max_pulse_ns:
            raise ValueError(
                f"pulse_ns must be within {self.min_pulse_ns}.."
                f"{self.max_pulse_ns}"
            )
        return pulse_ns


class PosixSysfsIo:
    """Perform the minimal filesystem operations used by sysfs PWM."""

    @staticmethod
    def exists(path):
        """Return whether a sysfs path currently exists."""
        return path.exists()

    @staticmethod
    def write(path, value):
        """Write one scalar value to a sysfs attribute."""
        path.write_text(str(value), encoding="ascii")


class SysfsPwmChannel:
    """Own one previously unexported PWM channel and clean it up safely."""

    def __init__(self, config, sysfs_root="/sys/class/pwm", io=None):
        """Prepare paths without exporting or enabling the channel."""
        if not isinstance(config, ServoPwmConfig):
            raise TypeError("config must be a ServoPwmConfig")
        self.config = config
        self._root = Path(sysfs_root)
        self._io = io if io is not None else PosixSysfsIo()
        self._chip_path = self._root / f"pwmchip{config.pwmchip}"
        self._channel_path = self._chip_path / f"pwm{config.channel}"
        self._exported_by_us = False
        self._opened = False
        self._enabled = False

    @property
    def opened(self):
        """Return whether this object configured the channel."""
        return self._opened

    @property
    def enabled(self):
        """Return whether this object requested PWM output."""
        return self._enabled

    def open(self):
        """Export and configure a disabled channel at the center pulse."""
        if self._opened:
            raise RuntimeError("PWM channel is already open")
        if not self._io.exists(self._chip_path):
            raise FileNotFoundError(f"PWM chip does not exist: {self._chip_path}")
        if self._io.exists(self._channel_path):
            raise RuntimeError("PWM channel is already exported by another owner")

        try:
            self._io.write(self._chip_path / "export", self.config.channel)
            self._exported_by_us = True
            self._wait_for_channel()
            self._io.write(
                self._channel_path / "period",
                self.config.period_ns,
            )
            self._io.write(
                self._channel_path / "duty_cycle",
                self.config.center_ns,
            )
            self._io.write(
                self._channel_path / "polarity",
                self.config.polarity,
            )
            self._opened = True
        except Exception:
            self.close()
            raise
        return self

    def enable_center(self):
        """Enable output only after restoring the configured center pulse."""
        self._require_open()
        self._io.write(
            self._channel_path / "duty_cycle",
            self.config.center_ns,
        )
        try:
            self._io.write(self._channel_path / "enable", 1)
        except OSError:
            try:
                self._io.write(self._channel_path / "enable", 0)
            except OSError:
                pass
            raise
        self._enabled = True

    def set_pulse_ns(self, pulse_ns):
        """Set one pulse after applying the provisional hard bounds."""
        self._require_open()
        pulse_ns = self.config.validate_pulse(pulse_ns)
        self._io.write(self._channel_path / "duty_cycle", pulse_ns)

    def disable(self):
        """Disable output if this object currently considers it enabled."""
        if self._opened and self._enabled:
            self._io.write(self._channel_path / "enable", 0)
            self._enabled = False

    def close(self):
        """Attempt disable and unexport even when one cleanup step fails."""
        cleanup_error = None
        if self._opened and self._enabled:
            try:
                self._io.write(self._channel_path / "enable", 0)
            except OSError as error:
                cleanup_error = error
            self._enabled = False
        if self._exported_by_us:
            try:
                self._io.write(
                    self._chip_path / "unexport",
                    self.config.channel,
                )
            except OSError as error:
                if cleanup_error is None:
                    cleanup_error = error
            self._exported_by_us = False
        self._opened = False
        if cleanup_error is not None:
            raise cleanup_error

    def _wait_for_channel(self):
        """Wait briefly for the kernel to create the exported attributes."""
        deadline = time.monotonic() + self.config.export_timeout_sec
        while time.monotonic() < deadline:
            if self._io.exists(self._channel_path):
                return
            time.sleep(0.01)
        raise TimeoutError(f"PWM export timed out: {self._channel_path}")

    def _require_open(self):
        """Reject output operations before successful configuration."""
        if not self._opened:
            raise RuntimeError("PWM channel is not open")

    def __enter__(self):
        """Export and configure the channel for a context block."""
        return self.open()

    def __exit__(self, exc_type, _exc_value, _traceback):
        """Request safe cleanup whenever a context block ends."""
        try:
            self.close()
        except OSError:
            if exc_type is None:
                raise
        return False
