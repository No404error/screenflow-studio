"""Floating image preview on hover (shared by asset pickers and lists)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QEvent, QObject, QPoint, QTimer, Qt
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QLabel, QWidget


def load_preview_pixmap(path: Path | None, max_edge: int = 280) -> QPixmap | None:
    if path is None or not path.is_file():
        return None
    pix = QPixmap(str(path))
    if pix.isNull():
        return None
    return pix.scaled(
        max_edge,
        max_edge,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


class HoverImagePreview(QObject):
    """
    Show a large floating thumbnail while the pointer is over a widget.

    Use path_getter for a single current path, or path_at(local_pos) for lists.
    For QComboBox, also previews items inside the popup list.
    """

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        max_edge: int = 280,
        delay_ms: int = 220,
    ) -> None:
        super().__init__(parent)
        self._max_edge = max_edge
        self._delay_ms = delay_ms
        self._path_getter: Callable[[], Path | None] | None = None
        self._path_at: Callable[[QPoint], Path | None] | None = None
        self._combo: QComboBox | None = None
        self._combo_path_for_data: Callable[[Any], Path | None] | None = None
        self._watched: list[QWidget] = []

        self._popup = QLabel(
            None,
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self._popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._popup.setStyleSheet(
            "QLabel { background: #1e1e1e; border: 1px solid #888; padding: 4px; }"
        )
        self._popup.hide()

        self._show_timer = QTimer(self)
        self._show_timer.setSingleShot(True)
        self._show_timer.timeout.connect(self._reveal)
        self._pending_path: Path | None = None

    def clear(self) -> None:
        self._show_timer.stop()
        self._popup.hide()
        self._pending_path = None

    def attach(
        self,
        widget: QWidget,
        *,
        path_getter: Callable[[], Path | None] | None = None,
        path_at: Callable[[QPoint], Path | None] | None = None,
    ) -> None:
        self._path_getter = path_getter
        self._path_at = path_at
        if widget not in self._watched:
            widget.setMouseTracking(True)
            widget.installEventFilter(self)
            self._watched.append(widget)

    def attach_combo(
        self,
        combo: QComboBox,
        path_for_data: Callable[[Any], Path | None],
    ) -> None:
        self._combo = combo
        self._combo_path_for_data = path_for_data
        self.attach(combo, path_getter=lambda: path_for_data(combo.currentData()))
        view = combo.view()
        if isinstance(view, QAbstractItemView):
            view.setMouseTracking(True)
            vp = view.viewport()
            vp.setMouseTracking(True)
            if vp not in self._watched:
                vp.installEventFilter(self)
                self._watched.append(vp)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        et = event.type()
        if et == QEvent.Type.Leave:
            self.clear()
            return False
        if et == QEvent.Type.Hide:
            self.clear()
            return False
        if et in (QEvent.Type.MouseMove, QEvent.Type.Enter, QEvent.Type.HoverMove):
            path = self._resolve_path(obj, event)
            if path is None:
                self.clear()
            else:
                self._schedule(path)
            return False
        return False

    def _resolve_path(self, obj: QObject, event: QEvent) -> Path | None:
        if (
            self._combo is not None
            and self._combo_path_for_data is not None
            and obj is self._combo.view().viewport()
        ):
            view = self._combo.view()
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()  # type: ignore[attr-defined]
            idx = view.indexAt(pos)
            if not idx.isValid():
                return None
            data = self._combo.itemData(idx.row())
            return self._combo_path_for_data(data)
        if not isinstance(obj, QWidget):
            return None
        if self._path_at is not None and hasattr(event, "position"):
            return self._path_at(event.position().toPoint())  # type: ignore[attr-defined]
        if self._path_at is not None and hasattr(event, "pos"):
            return self._path_at(event.pos())  # type: ignore[attr-defined]
        if self._path_getter is not None:
            return self._path_getter()
        return None

    def _schedule(self, path: Path) -> None:
        if self._pending_path == path and self._popup.isVisible():
            return
        self._pending_path = path
        self._show_timer.start(self._delay_ms)

    def _reveal(self) -> None:
        path = self._pending_path
        pix = load_preview_pixmap(path, self._max_edge)
        if pix is None:
            self._popup.hide()
            return
        self._popup.setPixmap(pix)
        self._popup.adjustSize()
        self._place_popup()
        self._popup.show()

    def _place_popup(self) -> None:
        cursor = QCursor.pos()
        geo = self._popup.frameGeometry()
        x = cursor.x() + 16
        y = cursor.y() + 16
        # Keep on screen roughly via available geometry of primary-ish screen
        screen = self._popup.screen()
        if screen is not None:
            avail = screen.availableGeometry()
            if x + geo.width() > avail.right():
                x = cursor.x() - geo.width() - 16
            if y + geo.height() > avail.bottom():
                y = cursor.y() - geo.height() - 16
            x = max(avail.left(), x)
            y = max(avail.top(), y)
        self._popup.move(x, y)
