"""Section-level help (?) next to group titles — one hover/click covers the whole block."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QToolButton,
    QWidget,
)


class SectionHelpButton(QToolButton):
    """
    Compact '?' control. Hover shows the full section help; click pins it in a dialog.
    """

    def __init__(
        self,
        t: Callable[..., str],
        help_key: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._t = t
        self._help_key = help_key
        self.setText("?")
        self.setAutoRaise(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setStyleSheet(
            "QToolButton { color: #555; font-weight: 700; padding: 0 4px; border: none; }"
            "QToolButton:hover { color: #0b57d0; }"
        )
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.clicked.connect(self._show_dialog)
        self.retranslate()

    @property
    def help_key(self) -> str:
        return self._help_key

    def set_help_key(self, key: str) -> None:
        self._help_key = key
        self.retranslate()

    def help_text(self) -> str:
        text = self._t(self._help_key)
        return text if text != self._help_key else self._t("help_missing")

    def retranslate(self) -> None:
        text = self.help_text()
        self.setToolTip(text)
        self.setAccessibleName(self._t("help_button_a11y"))

    def _show_dialog(self) -> None:
        QMessageBox.information(
            self.window() if self.window() else self,
            self._t("help_dialog_title"),
            self.help_text(),
        )


def section_title_row(
    t: Callable[..., str],
    title_key: str,
    help_key: str,
    *,
    parent: QWidget | None = None,
) -> tuple[QWidget, QLabel, SectionHelpButton]:
    """Title label + stretch + '?' — use above a form or instead of a bare group title."""
    row = QWidget(parent)
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    title = QLabel()
    title.setStyleSheet("font-weight: 600;")
    help_btn = SectionHelpButton(t, help_key)
    lay.addWidget(title)
    lay.addStretch(1)
    lay.addWidget(help_btn)

    def apply() -> None:
        title.setText(t(title_key))
        help_btn.retranslate()

    row.retranslate = apply  # type: ignore[attr-defined]
    apply()
    return row, title, help_btn


def toolbutton_with_help(
    tool_btn: QToolButton,
    help_btn: SectionHelpButton,
    *,
    parent: QWidget | None = None,
) -> QWidget:
    """Fold control left-aligned; '?' on the right (same rhythm as section titles)."""
    wrap = QWidget(parent)
    lay = QHBoxLayout(wrap)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    tool_btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    tool_btn.setAutoRaise(True)
    lay.addWidget(tool_btn, 0, Qt.AlignmentFlag.AlignLeft)
    lay.addStretch(1)
    lay.addWidget(help_btn, 0, Qt.AlignmentFlag.AlignRight)
    return wrap
