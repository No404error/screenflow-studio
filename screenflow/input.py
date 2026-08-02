from __future__ import annotations

import time

import pydirectinput
import pyautogui

from screenflow.logfmt import EngineLog
from screenflow.models import RuntimeConfig

pyautogui.FAILSAFE = False
pydirectinput.PAUSE = 0.05


class InputController:
    """Foreground mouse/keyboard with action cooldown."""

    def __init__(self, runtime: RuntimeConfig, log: EngineLog) -> None:
        self.runtime = runtime
        self.log = log
        self._last_action_at = 0.0

    def wait_ready(self) -> None:
        wait = self.runtime.action_cooldown - (time.time() - self._last_action_at)
        if wait > 0:
            self.log.detail(f"  cooldown {wait:.2f}s")
            time.sleep(wait)

    def click(self, x: int, y: int, *, force: bool = False) -> None:
        if not force:
            self.wait_ready()
        self._last_action_at = time.time()
        pydirectinput.moveTo(x, y)
        time.sleep(0.05)
        pydirectinput.click()
        time.sleep(self.runtime.action_delay)

    def tap_key(self, key: str, hold: float | None = None) -> None:
        if hold is None:
            hold = 0.1 if key == "esc" else 0.05
        self.wait_ready()
        self._last_action_at = time.time()
        pydirectinput.keyDown(key)
        time.sleep(hold)
        pydirectinput.keyUp(key)
        time.sleep(self.runtime.action_delay)

    def hold_key(self, key: str, seconds: float) -> None:
        self.wait_ready()
        self._last_action_at = time.time()
        pydirectinput.keyDown(key)
        time.sleep(seconds)
        pydirectinput.keyUp(key)
        time.sleep(self.runtime.action_delay)
