from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from screenflow.assets import (
    PageAsset,
    delete_page_asset,
    list_page_assets,
    resolve_asset_path,
    upload_page_asset,
)
from screenflow.models import Project
from studio.hover_preview import HoverImagePreview, load_preview_pixmap
from studio.section_help import section_title_row

_ICON = 48


class AssetKindList(QWidget):
    """List + upload/delete for one kind (detect or click) on a page."""

    changed = Signal()
    selection_changed = Signal()

    def __init__(
        self,
        t: Callable[..., str],
        kind: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._t = t
        self.kind = kind
        self.project: Project | None = None
        self.page_id: str | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.setIconSize(QSize(_ICON, _ICON))
        self.list.setMouseTracking(True)
        self.list.currentItemChanged.connect(self._on_sel)
        lay.addWidget(self.list, stretch=1)

        self._hover = HoverImagePreview(self)
        self._hover.attach(self.list.viewport(), path_at=self._path_at)

        row = QHBoxLayout()
        self.btn_upload = QPushButton()
        self.btn_upload.clicked.connect(self._upload)
        self.btn_delete = QPushButton()
        self.btn_delete.clicked.connect(self._delete)
        row.addWidget(self.btn_upload)
        row.addWidget(self.btn_delete)
        lay.addLayout(row)
        self.retranslate()

    def t(self, key: str, **kwargs: object) -> str:
        return self._t(key, **kwargs)

    def retranslate(self) -> None:
        self.btn_upload.setText(self.t("asset_upload"))
        self.btn_delete.setText(self.t("asset_delete"))

    def bind(self, project: Project | None, page_id: str | None) -> None:
        self.project = project
        self.page_id = page_id
        self.refresh()

    def _path_at(self, pos) -> Path | None:
        item = self.list.itemAt(pos)
        if item is None or not self.project:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, PageAsset):
            return None
        return resolve_asset_path(self.project, data.relpath)

    def refresh(self) -> None:
        current = self.selected_name()
        self.list.clear()
        self._hover.clear()
        if not self.project or not self.page_id:
            return
        for asset in list_page_assets(self.project, self.page_id, self.kind):
            item = QListWidgetItem(asset.name)
            item.setData(Qt.ItemDataRole.UserRole, asset)
            thumb = load_preview_pixmap(
                resolve_asset_path(self.project, asset.relpath), _ICON
            )
            if thumb is not None:
                item.setIcon(QIcon(thumb))
            self.list.addItem(item)
            if asset.name == current:
                self.list.setCurrentItem(item)
        if self.list.currentItem() is None and self.list.count():
            self.list.setCurrentRow(0)

    def selected_name(self) -> str | None:
        item = self.list.currentItem()
        if not item:
            return None
        return item.text()

    def selected_asset(self) -> PageAsset | None:
        item = self.list.currentItem()
        if not item:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return data if isinstance(data, PageAsset) else None

    def names(self) -> list[str]:
        return [self.list.item(i).text() for i in range(self.list.count())]

    def _on_sel(self, *_args) -> None:
        self.selection_changed.emit()

    def _upload(self) -> None:
        if not self.project or not self.page_id:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, self.t("dlg_image"), "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return
        name, ok = QInputDialog.getText(
            self, self.t("asset_name_title"), self.t("asset_name_label")
        )
        preferred = name.strip() if ok and name.strip() else None
        try:
            asset = upload_page_asset(
                self.project,
                self.page_id,
                self.kind,
                path,
                preferred_name=preferred,
            )
        except Exception as exc:
            QMessageBox.critical(self, self.t("err_title"), str(exc))
            return
        self.refresh()
        for i in range(self.list.count()):
            if self.list.item(i).text() == asset.name:
                self.list.setCurrentRow(i)
                break
        self.changed.emit()

    def _delete(self) -> None:
        if not self.project or not self.page_id:
            return
        name = self.selected_name()
        if not name:
            return
        if (
            QMessageBox.question(
                self,
                self.t("err_title"),
                self.t("confirm_delete", name=name),
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        delete_page_asset(self.project, self.page_id, self.kind, name)
        self.refresh()
        self.changed.emit()


class PageAssetsPanel(QGroupBox):
    """Page-owned detect + click libraries (no storage paths shown)."""

    changed = Signal()

    def __init__(self, t: Callable[..., str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._t = t
        self.setTitle("")
        lay = QVBoxLayout(self)
        self.hdr_images, _, self.help_page_images = section_title_row(
            t, "asset_panel_title", "help_page_images"
        )
        lay.addWidget(self.hdr_images)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: #666;")
        lay.addWidget(self.hint)

        row = QHBoxLayout()
        self.grp_detect = QGroupBox()
        dl = QVBoxLayout(self.grp_detect)
        self.detect_list = AssetKindList(t, "detect")
        self.detect_list.changed.connect(self.changed.emit)
        dl.addWidget(self.detect_list)
        row.addWidget(self.grp_detect)

        self.grp_click = QGroupBox()
        cl = QVBoxLayout(self.grp_click)
        self.click_list = AssetKindList(t, "click")
        self.click_list.changed.connect(self.changed.emit)
        cl.addWidget(self.click_list)
        row.addWidget(self.grp_click)
        lay.addLayout(row)
        self.retranslate()

    def t(self, key: str, **kwargs: object) -> str:
        return self._t(key, **kwargs)

    def retranslate(self) -> None:
        self.setTitle("")
        self.hdr_images.retranslate()  # type: ignore[attr-defined]
        self.help_page_images.retranslate()
        self.hint.setText(self.t("asset_panel_hint"))
        self.grp_detect.setTitle(self.t("asset_detect"))
        self.grp_click.setTitle(self.t("asset_click"))
        self.detect_list.retranslate()
        self.click_list.retranslate()

    def bind(self, project: Project | None, page_id: str | None) -> None:
        self.detect_list.bind(project, page_id)
        self.click_list.bind(project, page_id)

    def refresh(self) -> None:
        self.detect_list.refresh()
        self.click_list.refresh()
