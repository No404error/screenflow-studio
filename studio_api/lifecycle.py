"""App lifecycle: editor dirty flag, graceful shutdown of uvicorn + tray."""

from __future__ import annotations

import threading
import webbrowser
from typing import Any, Callable

_lock = threading.Lock()
_editor_dirty = False
_studio_url = "http://127.0.0.1:8787"
_server: Any = None
_tray_stop: Callable[[], None] | None = None
_shutting_down = False


def configure(*, studio_url: str) -> None:
    global _studio_url
    _studio_url = studio_url.rstrip("/")


def studio_url() -> str:
    return _studio_url


def set_server(server: Any) -> None:
    global _server
    _server = server


def set_tray_stop(cb: Callable[[], None] | None) -> None:
    global _tray_stop
    _tray_stop = cb


def set_editor_dirty(dirty: bool) -> None:
    global _editor_dirty
    with _lock:
        _editor_dirty = bool(dirty)


def is_editor_dirty() -> bool:
    with _lock:
        return _editor_dirty


def is_shutting_down() -> bool:
    with _lock:
        return _shutting_down


def open_studio() -> None:
    webbrowser.open(_studio_url)


def perform_shutdown() -> dict[str, Any]:
    """Stop engine, tray, and uvicorn. Safe to call multiple times."""
    global _shutting_down
    with _lock:
        if _shutting_down:
            return {"ok": True, "status": "already"}
        _shutting_down = True

    try:
        from studio_api.engine_bridge import bridge

        bridge.stop()
    except Exception:
        pass

    stop_tray = _tray_stop
    if stop_tray is not None:
        try:
            stop_tray()
        except Exception:
            pass

    server = _server
    if server is not None:
        server.should_exit = True

    return {"ok": True, "status": "shutting_down"}


def reset_for_tests() -> None:
    """Clear lifecycle state between unit tests."""
    global _editor_dirty, _server, _tray_stop, _shutting_down
    with _lock:
        _editor_dirty = False
        _shutting_down = False
    _server = None
    _tray_stop = None

