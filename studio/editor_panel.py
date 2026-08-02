from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from screenflow.assets import (
    PageAsset,
    asset_name_from_relpath,
    ensure_page_asset_dirs,
    list_page_assets,
    resolve_asset_path,
    sync_page_asset_maps,
    upload_page_asset,
)
from screenflow.models import (
    ActionStep,
    DecideParams,
    MacroDef,
    PageDef,
    PostListen,
    Project,
    ScoreSpec,
    StateNode,
    DEFAULT_STATE,
)
from screenflow.project import list_page_pairs, page_to_dict, set_page_pair
from studio.hover_preview import HoverImagePreview
from studio.page_assets import PageAssetsPanel
from studio.section_help import SectionHelpButton, section_title_row, toolbutton_with_help
from studio.state_tree_ui import StateTreeEditor
from studio.steps_editor import StepsEditor

KIND_EMPTY = "empty"


def _steps_snapshot(steps: list[ActionStep]) -> list[tuple]:
    return [(s.op, s.target, s.reason, s.hold) for s in steps]
KIND_PAGES = "pages"
KIND_PAGE_PAIRS = "page_pairs"
KIND_PAGE = "page"
KIND_STATE_TREE = "state_tree"
KIND_STATE_NODE = "state_node"
KIND_MACRO = "macro"
KIND_MACROS = "macros"


