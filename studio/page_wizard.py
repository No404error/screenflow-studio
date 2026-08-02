from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class NewPageWizard(QDialog):
    """
    Lightweight 3-step page creation:
    1) name  2) optional recognition image  3) open default actions?
    """

    def __init__(self, t: Callable[..., str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._t = t
        self.setModal(True)
        self.resize(420, 260)

        self.page_name = ""
        self.image_path: str | None = None
        self.edit_actions = False

        self.stack = QStackedWidget()
        self._build_step_name()
        self._build_step_image()
        self._build_step_actions()

        self.buttons = QDialogButtonBox()
        self.btn_back = self.buttons.addButton(
            QDialogButtonBox.StandardButton.Reset
        )
        self.btn_next = self.buttons.addButton(
            QDialogButtonBox.StandardButton.Yes
        )
        self.btn_cancel = self.buttons.addButton(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.btn_back.clicked.connect(self._back)
        self.btn_next.clicked.connect(self._next)
        self.btn_cancel.clicked.connect(self.reject)

        lay = QVBoxLayout(self)
        self.title = QLabel()
        self.title.setStyleSheet("font-weight: 600; font-size: 14px;")
        lay.addWidget(self.title)
        lay.addWidget(self.stack, stretch=1)
        lay.addWidget(self.buttons)

        self._step = 0
        self.retranslate()
        self._sync_nav()

    def t(self, key: str, **kwargs: object) -> str:
        return self._t(key, **kwargs)

    def retranslate(self) -> None:
        t = self.t
        self.setWindowTitle(t("wiz_title"))
        self.lbl_name.setText(t("dlg_page_name_label"))
        self.lbl_img_hint.setText(t("wiz_img_hint"))
        self.btn_pick_img.setText(t("asset_upload"))
        self.btn_clear_img.setText(t("wiz_skip_img"))
        self.chk_edit_actions.setText(t("wiz_edit_actions"))
        self.btn_cancel.setText(t("wiz_cancel"))
        self._sync_nav()

    def _build_step_name(self) -> None:
        w = QWidget()
        form = QFormLayout(w)
        self.ed_name = QLineEdit()
        self.lbl_name = QLabel()
        form.addRow(self.lbl_name, self.ed_name)
        self.stack.addWidget(w)

    def _build_step_image(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.lbl_img_hint = QLabel()
        self.lbl_img_hint.setWordWrap(True)
        lay.addWidget(self.lbl_img_hint)
        self.lbl_img_path = QLabel("—")
        self.lbl_img_path.setWordWrap(True)
        lay.addWidget(self.lbl_img_path)
        row = QHBoxLayout()
        self.btn_pick_img = QPushButton()
        self.btn_pick_img.clicked.connect(self._pick_image)
        self.btn_clear_img = QPushButton()
        self.btn_clear_img.clicked.connect(self._clear_image)
        row.addWidget(self.btn_pick_img)
        row.addWidget(self.btn_clear_img)
        lay.addLayout(row)
        lay.addStretch(1)
        self.stack.addWidget(w)

    def _build_step_actions(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.chk_edit_actions = QCheckBox()
        lay.addWidget(self.chk_edit_actions)
        lay.addStretch(1)
        self.stack.addWidget(w)

    def _pick_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self.t("dlg_image"), "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self.image_path = path
            self.lbl_img_path.setText(Path(path).name)

    def _clear_image(self) -> None:
        self.image_path = None
        self.lbl_img_path.setText("—")

    def _sync_nav(self) -> None:
        t = self.t
        titles = [t("wiz_step_name"), t("wiz_step_image"), t("wiz_step_done")]
        self.title.setText(titles[self._step])
        self.stack.setCurrentIndex(self._step)
        self.btn_back.setText(t("wiz_back"))
        self.btn_back.setEnabled(self._step > 0)
        self.btn_next.setText(
            t("wiz_finish") if self._step == 2 else t("wiz_next")
        )

    def _back(self) -> None:
        if self._step > 0:
            self._step -= 1
            self._sync_nav()

    def _next(self) -> None:
        if self._step == 0:
            name = self.ed_name.text().strip()
            if not name:
                self.ed_name.setFocus()
                return
            self.page_name = name
            self._step = 1
            self._sync_nav()
            return
        if self._step == 1:
            self._step = 2
            self._sync_nav()
            return
        self.edit_actions = self.chk_edit_actions.isChecked()
        self.accept()
