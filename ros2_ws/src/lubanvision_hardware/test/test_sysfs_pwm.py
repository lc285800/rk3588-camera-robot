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

"""Tests for the safety-bounded sysfs PWM channel."""

from pathlib import Path

import pytest

from lubanvision_hardware.sysfs_pwm import ServoPwmConfig, SysfsPwmChannel


class FakeSysfsIo:
    """Emulate kernel-created PWM attributes and record scalar writes."""

    def __init__(self, root, config):
        """Create one pwmchip without exporting its channel."""
        self.root = Path(root)
        self.config = config
        self.chip = self.root / f"pwmchip{config.pwmchip}"
        self.channel = self.chip / f"pwm{config.channel}"
        self.paths = {self.chip}
        self.writes = []
        self.fail_on_name = None
        self.create_channel_on_export = True

    def exists(self, path):
        """Return whether the fake kernel currently exposes a path."""
        return Path(path) in self.paths

    def write(self, path, value):
        """Record a write and emulate export or unexport side effects."""
        path = Path(path)
        if path.name == self.fail_on_name:
            raise OSError(f"injected {path.name} failure")
        self.writes.append((path.name, str(value)))
        if path.name == "export" and self.create_channel_on_export:
            self.paths.add(self.channel)
        elif path.name == "unexport":
            self.paths.discard(self.channel)


def make_channel(config=None):
    """Return a channel connected to an isolated fake sysfs tree."""
    config = config or ServoPwmConfig()
    root = Path("/fake/sys/class/pwm")
    io = FakeSysfsIo(root, config)
    return SysfsPwmChannel(config, sysfs_root=root, io=io), io


def test_default_config_matches_proven_smoke_range():
    """Defaults reproduce only the pulse range already smoke tested."""
    config = ServoPwmConfig()

    assert config.period_ns == 20_000_000
    assert config.center_ns == 1_900_000
    assert config.min_pulse_ns == 1_850_000
    assert config.max_pulse_ns == 1_950_000


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pwmchip": -1},
        {"channel": -1},
        {"min_pulse_ns": 0},
        {"min_pulse_ns": 1_910_000},
        {"max_pulse_ns": 1_890_000},
        {"period_ns": 1_550_000},
        {"polarity": "unknown"},
        {"export_timeout_sec": 0.0},
        {"export_timeout_sec": float("inf")},
    ],
)
def test_invalid_config_is_rejected(kwargs):
    """Unsafe mappings, timings, polarity, and timeout fail closed."""
    with pytest.raises((TypeError, ValueError)):
        ServoPwmConfig(**kwargs)


@pytest.mark.parametrize("pulse", [True, 1_900_000.0, 1_849_999, 1_950_001])
def test_invalid_runtime_pulse_is_rejected(pulse):
    """Non-integer and out-of-range commands never reach sysfs."""
    channel, io = make_channel()
    channel.open()
    writes_before = list(io.writes)

    with pytest.raises((TypeError, ValueError)):
        channel.set_pulse_ns(pulse)

    assert io.writes == writes_before


def test_open_configures_disabled_center_before_enable():
    """The channel starts disabled and enabling restores center first."""
    channel, io = make_channel()

    channel.open()
    assert channel.opened
    assert not channel.enabled
    channel.enable_center()

    assert channel.enabled
    assert io.writes == [
        ("export", "0"),
        ("period", "20000000"),
        ("duty_cycle", "1900000"),
        ("polarity", "normal"),
        ("duty_cycle", "1900000"),
        ("enable", "1"),
    ]


def test_context_disables_and_unexports_after_exception():
    """An application failure still disables and releases the channel."""
    channel, io = make_channel()

    with pytest.raises(RuntimeError, match="application failure"):
        with channel:
            channel.enable_center()
            channel.set_pulse_ns(1_850_000)
            raise RuntimeError("application failure")

    assert not channel.opened
    assert not channel.enabled
    assert io.writes[-2:] == [("enable", "0"), ("unexport", "0")]


def test_existing_export_is_never_taken_over():
    """A channel owned by another process is rejected without writes."""
    channel, io = make_channel()
    io.paths.add(io.channel)

    with pytest.raises(RuntimeError, match="another owner"):
        channel.open()

    assert io.writes == []


def test_export_timeout_still_requests_unexport():
    """A kernel export timeout cannot leave a userspace consumer behind."""
    config = ServoPwmConfig(export_timeout_sec=0.01)
    channel, io = make_channel(config)
    io.create_channel_on_export = False

    with pytest.raises(TimeoutError, match="export timed out"):
        channel.open()

    assert io.writes == [("export", "0"), ("unexport", "0")]
    assert not channel.opened


def test_unexport_is_attempted_when_disable_fails():
    """Cleanup still releases the channel after a disable write error."""
    channel, io = make_channel()
    channel.open()
    channel.enable_center()
    io.fail_on_name = "enable"

    with pytest.raises(OSError, match="injected enable failure"):
        channel.close()

    assert ("unexport", "0") in io.writes
    assert not channel.opened


def test_operations_before_open_fail_without_writes():
    """Output operations cannot silently configure an unopened channel."""
    channel, io = make_channel()

    with pytest.raises(RuntimeError, match="not open"):
        channel.enable_center()
    with pytest.raises(RuntimeError, match="not open"):
        channel.set_pulse_ns(1_900_000)

    assert io.writes == []