class EditorPanel(QWidget):
    project_changed = Signal()
    request_refresh_tree = Signal()
    request_select_ctx = Signal(object)

    def __init__(self, t: Callable[..., str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._t = t
        self.project: Project | None = None
        self._ctx: dict[str, Any] = {"kind": KIND_EMPTY}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel()
        self.title.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(self.title)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, stretch=1)

        self.page_empty = QLabel()
        self.page_empty.setWordWrap(True)
        self.stack.addWidget(self._wrap(self.page_empty))
        self._build_page_editor()
        self._build_state_tree_editor()
        self._build_macro_editor()
        self._build_pairs_editor()
        self._build_macros_overview()
        self.show_empty()

    def t(self, key: str, **kwargs: object) -> str:
        return self._t(key, **kwargs)

    def _wrap(self, inner: QWidget) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        return scroll

    def set_project(self, project: Project | None) -> None:
        # Drop editor context first so flush_all cannot write the old form
        # into a newly loaded project.
        self._ctx = {"kind": KIND_EMPTY}
        self.project = project
        self.show_empty()

    def retranslate(self) -> None:
        t = self.t
        self.page_empty.setText(t("editor_empty"))
        self.lbl_page_name.setText(t("ed_page_name"))
        self.lbl_page_id.setText(t("ed_page_id"))
        self.lbl_page_detect.setText(t("ed_page_detect"))
        self.lbl_page_pri.setText(t("ed_page_priority"))
        self.lbl_page_pair.setText(t("ed_page_pair"))
        self.lbl_page_thr.setText(t("ed_page_threshold"))
        self.lbl_page_near.setText(t("ed_page_near"))
        self.lbl_page_margin.setText(t("ed_page_margin"))
        self.lbl_page_on_close.setText(t("ed_page_on_close"))
        self._rebuild_page_on_close_combo(keep=self.cmb_page_on_close.currentData())
        self.btn_page_default_post.setText(t("ed_page_default_post"))
        self._refresh_page_decide_hint()
        self.lbl_page_hint.setText(t("ed_page_hint_no_detect"))
        self.btn_page_advanced.setText(t("sec_page_match"))
        self.help_page_match.retranslate()
        self.btn_page_detect_upload.setText(t("asset_upload"))
        self.btn_edit_states.setText(t("ed_edit_states"))
        self.page_assets.retranslate()
        self.state_tree.retranslate()
        self.lbl_macro_id.setText(t("ed_macro_id"))
        self.lbl_macro_name.setText(t("ed_macro_name"))
        self.btn_macro_advanced.setText(t("ed_advanced"))
        self.steps_macro.retranslate()
        self.hdr_pairs.retranslate()  # type: ignore[attr-defined]
        self.help_pairs.retranslate()
        self.lbl_pairs_hint.setText(t("pairs_hint"))
        self.btn_pair_add.setText(t("pairs_add"))
        self.btn_pair_del.setText(t("pairs_del"))
        self.lbl_pair_a.setText(t("pairs_page_a"))
        self.lbl_pair_b.setText(t("pairs_page_b"))
        self.hdr_macros.retranslate()  # type: ignore[attr-defined]
        self.help_macros.retranslate()
        self.lbl_macros_hint.setText(t("macros_overview_hint"))
        self._refresh_page_decide_hint()
        self._set_title_for_ctx()
        if self._ctx.get("kind") in (KIND_PAGES, KIND_PAGE_PAIRS):
            self._load_pairs()
        elif self._ctx.get("kind") == KIND_MACROS:
            self._load_macros_overview()

    def show_empty(self) -> None:
        self.flush_all()
        self._ctx = {"kind": KIND_EMPTY}
        self.title.setText(self.t("editor_title_empty"))
        self.stack.setCurrentIndex(0)

    def flush_all(self) -> None:
        """Write any open editor forms into the in-memory project."""
        kind = self._ctx.get("kind")
        if kind == KIND_PAGE:
            self.flush_page(refresh_nav=False)
        elif kind in (KIND_STATE_TREE, KIND_STATE_NODE):
            self.state_tree.flush_current_node(rebuild=False, allow_rebuild=False)
        elif kind == KIND_MACRO:
            self.flush_macro(refresh_nav=False)

    def show_selection(self, ctx: dict[str, Any]) -> None:
        if not self.project:
            self.show_empty()
            return
        self.flush_all()
        self._ctx = ctx
        kind = ctx.get("kind")
        if kind == KIND_PAGE:
            self._load_page(str(ctx["page_id"]))
        elif kind == KIND_STATE_TREE:
            self._load_state_tree(str(ctx["page_id"]))
        elif kind == KIND_STATE_NODE:
            self._load_state_tree(
                str(ctx["page_id"]), select_node_id=str(ctx.get("node_id") or "")
            )
        elif kind == KIND_MACRO:
            self._load_macro(str(ctx["macro_id"]))
        elif kind == KIND_MACROS:
            self._load_macros_overview()
        elif kind in (KIND_PAGES, KIND_PAGE_PAIRS):
            self._load_pairs()
        else:
            self._ctx = {"kind": KIND_EMPTY}
            self.title.setText(self.t("editor_title_empty"))
            self.stack.setCurrentIndex(0)

    def _set_title_for_ctx(self) -> None:
        kind = self._ctx.get("kind")
        t = self.t
        if kind == KIND_PAGE:
            pid = str(self._ctx.get("page_id", ""))
            pname = self.project.pages[pid].display_name() if self.project and pid in self.project.pages else pid
            self.title.setText(t("editor_title_page", name=pname))
        elif kind in (KIND_STATE_TREE, KIND_STATE_NODE):
            pid = str(self._ctx.get("page_id", ""))
            pname = self.project.pages[pid].display_name() if self.project and pid in self.project.pages else pid
            self.title.setText(t("editor_title_states", name=pname))
        elif kind == KIND_MACRO:
            mid = str(self._ctx.get("macro_id", ""))
            mname = mid
            if self.project and mid in self.project.macros:
                mname = self.project.macros[mid].name or mid
            self.title.setText(t("editor_title_macro", name=mname))
        elif kind == KIND_MACROS:
            self.title.setText(t("editor_title_macros"))
        elif kind in (KIND_PAGES, KIND_PAGE_PAIRS):
            self.title.setText(t("editor_title_pairs"))
        else:
            self.title.setText(t("editor_title_empty"))

    def _build_page_editor(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        form = QFormLayout()
        self.ed_page_name = QLineEdit()
        self.ed_page_id = QLineEdit()
        self.ed_page_id.setReadOnly(True)
        self.cmb_page_detect = QComboBox()
        self.cmb_page_detect.setEditable(False)
        self.btn_page_detect_upload = QPushButton()
        self.btn_page_detect_upload.clicked.connect(self._upload_page_detect)
        self._page_detect_hover = HoverImagePreview(self)
        self._page_detect_hover.attach_combo(
            self.cmb_page_detect, self._page_detect_path_for_data
        )
        row_d = QHBoxLayout()
        row_d.addWidget(self.cmb_page_detect, stretch=1)
        row_d.addWidget(self.btn_page_detect_upload)
        self.spin_page_pri = QSpinBox()
        self.spin_page_pri.setRange(-100, 100)
        self.cmb_page_pair = QComboBox()
        self.lbl_page_name = QLabel()
        self.lbl_page_id = QLabel()
        self.lbl_page_detect = QLabel()
        self.lbl_page_pri = QLabel()
        self.lbl_page_pair = QLabel()
        self.lbl_page_hint = QLabel()
        self.lbl_page_hint.setWordWrap(True)
        self.lbl_page_hint.setStyleSheet("color: #a15c00;")
        form.addRow(self.lbl_page_name, self.ed_page_name)
        form.addRow(self.lbl_page_detect, row_d)
        lay.addLayout(form)
        lay.addWidget(self.lbl_page_hint)

        self.btn_page_advanced = QToolButton()
        self.btn_page_advanced.setCheckable(True)
        self.btn_page_advanced.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.btn_page_advanced.setArrowType(Qt.ArrowType.RightArrow)
        self.help_page_match = SectionHelpButton(self.t, "help_page_match")
        self.page_advanced = QWidget()
        self.page_advanced.setVisible(False)
        adv = QFormLayout(self.page_advanced)
        adv.setContentsMargins(0, 0, 0, 0)
        self.spin_page_thr = QDoubleSpinBox()
        self.spin_page_thr.setRange(0.1, 1.0)
        self.spin_page_thr.setSingleStep(0.01)
        self.spin_page_thr.setSpecialValueText("—")
        self.spin_page_thr.setMinimum(0.0)
        self.spin_page_near = QDoubleSpinBox()
        self.spin_page_near.setRange(0.0, 1.0)
        self.spin_page_near.setSingleStep(0.01)
        self.spin_page_margin = QDoubleSpinBox()
        self.spin_page_margin.setRange(0.0, 1.0)
        self.spin_page_margin.setSingleStep(0.01)
        self.cmb_page_on_close = QComboBox()
        self.lbl_page_thr = QLabel()
        self.lbl_page_near = QLabel()
        self.lbl_page_margin = QLabel()
        self.lbl_page_on_close = QLabel()
        self.lbl_page_decide_hint = QLabel()
        self.lbl_page_decide_hint.setWordWrap(True)
        self.lbl_page_decide_hint.setStyleSheet("color: #555;")
        self.btn_page_default_post = QPushButton()
        self.btn_page_default_post.clicked.connect(self._edit_default_post)
        adv.addRow(self.lbl_page_id, self.ed_page_id)
        adv.addRow(self.lbl_page_pri, self.spin_page_pri)
        adv.addRow(self.lbl_page_pair, self.cmb_page_pair)
        adv.addRow(self.lbl_page_thr, self.spin_page_thr)
        adv.addRow(self.lbl_page_near, self.spin_page_near)
        adv.addRow(self.lbl_page_margin, self.spin_page_margin)
        adv.addRow(self.lbl_page_on_close, self.cmb_page_on_close)
        adv.addRow(self.btn_page_default_post)
        # Visible on the main page form (not only inside Advanced)
        lay.addWidget(self.lbl_page_decide_hint)

        def _toggle(on: bool) -> None:
            self.page_advanced.setVisible(on)
            self.btn_page_advanced.setArrowType(
                Qt.ArrowType.DownArrow if on else Qt.ArrowType.RightArrow
            )

        self.btn_page_advanced.toggled.connect(_toggle)
        lay.addWidget(
            toolbutton_with_help(self.btn_page_advanced, self.help_page_match)
        )
        lay.addWidget(self.page_advanced)

        self.page_assets = PageAssetsPanel(self.t)
        self.page_assets.changed.connect(self._on_page_assets_changed)
        lay.addWidget(self.page_assets)

        brow = QHBoxLayout()
        self.btn_edit_states = QPushButton()
        self.btn_edit_states.clicked.connect(self._emit_edit_states)
        brow.addWidget(self.btn_edit_states)
        lay.addLayout(brow)
        lay.addStretch(1)

        self._page_loading = False
        self.ed_page_name.editingFinished.connect(self._on_page_form_changed)
        self.cmb_page_detect.currentIndexChanged.connect(self._on_page_form_changed)
        self.spin_page_pri.valueChanged.connect(self._on_page_form_changed)
        self.cmb_page_pair.currentIndexChanged.connect(self._on_page_form_changed)
        self.spin_page_thr.valueChanged.connect(self._on_page_form_changed)
        self.spin_page_near.valueChanged.connect(self._on_page_form_changed)
        self.spin_page_margin.valueChanged.connect(self._on_page_form_changed)
        self.cmb_page_on_close.currentIndexChanged.connect(self._on_page_form_changed)

        self.stack.addWidget(self._wrap(w))

    def _build_state_tree_editor(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.state_tree = StateTreeEditor(self.t)
        self.state_tree.changed.connect(self.project_changed.emit)
        lay.addWidget(self.state_tree)
        self.stack.addWidget(self._wrap(w))

    def _build_macro_editor(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        form = QFormLayout()
        self.ed_macro_id = QLineEdit()
        self.ed_macro_id.setReadOnly(True)
        self.ed_macro_name = QLineEdit()
        self.lbl_macro_id = QLabel()
        self.lbl_macro_name = QLabel()
        form.addRow(self.lbl_macro_name, self.ed_macro_name)
        lay.addLayout(form)
        self.btn_macro_advanced = QToolButton()
        self.btn_macro_advanced.setCheckable(True)
        self.btn_macro_advanced.setAutoRaise(True)
        self.btn_macro_advanced.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
        )
        self.btn_macro_advanced.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.btn_macro_advanced.setArrowType(Qt.ArrowType.RightArrow)
        self.macro_advanced = QWidget()
        self.macro_advanced.setVisible(False)
        madv = QFormLayout(self.macro_advanced)
        madv.addRow(self.lbl_macro_id, self.ed_macro_id)

        def _toggle(on: bool) -> None:
            self.macro_advanced.setVisible(on)
            self.btn_macro_advanced.setArrowType(
                Qt.ArrowType.DownArrow if on else Qt.ArrowType.RightArrow
            )

        self.btn_macro_advanced.toggled.connect(_toggle)
        macro_adv_row = QWidget()
        macro_adv_lay = QHBoxLayout(macro_adv_row)
        macro_adv_lay.setContentsMargins(0, 0, 0, 0)
        macro_adv_lay.addWidget(
            self.btn_macro_advanced, 0, Qt.AlignmentFlag.AlignLeft
        )
        macro_adv_lay.addStretch(1)
        lay.addWidget(macro_adv_row)
        lay.addWidget(self.macro_advanced)
        self.steps_macro = StepsEditor(self.t, section_help=True)
        self.steps_macro.changed.connect(self._on_macro_steps_changed)
        lay.addWidget(self.steps_macro)
        self._macro_loading = False
        self.ed_macro_name.editingFinished.connect(self._on_macro_form_changed)
        self.stack.addWidget(self._wrap(w))

    def _load_page(self, page_id: str) -> None:
        assert self.project
        page = self.project.pages[page_id]
        ensure_page_asset_dirs(self.project, page_id)
        sync_page_asset_maps(self.project, page)
        self._page_loading = True
        self.ed_page_name.setText(page.display_name())
        self.ed_page_id.setText(page.page_id)
        self.spin_page_pri.setValue(page.detect_priority)
        dp = page.decide_params
        self.spin_page_thr.setValue(dp.threshold if dp.threshold is not None else 0.0)
        self.spin_page_near.setValue(dp.near if dp.near is not None else 0.0)
        self.spin_page_margin.setValue(dp.margin if dp.margin is not None else 0.0)
        self._rebuild_page_on_close_combo(keep=dp.on_close)
        # Auto-open Advanced when this page overrides decide rules
        if any(
            v is not None
            for v in (dp.threshold, dp.near, dp.margin, dp.on_close)
        ):
            self.btn_page_advanced.setChecked(True)
        self._refresh_page_decide_hint()
        self.cmb_page_pair.clear()
        self.cmb_page_pair.addItem("", "")
        for pid, other in self.project.pages.items():
            if pid != page_id:
                self.cmb_page_pair.addItem(other.display_name(), pid)
        idx = self.cmb_page_pair.findData(page.pair_with or "")
        self.cmb_page_pair.setCurrentIndex(max(0, idx))
        self.page_assets.bind(self.project, page_id)
        self._refresh_page_detect_combo(
            selected=asset_name_from_relpath(page.detect_relpath)
        )
        self._update_page_detect_hint()
        self._page_loading = False
        self._set_title_for_ctx()
        self.stack.setCurrentIndex(1)

    def _update_page_detect_hint(self) -> None:
        page_id = self.ed_page_id.text().strip()
        has = bool(
            self.project
            and page_id
            and list_page_assets(self.project, page_id, "detect")
        )
        self.lbl_page_hint.setVisible(not has)

    def _page_detect_path_for_data(self, data: object) -> Path | None:
        if not self.project or not data:
            return None
        return resolve_asset_path(self.project, str(data))

    def _refresh_page_detect_combo(self, selected: str | None = None) -> None:
        page_id = self.ed_page_id.text().strip()
        keep = selected or self.cmb_page_detect.currentData()
        self.cmb_page_detect.blockSignals(True)
        self.cmb_page_detect.clear()
        if not self.project or not page_id:
            self.cmb_page_detect.blockSignals(False)
            return
        for a in list_page_assets(self.project, page_id, "detect"):
            self.cmb_page_detect.addItem(a.name, a.relpath)
        if keep:
            idx = self.cmb_page_detect.findText(str(keep))
            if idx < 0:
                idx = self.cmb_page_detect.findData(str(keep))
            if idx >= 0:
                self.cmb_page_detect.setCurrentIndex(idx)
        self.cmb_page_detect.blockSignals(False)

    def _on_page_assets_changed(self) -> None:
        if not self.project:
            return
        page_id = self.ed_page_id.text().strip()
        page = self.project.pages.get(page_id)
        if page:
            sync_page_asset_maps(self.project, page)
        self._refresh_page_detect_combo()
        self._update_page_detect_hint()
        # Keep case editor asset dropdowns in sync when libraries change
        self.state_tree.set_page_context(self.project, page_id)
        self.project_changed.emit()
        self.request_refresh_tree.emit()

    def _upload_page_detect(self) -> None:
        if not self.project:
            return
        page_id = self.ed_page_id.text().strip()
        path, _ = QFileDialog.getOpenFileName(
            self, self.t("dlg_image"), "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self, self.t("asset_name_title"), self.t("asset_name_label")
        )
        preferred = name.strip() if ok and name.strip() else "main"
        try:
            asset = upload_page_asset(
                self.project, page_id, "detect", path, preferred_name=preferred
            )
        except Exception as exc:
            QMessageBox.critical(self, self.t("err_title"), str(exc))
            return
        page = self.project.pages[page_id]
        sync_page_asset_maps(self.project, page)
        page.detect_relpath = asset.relpath
        self.page_assets.refresh()
        self._refresh_page_detect_combo(selected=asset.name)
        self.project_changed.emit()
        self.request_refresh_tree.emit()

    def _on_page_form_changed(self, *_args) -> None:
        if getattr(self, "_page_loading", False):
            return
        self.flush_page(refresh_nav=True)

    def flush_page(self, *, refresh_nav: bool = True) -> None:
        if not self.project:
            return
        page_id = self.ed_page_id.text().strip()
        page = self.project.pages.get(page_id)
        if not page:
            return
        before = page_to_dict(page)
        before_pairs = {
            pid: p.pair_with for pid, p in self.project.pages.items()
        }
        page.name = self.ed_page_name.text().strip() or page_id
        sync_page_asset_maps(self.project, page)
        rel = self.cmb_page_detect.currentData()
        if rel:
            page.detect_relpath = str(rel)
        page.detect_priority = self.spin_page_pri.value()
        pair = self.cmb_page_pair.currentData()
        set_page_pair(self.project, page_id, str(pair) if pair else None)
        page.decide_params = DecideParams(
            threshold=self.spin_page_thr.value() or None,
            near=self.spin_page_near.value() or None,
            margin=self.spin_page_margin.value() or None,
            on_close=self.cmb_page_on_close.currentData(),
        )
        self._refresh_page_decide_hint()
        after_pairs = {
            pid: p.pair_with for pid, p in self.project.pages.items()
        }
        if page_to_dict(page) != before or after_pairs != before_pairs:
            self.project_changed.emit()
        if refresh_nav:
            self.request_refresh_tree.emit()
            self._set_title_for_ctx()

    def _rebuild_page_on_close_combo(self, *, keep: object = None) -> None:
        t = self.t
        self.cmb_page_on_close.blockSignals(True)
        self.cmb_page_on_close.clear()
        self.cmb_page_on_close.addItem(t("on_close_inherit"), None)
        self.cmb_page_on_close.addItem(t("on_close_priority"), "priority")
        self.cmb_page_on_close.addItem(t("on_close_abstain"), "abstain")
        idx = self.cmb_page_on_close.findData(keep)
        self.cmb_page_on_close.setCurrentIndex(max(0, idx))
        self.cmb_page_on_close.blockSignals(False)

    def _refresh_page_decide_hint(self) -> None:
        if not hasattr(self, "lbl_page_decide_hint"):
            return
        if self._ctx.get("kind") != KIND_PAGE or not self.project:
            self.lbl_page_decide_hint.clear()
            return
        page_id = self.ed_page_id.text().strip()
        page = self.project.pages.get(page_id)
        if not page:
            self.lbl_page_decide_hint.clear()
            return
        oc = page.decide_params.on_close
        if oc == "abstain":
            m = page.decide_params.margin
            if m is not None:
                extra = self.t("page_decide_hint_gap", gap=m)
            else:
                extra = ""
            self.lbl_page_decide_hint.setText(
                self.t("page_decide_hint_abstain", extra=extra)
            )
        elif oc == "priority":
            self.lbl_page_decide_hint.setText(self.t("page_decide_hint_priority"))
        else:
            self.lbl_page_decide_hint.clear()

    def _edit_default_post(self) -> None:
        if not self.project:
            return
        page_id = self.ed_page_id.text().strip()
        page = self.project.pages.get(page_id)
        if not page:
            return
        if page.default_post is None:
            page.default_post = PostListen(tree=[])
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

        dlg = QDialog(self)
        dlg.setWindowTitle(self.t("ed_page_default_post"))
        dlg.resize(480, 560)
        lay = QVBoxLayout(dlg)
        editor = StateTreeEditor(self.t)
        macros = [(mid, m.name or mid) for mid, m in self.project.macros.items()]
        editor.set_catalog(macros, sorted(page.click_map.keys()))
        editor.set_page_context(self.project, page_id)
        editor.bind(page.default_post.tree)
        lay.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dlg.accept)
        lay.addWidget(buttons)
        dlg.exec()
        self.project_changed.emit()

    def _emit_edit_states(self) -> None:
        self.show_selection(
            {"kind": KIND_STATE_TREE, "page_id": self.ed_page_id.text().strip()}
        )

    def _load_state_tree(
        self, page_id: str, *, select_node_id: str | None = None
    ) -> None:
        assert self.project
        page = self.project.pages[page_id]
        sync_page_asset_maps(self.project, page)
        macros = [(mid, m.name or mid) for mid, m in self.project.macros.items()]
        self.state_tree.set_catalog(macros, sorted(page.click_map.keys()))
        self.state_tree.set_page_context(self.project, page_id)
        self.state_tree.bind(page.state_tree, select_id=select_node_id or None)
        self._set_title_for_ctx()
        self.stack.setCurrentIndex(2)

    def _project_click_catalog(self) -> tuple[list[str], list[PageAsset]]:
        """Union of click image names/assets across all pages (for macro steps)."""
        assert self.project
        names: list[str] = []
        assets: list[PageAsset] = []
        seen: set[str] = set()
        for page_id, page in self.project.pages.items():
            sync_page_asset_maps(self.project, page)
            for a in list_page_assets(self.project, page_id, "click"):
                if a.name in seen:
                    continue
                seen.add(a.name)
                names.append(a.name)
                assets.append(a)
            for name in page.click_map:
                if name not in seen:
                    seen.add(name)
                    names.append(name)
        return sorted(names), assets

    def _load_macro(self, macro_id: str) -> None:
        assert self.project
        macro = self.project.macros.get(macro_id)
        if not macro:
            self.show_empty()
            return
        self._macro_loading = True
        self.ed_macro_id.setText(macro.id)
        self.ed_macro_name.setText(macro.name)
        click_keys, click_assets = self._project_click_catalog()
        self.steps_macro.set_catalog(
            macros=[],
            click_keys=click_keys,
            click_assets=click_assets,
            project=self.project,
        )
        self.steps_macro.set_steps(macro.steps)
        self._macro_loading = False
        self._set_title_for_ctx()
        self.stack.setCurrentIndex(3)

    def _build_macros_overview(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.hdr_macros, _, self.help_macros = section_title_row(
            self.t, "editor_title_macros", "help_macros"
        )
        lay.addWidget(self.hdr_macros)
        self.lbl_macros_hint = QLabel()
        self.lbl_macros_hint.setWordWrap(True)
        lay.addWidget(self.lbl_macros_hint)
        self.list_macros = QListWidget()
        self.list_macros.itemActivated.connect(self._open_macro_from_overview)
        self.list_macros.itemDoubleClicked.connect(self._open_macro_from_overview)
        lay.addWidget(self.list_macros, stretch=1)
        self.stack.addWidget(self._wrap(w))

    def _load_macros_overview(self) -> None:
        assert self.project
        self.list_macros.clear()
        if not self.project.macros:
            item = QListWidgetItem(self.t("macros_overview_empty"))
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_macros.addItem(item)
        else:
            for mid, macro in self.project.macros.items():
                label = macro.name or mid
                item = QListWidgetItem(f"{label}  ({mid})")
                item.setData(Qt.ItemDataRole.UserRole, mid)
                self.list_macros.addItem(item)
        self._set_title_for_ctx()
        self.stack.setCurrentIndex(5)

    def _open_macro_from_overview(self, item: QListWidgetItem) -> None:
        mid = item.data(Qt.ItemDataRole.UserRole)
        if not mid:
            return
        self.request_select_ctx.emit({"kind": KIND_MACRO, "macro_id": str(mid)})

    def _on_macro_form_changed(self, *_args) -> None:
        if getattr(self, "_macro_loading", False):
            return
        self.flush_macro(refresh_nav=True)

    def _on_macro_steps_changed(self) -> None:
        if getattr(self, "_macro_loading", False):
            return
        self.flush_macro(refresh_nav=False)

    def flush_macro(self, *, refresh_nav: bool = True) -> None:
        if not self.project:
            return
        mid = self.ed_macro_id.text().strip()
        macro = self.project.macros.get(mid)
        if not macro:
            return
        before = (macro.name, _steps_snapshot(macro.steps))
        macro.name = self.ed_macro_name.text().strip() or mid
        macro.steps = self.steps_macro.get_steps()
        after = (macro.name, _steps_snapshot(macro.steps))
        if after != before:
            self.project_changed.emit()
        if refresh_nav:
            self.request_refresh_tree.emit()
            self._set_title_for_ctx()

    def _build_pairs_editor(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.hdr_pairs, _, self.help_pairs = section_title_row(
            self.t, "editor_title_pairs", "help_pairs"
        )
        lay.addWidget(self.hdr_pairs)
        self.lbl_pairs_hint = QLabel()
        self.lbl_pairs_hint.setWordWrap(True)
        lay.addWidget(self.lbl_pairs_hint)
        self.list_pairs = QListWidget()
        lay.addWidget(self.list_pairs, stretch=1)

        form = QFormLayout()
        self.cmb_pair_a = QComboBox()
        self.cmb_pair_b = QComboBox()
        self.lbl_pair_a = QLabel()
        self.lbl_pair_b = QLabel()
        form.addRow(self.lbl_pair_a, self.cmb_pair_a)
        form.addRow(self.lbl_pair_b, self.cmb_pair_b)
        lay.addLayout(form)

        row = QHBoxLayout()
        self.btn_pair_add = QPushButton()
        self.btn_pair_add.clicked.connect(self._add_pair)
        self.btn_pair_del = QPushButton()
        self.btn_pair_del.clicked.connect(self._del_pair)
        row.addWidget(self.btn_pair_add)
        row.addWidget(self.btn_pair_del)
        lay.addLayout(row)
        lay.addStretch(1)
        self.stack.addWidget(self._wrap(w))

    def _load_pairs(self) -> None:
        assert self.project
        self.list_pairs.clear()
        for a, b in list_page_pairs(self.project):
            na = self.project.pages[a].display_name()
            nb = self.project.pages[b].display_name()
            item = QListWidgetItem(self.t("pairs_row", a=na, b=nb))
            item.setData(Qt.ItemDataRole.UserRole, (a, b))
            self.list_pairs.addItem(item)

        for cmb in (self.cmb_pair_a, self.cmb_pair_b):
            cmb.clear()
            for pid, page in self.project.pages.items():
                cmb.addItem(page.display_name(), pid)

        self._set_title_for_ctx()
        self.stack.setCurrentIndex(4)

    def _add_pair(self) -> None:
        if not self.project:
            return
        a = self.cmb_pair_a.currentData()
        b = self.cmb_pair_b.currentData()
        if not a or not b or a == b:
            QMessageBox.information(
                self, self.t("err_title"), self.t("pairs_err_same")
            )
            return
        set_page_pair(self.project, str(a), str(b))
        self.project_changed.emit()
        self.request_refresh_tree.emit()
        self._load_pairs()

    def _del_pair(self) -> None:
        if not self.project:
            return
        item = self.list_pairs.currentItem()
        if item is None:
            return
        pair = item.data(Qt.ItemDataRole.UserRole)
        if not pair:
            return
        a, _b = pair
        set_page_pair(self.project, str(a), None)
        self.project_changed.emit()
        self.request_refresh_tree.emit()
        self._load_pairs()


def make_page(page_id: str, name: str | None = None) -> PageDef:
    return PageDef(
        page_id=page_id,
        name=(name or page_id).strip() or page_id,
        detect_relpath=f"pages/{page_id}/detect/main.png",
        state_tree=[
            StateNode(
                id=DEFAULT_STATE,
                name=DEFAULT_STATE,
                is_else=True,
                actions=[],
            )
        ],
    )


def make_macro(macro_id: str, name: str | None = None) -> MacroDef:
    return MacroDef(
        id=macro_id,
        name=(name or macro_id).strip() or macro_id,
        steps=[ActionStep(op="wait", target=0.5)],
        scope="project",
    )
