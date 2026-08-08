from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
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
from studio.hover_preview import load_preview_pixmap
from studio.section_help import section_title_row

_ICON = 48
_DETAIL_EDGE = 220


class FeatureAssetList(QWidget):
    """List + upload/delete for page feature images, with a selection detail pane."""

    changed = Signal()
    selection_changed = Signal()

    def __init__(
        self,
        t: Callable[..., str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._t = t
        self.project: Project | None = None
        self.page_id: str | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.setIconSize(QSize(_ICON, _ICON))
        self.list.currentItemChanged.connect(self._on_sel)
        left.addWidget(self.list, stretch=1)

        row = QHBoxLayout()
        self.btn_upload = QPushButton()
        self.btn_upload.clicked.connect(self._upload)
        self.btn_delete = QPushButton()
        self.btn_delete.clicked.connect(self._delete)
        row.addWidget(self.btn_upload)
        row.addWidget(self.btn_delete)
        left.addLayout(row)
        root.addLayout(left, stretch=2)

        detail = QWidget()
        detail.setMinimumWidth(200)
        dl = QVBoxLayout(detail)
        dl.setContentsMargins(8, 0, 0, 0)
        self.lbl_detail_title = QLabel()
        self.lbl_detail_title.setStyleSheet("font-weight: 600;")
        dl.addWidget(self.lbl_detail_title)

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(_DETAIL_EDGE, _DETAIL_EDGE)
        self.preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.preview.setStyleSheet(
            "QLabel { background: #2a2a2a; border: 1px solid #666; }"
        )
        dl.addWidget(self.preview, stretch=1)

        form = QFormLayout()
        form.setContentsMargins(0, 8, 0, 0)
        self.lbl_name_k = QLabel()
        self.lbl_name_v = QLabel()
        self.lbl_name_v.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.lbl_mode_k = QLabel()
        self.lbl_mode_v = QLabel()
        self.lbl_mode_v.setWordWrap(True)
        self.lbl_roi_k = QLabel()
        self.lbl_roi_v = QLabel()
        self.lbl_roi_v.setWordWrap(True)
        self.lbl_main_k = QLabel()
        self.lbl_main_v = QLabel()
        form.addRow(self.lbl_name_k, self.lbl_name_v)
        form.addRow(self.lbl_mode_k, self.lbl_mode_v)
        form.addRow(self.lbl_roi_k, self.lbl_roi_v)
        form.addRow(self.lbl_main_k, self.lbl_main_v)
        dl.addLayout(form)
        self.lbl_detail_hint = QLabel()
        self.lbl_detail_hint.setWordWrap(True)
        self.lbl_detail_hint.setStyleSheet("color: #888;")
        dl.addWidget(self.lbl_detail_hint)
        root.addWidget(detail, stretch=3)

        self.retranslate()
        self._show_empty_detail()

    def t(self, key: str, **kwargs: object) -> str:
        return self._t(key, **kwargs)

    def retranslate(self) -> None:
        self.btn_upload.setText(self.t("asset_upload"))
        self.btn_delete.setText(self.t("asset_delete"))
        self.lbl_detail_title.setText(self.t("asset_detail_title"))
        self.lbl_name_k.setText(self.t("asset_detail_name"))
        self.lbl_mode_k.setText(self.t("asset_detail_mode"))
        self.lbl_roi_k.setText(self.t("asset_detail_roi"))
        self.lbl_main_k.setText(self.t("asset_detail_main"))
        self._update_detail()

    def bind(self, project: Project | None, page_id: str | None) -> None:
        self.project = project
        self.page_id = page_id
        self.refresh()

    def refresh(self) -> None:
        current = self.selected_name()
        self.list.clear()
        if not self.project or not self.page_id:
            self._show_empty_detail()
            return
        for asset in list_page_assets(self.project, self.page_id):
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
        self._update_detail()

    def selected_name(self) -> str | None:
        asset = self.selected_asset()
        return asset.name if asset else None

    def selected_asset(self) -> PageAsset | None:
        item = self.list.currentItem()
        if not item:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return data if isinstance(data, PageAsset) else None

    def _on_sel(self, *_args) -> None:
        self._update_detail()
        self.selection_changed.emit()

    def _main_detect_stem(self) -> str | None:
        if not self.project or not self.page_id:
            return None
        page = self.project.pages.get(self.page_id)
        if page is None:
            return None
        return Path(page.detect_relpath).stem

    def _show_empty_detail(self) -> None:
        self.preview.clear()
        self.preview.setText(self.t("asset_detail_empty"))
        self.lbl_name_v.setText("—")
        self.lbl_mode_v.setText("—")
        self.lbl_roi_v.setText("—")
        self.lbl_main_v.setText("—")
        self.lbl_detail_hint.setText("")

    def _update_detail(self) -> None:
        asset = self.selected_asset()
        if asset is None or not self.project:
            self._show_empty_detail()
            return

        path = resolve_asset_path(self.project, asset.relpath)
        pix = load_preview_pixmap(path, _DETAIL_EDGE)
        if pix is not None:
            self.preview.setPixmap(pix)
            self.preview.setText("")
        else:
            self.preview.clear()
            self.preview.setText(self.t("asset_detail_missing"))

        self.lbl_name_v.setText(asset.name)
        if asset.roi:
            self.lbl_mode_v.setText(self.t("asset_search_roi"))
            y0, y1, x0, x1 = asset.roi
            self.lbl_roi_v.setText(
                self.t(
                    "asset_roi_coords",
                    y0=f"{y0:.3f}",
                    y1=f"{y1:.3f}",
                    x0=f"{x0:.3f}",
                    x1=f"{x1:.3f}",
                )
            )
            self.lbl_detail_hint.setText(self.t("asset_roi_tip"))
        else:
            self.lbl_mode_v.setText(self.t("asset_search_full"))
            self.lbl_roi_v.setText(self.t("asset_roi_none"))
            self.lbl_detail_hint.setText(self.t("asset_full_tip"))

        is_main = self._main_detect_stem() == asset.name
        self.lbl_main_v.setText(
            self.t("asset_yes") if is_main else self.t("asset_no")
        )

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
        from studio.roi_crop_dialog import prompt_upload_with_roi

        cropped = prompt_upload_with_roi(self, self.t, path)
        if cropped is None:
            return
        use_path, roi = cropped
        try:
            asset = upload_page_asset(
                self.project,
                self.page_id,
                use_path,
                preferred_name=preferred,
                roi=roi,
            )
        except Exception as exc:
            QMessageBox.critical(self, self.t("err_title"), str(exc))
            return
        self.refresh()
        for i in range(self.list.count()):
            data = self.list.item(i).data(Qt.ItemDataRole.UserRole)
            if isinstance(data, PageAsset) and data.name == asset.name:
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
        delete_page_asset(self.project, self.page_id, name)
        self.refresh()
        self.changed.emit()


class PageAssetsPanel(QGroupBox):
    """Page-owned feature image library (no storage paths shown)."""

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

        self.feature_list = FeatureAssetList(t)
        self.feature_list.changed.connect(self.changed.emit)
        lay.addWidget(self.feature_list, stretch=1)
        self.retranslate()

    def t(self, key: str, **kwargs: object) -> str:
        return self._t(key, **kwargs)

    def retranslate(self) -> None:
        self.setTitle("")
        self.hdr_images.retranslate()  # type: ignore[attr-defined]
        self.help_page_images.retranslate()
        self.hint.setText(self.t("asset_panel_hint"))
        self.feature_list.retranslate()

    def bind(self, project: Project | None, page_id: str | None) -> None:
        self.feature_list.bind(project, page_id)

    def refresh(self) -> None:
        self.feature_list.refresh()
