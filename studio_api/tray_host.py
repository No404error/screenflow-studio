"""Windows system tray for ScreenFlow Web Studio (optional elsewhere)."""

from __future__ import annotations

import sys
import threading
from typing import Any

from studio_api import lifecycle
from studio_api.settings import load_ui_settings

_icon: Any = None
_thread: threading.Thread | None = None


def _lang() -> str:
    lang = (load_ui_settings().get("lang") or "en").strip().lower()
    return "zh" if lang == "zh" else "en"


def _t(key: str) -> str:
    zh = {
        "tray_open": "打开 Studio",
        "tray_quit": "退出",
        "tray_tooltip": "ScreenFlow",
        "tray_dirty_title": "ScreenFlow",
        "tray_dirty_body": (
            "项目有未保存的更改。\n\n"
            "是 — 打开 Studio 以便保存\n"
            "否 — 丢弃更改并退出\n"
            "取消 — 返回"
        ),
    }
    en = {
        "tray_open": "Open Studio",
        "tray_quit": "Quit",
        "tray_tooltip": "ScreenFlow",
        "tray_dirty_title": "ScreenFlow",
        "tray_dirty_body": (
            "The project has unsaved changes.\n\n"
            "Yes — Open Studio to save\n"
            "No — Discard and quit\n"
            "Cancel — Go back"
        ),
    }
    table = zh if _lang() == "zh" else en
    return table.get(key, key)


def _make_icon_image():
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Soft teal disc + frame — readable at tray size, not purple Vite default.
    draw.ellipse((2, 2, size - 3, size - 3), fill=(46, 107, 98))
    draw.rounded_rectangle((16, 18, 48, 46), radius=4, outline=(236, 242, 240), width=3)
    draw.line((22, 28, 42, 28), fill=(236, 242, 240), width=2)
    draw.line((22, 36, 36, 36), fill=(196, 214, 210), width=2)
    return img


def _message_dirty_choice() -> str:
    """Return 'open' | 'quit' | 'cancel' via Win32 Yes/No/Cancel box."""
    if sys.platform != "win32":
        return "cancel"
    import ctypes

    MB_YESNOCANCEL = 0x00000003
    MB_ICONWARNING = 0x00000030
    MB_SETFOREGROUND = 0x00010000
    MB_TOPMOST = 0x00040000
    IDYES, IDNO = 6, 7
    flags = MB_YESNOCANCEL | MB_ICONWARNING | MB_SETFOREGROUND | MB_TOPMOST
    result = ctypes.windll.user32.MessageBoxW(
        None,
        _t("tray_dirty_body"),
        _t("tray_dirty_title"),
        flags,
    )
    if result == IDYES:
        return "open"
    if result == IDNO:
        return "quit"
    return "cancel"


def _on_open(icon: Any = None, item: Any = None) -> None:  # noqa: ARG001
    lifecycle.open_studio()


def _on_quit(icon: Any = None, item: Any = None) -> None:  # noqa: ARG001
    if lifecycle.is_editor_dirty():
        choice = _message_dirty_choice()
        if choice == "open":
            lifecycle.open_studio()
            return
        if choice == "cancel":
            return
        lifecycle.set_editor_dirty(False)
    lifecycle.perform_shutdown()


def start_tray() -> bool:
    """Start tray icon in a daemon thread. Returns False if unavailable."""
    global _icon, _thread
    if _icon is not None:
        return True
    try:
        import pystray
    except Exception:
        return False

    image = _make_icon_image()
    menu = pystray.Menu(
        pystray.MenuItem(lambda _: _t("tray_open"), _on_open, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda _: _t("tray_quit"), _on_quit),
    )
    icon = pystray.Icon("ScreenFlow", image, _t("tray_tooltip"), menu)
    _icon = icon

    def _stop() -> None:
        try:
            icon.stop()
        except Exception:
            pass

    lifecycle.set_tray_stop(_stop)

    def _run() -> None:
        try:
            icon.run()
        except Exception:
            pass

    _thread = threading.Thread(target=_run, name="screenflow-tray", daemon=True)
    _thread.start()
    return True


def stop_tray() -> None:
    global _icon, _thread
    icon = _icon
    _icon = None
    _thread = None
    if icon is not None:
        try:
            icon.stop()
        except Exception:
            pass
    lifecycle.set_tray_stop(None)
