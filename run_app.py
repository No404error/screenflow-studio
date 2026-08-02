# -*- coding: utf-8 -*-
"""
Unified app entry (packaged as ScreenFlow.exe).

Default → Studio UI.
With --engine-runner → elevated/plain engine child (same binary, second process).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from studio.elevate import ENGINE_RUNNER_FLAG


def _run_studio() -> None:
    # Windows: importing pyautogui (via engine) calls SetProcessDPIAware and locks
    # process DPI before QApplication. Qt then fails to set Per-Monitor V2.
    # Neutralize only for Studio; Runner child keeps normal DPI setup.
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

    run_studio()


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if ENGINE_RUNNER_FLAG in args:
        args = [a for a in args if a != ENGINE_RUNNER_FLAG]
        # Match run_runner.py: detach console when started via python.exe / UAC.
        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.kernel32.FreeConsole()
            except Exception:
                pass
        from run_runner import main as runner_main

        return int(runner_main(args))
    _run_studio()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
