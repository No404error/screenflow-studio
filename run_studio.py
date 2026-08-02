# -*- coding: utf-8 -*-
"""Launch ScreenFlow Studio (PySide6)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Windows: importing pyautogui (via engine) calls SetProcessDPIAware and locks
# process DPI before QApplication. Qt then fails to set Per-Monitor V2 and
# prints "SetProcessDpiAwarenessContext() failed: Access is denied."
# Neutralize those calls only for Studio; the elevated Runner still gets
# pyautogui's normal DPI setup when launched as its own process.
if sys.platform == "win32":
    try:
        import ctypes

        ctypes.windll.user32.SetProcessDPIAware = lambda: 1  # type: ignore[method-assign]
        ctypes.windll.shcore.SetProcessDpiAwareness = (  # type: ignore[method-assign]
            lambda *_a, **_k: 0
        )
    except Exception:
        pass

from studio.app import run_studio

if __name__ == "__main__":
    run_studio()
