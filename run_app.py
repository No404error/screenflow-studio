# -*- coding: utf-8 -*-
"""
Unified app entry (packaged as ScreenFlow.exe).

Default → Web Studio (API + UI).
With --engine-runner → elevated/plain engine child (same binary, second process).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from screenflow.elevate import ENGINE_RUNNER_FLAG


def _ensure_stdio() -> None:
    """Windowed (console=False) PyInstaller builds leave stdout/stderr as None."""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    _ensure_stdio()
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

    from run_web_studio import main as web_main

    return int(web_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
