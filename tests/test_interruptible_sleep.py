"""Interruptible sleeps honor pause/stop."""

from __future__ import annotations

from screenflow.input import InputController
from screenflow.logfmt import EngineLog
from screenflow.models import RuntimeConfig


def test_interruptible_sleep_stops_when_not_running():
    ctrl = InputController(RuntimeConfig(), EngineLog())
    flags = {"n": 0}

    def is_running() -> bool:
        flags["n"] += 1
        return flags["n"] < 3

    assert ctrl.interruptible_sleep(10.0, is_running, slice_s=0.01) is False
    assert flags["n"] >= 3


def test_interruptible_sleep_completes():
    ctrl = InputController(RuntimeConfig(), EngineLog())
    assert ctrl.interruptible_sleep(0.05, lambda: True, slice_s=0.02) is True
