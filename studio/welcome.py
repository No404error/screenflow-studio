from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from studio.settings import get_recent


class WelcomePage(QWidget):
    """Start page: new / open / recent projects (VS Code-like)."""

    new_requested = Signal()
    open_requested = Signal()
    open_path_requested = Signal(str)
    clear_recent_requested = Signal()

    def __init__(self, t: Callable[..., str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._t = t

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        self.title = QLabel()
        self.title.setStyleSheet("font-size: 22px; font-weight: 600;")
        lay.addWidget(self.title)

        self.subtitle = QLabel()
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet("color: #666;")
        lay.addWidget(self.subtitle)

        row = QHBoxLayout()
        self.btn_new = QPushButton()
        self.btn_new.clicked.connect(self.new_requested.emit)
        self.btn_open = QPushButton()
        self.btn_open.clicked.connect(self.open_requested.emit)
        row.addWidget(self.btn_new)
        row.addWidget(self.btn_open)
        row.addStretch(1)
        lay.addLayout(row)

        self.lbl_recent = QLabel()
        self.lbl_recent.setStyleSheet("font-weight: 600; margin-top: 12px;")
        lay.addWidget(self.lbl_recent)

        self.list = QListWidget()
        self.list.itemActivated.connect(self._activate)
        self.list.itemDoubleClicked.connect(self._activate)
        lay.addWidget(self.list, stretch=1)

        bottom = QHBoxLayout()
        self.btn_open_sel = QPushButton()
        self.btn_open_sel.clicked.connect(self._open_selected)
        self.btn_clear = QPushButton()
        self.btn_clear.clicked.connect(self.clear_recent_requested.emit)
        bottom.addWidget(self.btn_open_sel)
        bottom.addWidget(self.btn_clear)
        bottom.addStretch(1)
        lay.addLayout(bottom)

        self.retranslate()
        self.refresh()

    def t(self, key: str, **kwargs: object) -> str:
        return self._t(key, **kwargs)

    def retranslate(self) -> None:
        t = self.t
        self.title.setText(t("welcome_title"))
        self.subtitle.setText(t("welcome_subtitle"))
        self.btn_new.setText(t("act_new"))
        self.btn_open.setText(t("act_open"))
        self.lbl_recent.setText(t("recent_title"))
        self.btn_open_sel.setText(t("recent_open"))
        self.btn_clear.setText(t("recent_clear"))
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        recent = get_recent()
        if not recent:
            item = QListWidgetItem(self.t("recent_empty"))
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(item)
            self.btn_open_sel.setEnabled(False)
            self.btn_clear.setEnabled(False)
            return
        self.btn_open_sel.setEnabled(True)
        self.btn_clear.setEnabled(True)
        for entry in recent:
            text = f"{entry['name']}\n{entry['path']}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, entry["path"])
            self.list.addItem(item)

    def _activate(self, item: QListWidgetItem | None) -> None:
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.open_path_requested.emit(str(path))

    def _open_selected(self) -> None:
        item = self.list.currentItem()
        if item:
            self._activate(item)
