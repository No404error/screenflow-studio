from __future__ import annotations

import time
from typing import Callable

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

    def interruptible_sleep(
        self,
        seconds: float,
        is_running: Callable[[], bool] | None = None,
        *,
        slice_s: float = 0.05,
    ) -> bool:
        """
        Sleep up to `seconds`, checking is_running between slices.
        Returns False if interrupted (paused/stopped).
        """
        if seconds <= 0:
            return True
        deadline = time.time() + float(seconds)
        while True:
            if is_running is not None and not is_running():
                return False
            remain = deadline - time.time()
            if remain <= 0:
                return True
            time.sleep(min(slice_s, remain))

    def wait_ready(self, is_running: Callable[[], bool] | None = None) -> bool:
        wait = self.runtime.action_cooldown - (time.time() - self._last_action_at)
        if wait > 0:
            self.log.detail(f"  cooldown {wait:.2f}s")
            if not self.interruptible_sleep(wait, is_running):
                return False
        return True

    def click(
        self,
        x: int,
        y: int,
        *,
        force: bool = False,
        is_running: Callable[[], bool] | None = None,
    ) -> bool:
        if not force:
            if not self.wait_ready(is_running):
                return False
        self._last_action_at = time.time()
        pydirectinput.moveTo(x, y)
        if not self.interruptible_sleep(0.05, is_running):
            return False
        pydirectinput.click()
        return self.interruptible_sleep(self.runtime.action_delay, is_running)

    def tap_key(
        self,
        key: str,
        hold: float | None = None,
        *,
        is_running: Callable[[], bool] | None = None,
    ) -> bool:
        if hold is None:
            hold = 0.1 if key == "esc" else 0.05
        if not self.wait_ready(is_running):
            return False
        self._last_action_at = time.time()
        pydirectinput.keyDown(key)
        if not self.interruptible_sleep(hold, is_running):
            try:
                pydirectinput.keyUp(key)
            except Exception:
                pass
            return False
        pydirectinput.keyUp(key)
        return self.interruptible_sleep(self.runtime.action_delay, is_running)

    def hold_key(
        self,
        key: str,
        seconds: float,
        *,
        is_running: Callable[[], bool] | None = None,
    ) -> bool:
        if not self.wait_ready(is_running):
            return False
        self._last_action_at = time.time()
        pydirectinput.keyDown(key)
        if not self.interruptible_sleep(seconds, is_running):
            try:
                pydirectinput.keyUp(key)
            except Exception:
                pass
            return False
        pydirectinput.keyUp(key)
        return self.interruptible_sleep(self.runtime.action_delay, is_running)
