"""Upload helper: show full-page capture at native scale; optional drag-rect crop + ROI."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from screenflow.roi import roi_from_pixel_rect


def _bgr_to_qpixmap(img: np.ndarray) -> QPixmap:
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format.Format_RGB888).copy()
    return QPixmap.fromImage(qimg)


class _CropCanvas(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pix = QPixmap()
        self._origin: QPoint | None = None
        self._current: QPoint | None = None
        self.setMouseTracking(True)

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._pix = pixmap
        self.setFixedSize(pixmap.size())
        self.clear_selection()

    def selection_rect(self) -> QRect | None:
        if self._origin is None or self._current is None:
            return None
        return QRect(self._origin, self._current).normalized()

    def clear_selection(self) -> None:
        self._origin = None
        self._current = None
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self._current = self._origin
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._origin is not None:
            self._current = event.position().toPoint()
            self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        if not self._pix.isNull():
            painter.drawPixmap(0, 0, self._pix)
        rect = self.selection_rect()
        if rect is not None and rect.width() > 2 and rect.height() > 2:
            painter.setPen(QPen(QColor(0, 180, 80), 2, Qt.PenStyle.SolidLine))
            painter.setBrush(QColor(0, 180, 80, 40))
            painter.drawRect(rect)


class RoiCropDialog(QDialog):
    """
    Top-level fullscreen window (not a child of Studio).

    Returns via ``outcome()`` after accept:
      (image_path_to_upload, roi_or_none)
    roi is [y0,y1,x0,x1] on the original full capture; None = full-frame search.
    """

    def __init__(
        self,
        image_path: str | Path,
        t: Callable[..., str],
        _parent: QWidget | None = None,
    ) -> None:
        # Always a global top-level window so fullscreen is not clipped by Studio.
        super().__init__(None)
        self._t = t
        self._src = Path(image_path)
        self._outcome_path: Path | None = None
        self._outcome_roi: list[float] | None = None
        self._temp_files: list[Path] = []
        self._view_scale = 1.0

        data = np.fromfile(str(self._src), dtype=np.uint8)
        self._bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if self._bgr is None:
            raise FileNotFoundError(self._src)
        self._oh, self._ow = self._bgr.shape[:2]
        # Native 1:1 pixels for accurate ROI (scroll when larger than the screen).
        full_pix = _bgr_to_qpixmap(self._bgr)

        self.setWindowTitle(t("roi_crop_title"))
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        self.hint = QLabel(t("roi_crop_hint"))
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._canvas = _CropCanvas()
        self._canvas.set_pixmap(full_pix)
        self._scroll.setWidget(self._canvas)
        lay.addWidget(self._scroll, stretch=1)

        row = QHBoxLayout()
        self.btn_clear = QPushButton(t("roi_crop_clear"))
        self.btn_clear.clicked.connect(self._canvas.clear_selection)
        row.addWidget(self.btn_clear)
        row.addStretch(1)
        lay.addLayout(row)

        buttons = QDialogButtonBox()
        self.btn_use_sel = buttons.addButton(
            t("roi_crop_use_selection"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.btn_full = buttons.addButton(
            t("roi_crop_use_full"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.btn_cancel = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.btn_use_sel.clicked.connect(self._accept_selection)
        self.btn_full.clicked.connect(self._accept_full)
        self.btn_cancel.clicked.connect(self.reject)
        lay.addWidget(buttons)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            self.setGeometry(screen.geometry())
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)

    def t(self, key: str, **kwargs: object) -> str:
        return self._t(key, **kwargs)

    def outcome(self) -> tuple[Path, list[float] | None] | None:
        if self._outcome_path is None:
            return None
        return self._outcome_path, self._outcome_roi

    def _view_to_orig(self, rect: QRect) -> tuple[int, int, int, int]:
        s = self._view_scale if self._view_scale > 0 else 1.0
        x0 = int(rect.left() / s)
        y0 = int(rect.top() / s)
        x1 = int(rect.right() / s) + 1
        y1 = int(rect.bottom() / s) + 1
        x0 = max(0, min(x0, self._ow - 1))
        y0 = max(0, min(y0, self._oh - 1))
        x1 = max(x0 + 1, min(x1, self._ow))
        y1 = max(y0 + 1, min(y1, self._oh))
        return x0, y0, x1, y1

    def _accept_selection(self) -> None:
        rect = self._canvas.selection_rect()
        if rect is None or rect.width() < 4 or rect.height() < 4:
            QMessageBox.information(
                self, self.t("err_title"), self.t("roi_crop_need_selection")
            )
            return
        x0, y0, x1, y1 = self._view_to_orig(rect)
        roi = roi_from_pixel_rect(x0, y0, x1, y1, width=self._ow, height=self._oh)
        if roi is None:
            QMessageBox.information(
                self, self.t("err_title"), self.t("roi_crop_need_selection")
            )
            return
        crop = self._bgr[y0:y1, x0:x1]
        fd, tmp_name = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        tmp = Path(tmp_name)
        ok, buf = cv2.imencode(".png", crop)
        if not ok:
            QMessageBox.critical(self, self.t("err_title"), self.t("roi_crop_failed"))
            return
        buf.tofile(str(tmp))
        self._temp_files.append(tmp)
        self._outcome_path = tmp
        self._outcome_roi = roi
        self.accept()

    def _accept_full(self) -> None:
        self._outcome_path = self._src
        self._outcome_roi = None
        self.accept()


def prompt_upload_with_roi(
    parent: QWidget | None,
    t: Callable[..., str],
    image_path: str | Path,
) -> tuple[Path, list[float] | None] | None:
    """
    Open a global top-level fullscreen crop window.
    Returns (path, roi) or None if cancelled.
    path may be a temp cropped PNG; roi None means full-frame search.
    """
    try:
        dlg = RoiCropDialog(image_path, t, parent)
    except Exception as exc:
        QMessageBox.critical(parent, t("err_title"), str(exc))
        return None
    # exec() blocks Studio until the independent window closes.
    ok = dlg.exec() == QDialog.DialogCode.Accepted
    out = dlg.outcome() if ok else None
    dlg.close()
    return out
