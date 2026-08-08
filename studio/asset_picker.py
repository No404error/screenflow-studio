"""Dropdown of page feature assets with hover image preview."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QWidget

from screenflow.assets import PageAsset, list_page_assets, resolve_asset_path
from screenflow.models import Project
from studio.hover_preview import HoverImagePreview


class AssetNameCombo(QComboBox):
    """Non-editable list of feature asset names for one page."""

    selection_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEditable(False)
        self._project: Project | None = None
        self._page_id: str | None = None
        self._hover = HoverImagePreview(self)
        self._hover.attach_combo(self, self._path_for_data)
        self.currentIndexChanged.connect(lambda _i: self.selection_changed.emit())

    def _path_for_data(self, data: object) -> Path | None:
        if self._project is None:
            return None
        if isinstance(data, PageAsset):
            return resolve_asset_path(self._project, data.relpath)
        if isinstance(data, str) and data and self._page_id:
            from screenflow.assets import page_asset_dir

            folder = page_asset_dir(self._project, self._page_id)
            if folder.is_dir():
                for p in folder.iterdir():
                    if p.is_file() and p.stem == data:
                        return p
        return None

    def bind(
        self,
        project: Project | None,
        page_id: str | None,
        *,
        selected: str | None = None,
        allow_empty: bool = True,
    ) -> None:
        keep = selected if selected is not None else self.current_name()
        self._project = project
        self._page_id = page_id
        self.blockSignals(True)
        self.clear()
        if allow_empty:
            self.addItem("—", None)
        assets: list[PageAsset] = []
        if project and page_id:
            assets = list_page_assets(project, page_id)
        names = {a.name for a in assets}
        for a in assets:
            self.addItem(a.name, a)
        if keep and keep not in names:
            # Preserve invalid/orphan selection so the user can see and fix it
            self.addItem(keep, keep)
        if keep:
            idx = self.findText(keep)
            if idx >= 0:
                self.setCurrentIndex(idx)
            elif allow_empty:
                self.setCurrentIndex(0)
        elif allow_empty:
            self.setCurrentIndex(0)
        elif self.count():
            self.setCurrentIndex(0)
        self.blockSignals(False)

    def current_name(self) -> str | None:
        data = self.currentData()
        if isinstance(data, PageAsset):
            return data.name
        if isinstance(data, str) and data.strip():
            return data.strip()
        text = self.currentText().strip()
        if not text or text == "—":
            return None
        return text

    def first_asset_name(self) -> str | None:
        for i in range(self.count()):
            data = self.itemData(i)
            if isinstance(data, PageAsset):
                return data.name
        return None

    def fill_assets(
        self,
        project: Project | None,
        assets: list[PageAsset],
        *,
        selected: str | None = None,
        allow_empty: bool = True,
    ) -> None:
        """Fill from an explicit asset list (e.g. steps editor click targets)."""
        keep = selected if selected is not None else self.current_name()
        self._project = project
        if assets and project:
            parts = assets[0].relpath.replace("\\", "/").split("/")
            if len(parts) >= 2 and parts[0] == "pages":
                self._page_id = parts[1]
        self.blockSignals(True)
        self.clear()
        if allow_empty:
            self.addItem("—", None)
        names = {a.name for a in assets}
        for a in assets:
            self.addItem(a.name, a)
        if keep and keep not in names:
            self.addItem(keep, keep)
        if keep:
            idx = self.findText(keep)
            self.setCurrentIndex(idx if idx >= 0 else 0)
        elif self.count():
            self.setCurrentIndex(0)
        self.blockSignals(False)
