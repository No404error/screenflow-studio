"""Expandable state-tree editor: drag to reorder/reparent; order drives priority."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from screenflow.assets import list_page_assets
from screenflow.models import (
    DecideParams,
    PostListen,
    ScoreSpec,
    StateNode,
)
from screenflow.project import page_to_dict
from studio.asset_picker import AssetNameCombo
from studio.section_help import SectionHelpButton, section_title_row, toolbutton_with_help
from studio.steps_editor import StepsEditor

_ROLE_NODE = Qt.ItemDataRole.UserRole


def _unique_id(base: str, existing: set[str]) -> str:
    cand = base
    n = 2
    while cand in existing:
        cand = f"{base}_{n}"
        n += 1
    return cand


def normalize_sibling_order(siblings: list[StateNode]) -> None:
    """ELSE lines sink to bottom; priority = top-high among non-ELSE (…, 30, 20, 10)."""
    else_nodes = [n for n in siblings if n.is_else]
    others = [n for n in siblings if not n.is_else]
    siblings[:] = others + else_nodes
    n = len(others)
    for i, node in enumerate(others):
        node.priority = (n - i) * 10
    for node in else_nodes:
        node.priority = 0


def sort_siblings_by_priority(siblings: list[StateNode]) -> None:
    """After an explicit priority edit: sort by number, then rewrite from order."""
    else_nodes = [n for n in siblings if n.is_else]
    others = [n for n in siblings if not n.is_else]
    others.sort(key=lambda n: (n.priority, n.id), reverse=True)
    siblings[:] = others + else_nodes
    normalize_sibling_order(siblings)


def normalize_tree(roots: list[StateNode]) -> None:
    normalize_sibling_order(roots)
    for node in roots:
        if node.children:
            # Branch nodes must not keep leaf-only fields
            if node.children:
                node.actions = []
                node.post = None
            normalize_tree(node.children)


def order_tree_from_priority(roots: list[StateNode]) -> None:
    """On load: display order follows stored priority, then rewrite clean priorities."""

    def walk(sibs: list[StateNode]) -> None:
        else_nodes = [n for n in sibs if n.is_else]
        others = [n for n in sibs if not n.is_else]
        others.sort(key=lambda n: (n.priority, n.id), reverse=True)
        sibs[:] = others + else_nodes
        for node in sibs:
            if node.children:
                walk(node.children)
        normalize_sibling_order(sibs)

    walk(roots)
    normalize_tree(roots)


class _StateTreeWidget(QTreeWidget):
    """Internal-move tree that reports structure changes after a drop."""

    structure_changed = Signal()
    drop_rejected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderHidden(False)
        self.setColumnCount(2)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setExpandsOnDoubleClick(False)

    def dropEvent(self, event: QDropEvent) -> None:
        src = self.currentItem()
        if src is None:
            event.ignore()
            return
        dest = self.itemAt(event.position().toPoint())
        indicator = self.dropIndicatorPosition()

        # Reject drop onto own descendant
        if dest is not None and self._is_ancestor(src, dest):
            self.drop_rejected.emit("st_err_drop_self")
            event.ignore()
            return

        # Dropping ON an item makes it a parent — reject if that item is ELSE or has actions/post
        if dest is not None and indicator == QAbstractItemView.DropIndicatorPosition.OnItem:
            dest_node: StateNode | None = dest.data(0, _ROLE_NODE)
            if dest_node is not None:
                if dest_node.is_else:
                    self.drop_rejected.emit("st_err_drop_else_parent")
                    event.ignore()
                    return
                if dest_node.actions or dest_node.post:
                    self.drop_rejected.emit("st_err_drop_leaf")
                    event.ignore()
                    return

        super().dropEvent(event)
        self.structure_changed.emit()

    @staticmethod
    def _is_ancestor(ancestor: QTreeWidgetItem, node: QTreeWidgetItem) -> bool:
        p = node.parent()
        while p is not None:
            if p is ancestor:
                return True
            p = p.parent()
        return False


class StateTreeEditor(QWidget):
    """Edit a list[StateNode] roots (page tree or post tree)."""

    changed = Signal()

    def __init__(self, t: Callable[..., str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._t = t
        self.roots: list[StateNode] = []
        self._selected_id: str | None = None
        self._loading = False
        self._project_for_tpl = None
        self._page_id: str | None = None
        self._catalog_macros: list = []
        self._catalog_clicks: list[str] = []
        self._form_ready = False

        root_lay = QVBoxLayout(self)
        self.lbl_hint = QLabel()
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setObjectName("stHint")
        root_lay.addWidget(self.lbl_hint)

        split = QSplitter(Qt.Orientation.Horizontal)
        root_lay.addWidget(split, stretch=1)

        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        self.tree = _StateTreeWidget()
        self.tree.structure_changed.connect(self._on_structure_changed)
        self.tree.drop_rejected.connect(self._on_drop_rejected)
        self.tree.currentItemChanged.connect(self._on_select_item)
        left_l.addWidget(self.tree, stretch=1)

        row = QHBoxLayout()
        self.btn_add = QPushButton()
        self.btn_add.clicked.connect(self._add_sibling)
        self.btn_add_child = QPushButton()
        self.btn_add_child.clicked.connect(self._add_child)
        self.btn_del = QPushButton()
        self.btn_del.clicked.connect(self._delete)
        self.btn_move_up = QPushButton()
        self.btn_move_up.clicked.connect(lambda: self._move(-1))
        self.btn_move_down = QPushButton()
        self.btn_move_down.clicked.connect(lambda: self._move(1))
        for b in (
            self.btn_add,
            self.btn_add_child,
            self.btn_del,
            self.btn_move_up,
            self.btn_move_down,
        ):
            row.addWidget(b)
        left_l.addLayout(row)
        split.addWidget(left)

        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)

        self.hdr_basic, _, self.help_case_basic = section_title_row(
            self.t, "st_grp_basic", "help_case_basic"
        )
        right_l.addWidget(self.hdr_basic)
        self.grp_basic = QGroupBox()
        self.grp_basic.setTitle("")
        form = QFormLayout(self.grp_basic)
        self.ed_name = QLineEdit()
        self.chk_else = QCheckBox()
        self.cmb_score_kind = QComboBox()
        self.cmb_source = QComboBox()
        self.cmb_key = AssetNameCombo()
        self.cmb_source.currentIndexChanged.connect(self._on_source_changed)
        self.ed_roi = QLineEdit()
        self.ed_roi.setPlaceholderText("0.75,1,0.75,1")
        self.spin_const = QDoubleSpinBox()
        self.spin_const.setRange(0, 1)
        self.spin_const.setSingleStep(0.01)
        self.lbl_name = QLabel()
        self.lbl_else = QLabel()
        self.lbl_score_kind = QLabel()
        self.lbl_source = QLabel()
        self.lbl_key = QLabel()
        self.lbl_roi = QLabel()
        self.lbl_const = QLabel()
        form.addRow(self.lbl_name, self.ed_name)
        form.addRow(self.lbl_else, self.chk_else)
        form.addRow(self.lbl_score_kind, self.cmb_score_kind)
        form.addRow(self.lbl_source, self.cmb_source)
        form.addRow(self.lbl_key, self.cmb_key)
        form.addRow(self.lbl_roi, self.ed_roi)
        form.addRow(self.lbl_const, self.spin_const)
        right_l.addWidget(self.grp_basic)

        self.btn_advanced = QToolButton()
        self.btn_advanced.setCheckable(True)
        self.btn_advanced.setChecked(False)
        self.btn_advanced.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.btn_advanced.setArrowType(Qt.ArrowType.RightArrow)
        self.help_case_advanced = SectionHelpButton(self.t, "help_case_advanced")
        self.grp_advanced = QWidget()
        self.grp_advanced.setVisible(False)
        adv = QFormLayout(self.grp_advanced)
        adv.setContentsMargins(0, 0, 0, 0)
        self.ed_id = QLineEdit()
        self.spin_pri = QDoubleSpinBox()
        self.spin_pri.setDecimals(0)
        self.spin_pri.setRange(-1000, 1000)
        self.ed_when_var = QLineEdit()
        self.chk_layer_params = QCheckBox()
        self.spin_layer_thr = QDoubleSpinBox()
        self.spin_layer_thr.setRange(0.1, 1.0)
        self.spin_layer_thr.setSingleStep(0.01)
        self.spin_layer_near = QDoubleSpinBox()
        self.spin_layer_near.setRange(0.0, 1.0)
        self.spin_layer_near.setSingleStep(0.01)
        self.spin_layer_margin = QDoubleSpinBox()
        self.spin_layer_margin.setRange(0.0, 1.0)
        self.spin_layer_margin.setSingleStep(0.01)
        self.lbl_id = QLabel()
        self.lbl_pri = QLabel()
        self.lbl_pri_hint = QLabel()
        self.lbl_pri_hint.setWordWrap(True)
        self.lbl_when_var = QLabel()
        self.lbl_layer_thr = QLabel()
        self.lbl_layer_near = QLabel()
        self.lbl_layer_margin = QLabel()
        adv.addRow(self.lbl_id, self.ed_id)
        adv.addRow(self.lbl_pri, self.spin_pri)
        adv.addRow(self.lbl_pri_hint)
        adv.addRow(self.lbl_when_var, self.ed_when_var)
        adv.addRow(self.chk_layer_params)
        adv.addRow(self.lbl_layer_thr, self.spin_layer_thr)
        adv.addRow(self.lbl_layer_near, self.spin_layer_near)
        adv.addRow(self.lbl_layer_margin, self.spin_layer_margin)
        self.chk_layer_params.toggled.connect(self._on_layer_params_toggled)

        def _toggle_adv(on: bool) -> None:
            self.grp_advanced.setVisible(on)
            self.btn_advanced.setArrowType(
                Qt.ArrowType.DownArrow if on else Qt.ArrowType.RightArrow
            )

        self.btn_advanced.toggled.connect(_toggle_adv)
        right_l.addWidget(
            toolbutton_with_help(self.btn_advanced, self.help_case_advanced)
        )
        right_l.addWidget(self.grp_advanced)

        self.grp_actions = QGroupBox()
        self.grp_actions.setTitle("")
        al = QVBoxLayout(self.grp_actions)
        self.steps = StepsEditor(self.t, section_help=True)
        self.steps.changed.connect(self._on_steps_changed)
        al.addWidget(self.steps)
        right_l.addWidget(self.grp_actions)

        self.hdr_post, _, self.help_case_post = section_title_row(
            self.t, "st_post", "help_case_post"
        )
        right_l.addWidget(self.hdr_post)
        self.grp_post = QGroupBox()
        self.grp_post.setTitle("")
        pl = QVBoxLayout(self.grp_post)
        self.chk_post = QCheckBox()
        self.cmb_post_mode = QComboBox()
        self.spin_frames = QDoubleSpinBox()
        self.spin_frames.setDecimals(0)
        self.spin_frames.setRange(1, 9999)
        self.spin_frames.setValue(3)
        self.spin_settle = QDoubleSpinBox()
        self.spin_settle.setDecimals(2)
        self.spin_settle.setRange(0.0, 30.0)
        self.spin_settle.setSingleStep(0.1)
        self.spin_settle.setValue(0.0)
        self.chk_end_unknown = QCheckBox()
        pf = QFormLayout()
        self.lbl_post_enable = QLabel()
        self.lbl_post_mode = QLabel()
        self.lbl_post_frames = QLabel()
        self.lbl_post_settle = QLabel()
        self.lbl_post_end_unknown = QLabel()
        pf.addRow(self.lbl_post_enable, self.chk_post)
        pf.addRow(self.lbl_post_mode, self.cmb_post_mode)
        pf.addRow(self.lbl_post_frames, self.spin_frames)
        pf.addRow(self.lbl_post_settle, self.spin_settle)
        pf.addRow(self.lbl_post_end_unknown, self.chk_end_unknown)
        pl.addLayout(pf)
        self.btn_edit_post_tree = QPushButton()
        self.btn_edit_post_tree.clicked.connect(self._edit_post_tree)
        pl.addWidget(self.btn_edit_post_tree)
        right_l.addWidget(self.grp_post)

        trow = QHBoxLayout()
        self.btn_save_tpl = QPushButton()
        self.btn_save_tpl.clicked.connect(self._save_template)
        self.btn_load_tpl = QPushButton()
        self.btn_load_tpl.clicked.connect(self._load_template)
        trow.addWidget(self.btn_save_tpl)
        trow.addWidget(self.btn_load_tpl)
        right_l.addLayout(trow)
        right_l.addStretch(1)
        split.addWidget(right)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 4)

        self.chk_else.toggled.connect(self._on_else_toggled_ui)
        self.chk_else.toggled.connect(self._on_form_changed_rebuild)
        self.cmb_score_kind.currentIndexChanged.connect(self._update_score_visibility)
        self.cmb_score_kind.currentIndexChanged.connect(self._on_form_changed)
        self.cmb_post_mode.currentIndexChanged.connect(self._update_post_visibility)
        self.cmb_post_mode.currentIndexChanged.connect(self._on_form_changed)
        self.ed_name.editingFinished.connect(self._on_form_changed)
        self.ed_id.editingFinished.connect(self._on_form_changed)
        self.spin_pri.valueChanged.connect(self._on_form_changed)
        self.ed_when_var.editingFinished.connect(self._on_form_changed)
        self.chk_layer_params.toggled.connect(self._on_form_changed)
        self.spin_layer_thr.valueChanged.connect(self._on_form_changed)
        self.spin_layer_near.valueChanged.connect(self._on_form_changed)
        self.spin_layer_margin.valueChanged.connect(self._on_form_changed)
        self.cmb_source.currentIndexChanged.connect(self._on_form_changed)
        self.cmb_key.selection_changed.connect(self._on_form_changed)
        self.ed_roi.editingFinished.connect(self._on_form_changed)
        self.spin_const.valueChanged.connect(self._on_form_changed)
        self.chk_post.toggled.connect(self._on_form_changed_rebuild)
        self.spin_frames.valueChanged.connect(self._on_form_changed)
        self.spin_settle.valueChanged.connect(self._on_form_changed)
        self.chk_end_unknown.toggled.connect(self._on_form_changed)

        self.retranslate()

    def t(self, key: str, **kwargs: object) -> str:
        return self._t(key, **kwargs)

    def retranslate(self) -> None:
        t = self.t
        self.lbl_hint.setText(t("st_hint_order"))
        self.tree.setHeaderLabels([t("st_col_state"), t("st_col_detail")])
        self.btn_add.setText(t("st_add_sibling"))
        self.btn_add_child.setText(t("st_add_child"))
        self.btn_del.setText(t("st_delete"))
        self.btn_move_up.setText(t("st_move_up"))
        self.btn_move_down.setText(t("st_move_down"))
        self.grp_basic.setTitle("")
        self.hdr_basic.retranslate()  # type: ignore[attr-defined]
        self.help_case_basic.retranslate()
        self.btn_advanced.setText(t("st_grp_advanced"))
        self.help_case_advanced.retranslate()
        self.lbl_name.setText(t("st_name"))
        self.lbl_id.setText(t("st_id"))
        self.lbl_pri.setText(t("st_priority"))
        self.lbl_pri_hint.setText(t("st_priority_hint"))
        self.lbl_when_var.setText(t("st_when_var"))
        self.ed_when_var.setPlaceholderText(t("st_when_var_ph"))
        self.chk_layer_params.setText(t("st_layer_params"))
        self.lbl_layer_thr.setText(t("st_layer_threshold"))
        self.lbl_layer_near.setText(t("st_layer_near"))
        self.lbl_layer_margin.setText(t("st_layer_margin"))
        self.lbl_else.setText(t("st_else"))
        self.chk_else.setText(t("st_else_hint"))
        self.lbl_score_kind.setText(t("st_score_kind"))
        self.lbl_source.setText(t("st_score_source"))
        self.lbl_key.setText(t("st_score_key"))
        self.lbl_roi.setText(t("st_roi"))
        self.lbl_const.setText(t("st_constant"))
        self._fill_score_combos()
        self._fill_post_modes()
        self.grp_actions.setTitle("")
        self.grp_post.setTitle("")
        self.hdr_post.retranslate()  # type: ignore[attr-defined]
        self.help_case_post.retranslate()
        self.lbl_post_enable.setText(t("st_post_enable"))
        self.chk_post.setText(t("st_post_enable_hint"))
        self.lbl_post_mode.setText(t("st_post_mode"))
        self.lbl_post_frames.setText(t("st_post_frames"))
        self.lbl_post_settle.setText(t("st_post_settle"))
        self.lbl_post_end_unknown.setText(t("st_post_end_unknown"))
        self.chk_end_unknown.setText(t("st_post_end_unknown_hint"))
        self.btn_edit_post_tree.setText(t("st_edit_post_tree"))
        self.btn_save_tpl.setText(t("st_save_template"))
        self.btn_load_tpl.setText(t("st_load_template"))
        self.steps.retranslate()
        self._rebuild_tree()

    def _fill_score_combos(self) -> None:
        kind = self.cmb_score_kind.currentData()
        src = self.cmb_source.currentData()
        self.cmb_score_kind.blockSignals(True)
        self.cmb_source.blockSignals(True)
        self.cmb_score_kind.clear()
        self.cmb_score_kind.addItem(self.t("st_kind_template"), "template")
        self.cmb_score_kind.addItem(self.t("st_kind_constant"), "constant")
        self.cmb_score_kind.addItem(self.t("st_kind_invert"), "invert")
        self.cmb_source.clear()
        self.cmb_source.addItem(self.t("st_src_detect"), "detect")
        self.cmb_source.addItem(self.t("st_src_click"), "click")
        if kind is not None:
            i = self.cmb_score_kind.findData(kind)
            self.cmb_score_kind.setCurrentIndex(max(0, i))
        if src is not None:
            i = self.cmb_source.findData(src)
            self.cmb_source.setCurrentIndex(max(0, i))
        self.cmb_score_kind.blockSignals(False)
        self.cmb_source.blockSignals(False)

    def _fill_post_modes(self) -> None:
        mode = self.cmb_post_mode.currentData()
        self.cmb_post_mode.blockSignals(True)
        self.cmb_post_mode.clear()
        self.cmb_post_mode.addItem(self.t("st_mode_once"), "once")
        self.cmb_post_mode.addItem(self.t("st_mode_until_page"), "until_page")
        self.cmb_post_mode.addItem(self.t("st_mode_until_case"), "until_case")
        self.cmb_post_mode.addItem(self.t("st_mode_frames"), "frames")
        if mode is not None:
            from screenflow.models import normalize_post_mode

            i = self.cmb_post_mode.findData(normalize_post_mode(str(mode)))
            self.cmb_post_mode.setCurrentIndex(max(0, i))
        self.cmb_post_mode.blockSignals(False)

    def set_catalog(self, macros, click_keys) -> None:
        self._catalog_macros = list(macros or [])
        self._catalog_clicks = list(click_keys or [])
        self._push_steps_catalog()

    def set_project(self, project) -> None:
        self._project_for_tpl = project

    def set_page_context(self, project, page_id: str | None) -> None:
        self._project_for_tpl = project
        self._page_id = page_id
        self.refresh_asset_catalogs()

    def _page_snapshot(self) -> object:
        """Comparable snapshot of the page being edited (for dirty detection)."""
        if not self._project_for_tpl or not self._page_id:
            return None
        page = self._project_for_tpl.pages.get(self._page_id)
        if page is None:
            return None
        return page_to_dict(page)

    def refresh_asset_catalogs(self) -> None:
        """Reload detect/click dropdowns after uploads or library switches."""
        self._push_steps_catalog()
        kind = str(self.cmb_source.currentData() or "detect")
        self.cmb_key.bind(
            self._project_for_tpl,
            self._page_id,
            kind,
            selected=self.cmb_key.current_name(),
        )

    def _push_steps_catalog(self) -> None:
        click_assets = []
        if self._project_for_tpl and self._page_id:
            click_assets = list_page_assets(
                self._project_for_tpl, self._page_id, "click"
            )
        self.steps.set_catalog(
            macros=self._catalog_macros,
            click_keys=self._catalog_clicks,
            click_assets=click_assets,
            project=self._project_for_tpl,
        )

    def _on_source_changed(self, _index: int = 0) -> None:
        if self._loading:
            return
        kind = str(self.cmb_source.currentData() or "detect")
        self.cmb_key.set_kind(kind)

    def bind(self, roots: list[StateNode], *, select_id: str | None = None) -> None:
        self.roots = roots
        order_tree_from_priority(self.roots)
        self._form_ready = False
        self._selected_id = None
        self._rebuild_tree()
        if select_id:
            self._select_by_id(select_id)

    def select_node(self, node_id: str) -> None:
        """Focus a node in the editor tree (used by project nav)."""
        if self._form_ready:
            self.flush_current_node(rebuild=False, allow_rebuild=False)
        self._select_by_id(node_id)
        cur = self.tree.currentItem()
        if cur is not None:
            self.tree.scrollToItem(cur)

    def _ids(self) -> set[str]:
        from screenflow.project import iter_tree

        return {n.id for n in iter_tree(self.roots)}

    def _item_label(self, node: StateNode) -> tuple[str, str]:
        name = node.display_name()
        if node.is_else:
            return f"{name}{self.t('st_else_tag')}", self.t("st_detail_else")
        if node.children:
            return name, self.t("st_detail_branch", n=len(node.children))
        n_act = len(node.actions)
        extra = self.t("st_detail_post") if node.post else ""
        if extra:
            return name, self.t("st_detail_leaf", n=n_act) + " · " + extra
        return name, self.t("st_detail_leaf", n=n_act)

    def _rebuild_tree(self) -> None:
        self._loading = True
        self.tree.blockSignals(True)
        expanded_ids: set[str] = set()

        def collect_expanded(item: QTreeWidgetItem | None = None) -> None:
            if item is None:
                for i in range(self.tree.topLevelItemCount()):
                    collect_expanded(self.tree.topLevelItem(i))
                return
            node = item.data(0, _ROLE_NODE)
            if node and item.isExpanded():
                expanded_ids.add(node.id)
            for i in range(item.childCount()):
                collect_expanded(item.child(i))

        collect_expanded()
        self.tree.clear()

        def add_nodes(parent_item: QTreeWidgetItem | None, nodes: list[StateNode]) -> None:
            for node in nodes:
                title, detail = self._item_label(node)
                item = QTreeWidgetItem([title, detail])
                item.setData(0, _ROLE_NODE, node)
                item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsDragEnabled
                    | Qt.ItemFlag.ItemIsDropEnabled
                )
                if parent_item is None:
                    self.tree.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)
                if node.children:
                    add_nodes(item, node.children)
                    item.setExpanded(node.id in expanded_ids or True)

        add_nodes(None, self.roots)
        self.tree.expandAll()
        self.tree.blockSignals(False)
        self._loading = False
        if self._selected_id:
            self._select_by_id(self._selected_id)
        elif self.tree.topLevelItemCount():
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
        else:
            self._clear_form()

    def _select_by_id(self, node_id: str) -> None:
        def walk(item: QTreeWidgetItem) -> bool:
            node = item.data(0, _ROLE_NODE)
            if isinstance(node, StateNode) and node.id == node_id:
                # Expand ancestors so the item is visible
                p = item.parent()
                while p is not None:
                    p.setExpanded(True)
                    p = p.parent()
                self.tree.setCurrentItem(item)
                self.tree.scrollToItem(item)
                return True
            for i in range(item.childCount()):
                if walk(item.child(i)):
                    return True
            return False

        for i in range(self.tree.topLevelItemCount()):
            if walk(self.tree.topLevelItem(i)):
                return

    def _current_node(self) -> StateNode | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        node = item.data(0, _ROLE_NODE)
        return node if isinstance(node, StateNode) else None

    def _sibling_list_of(self, node: StateNode) -> list[StateNode] | None:
        def find(parent_list: list[StateNode]) -> list[StateNode] | None:
            for n in parent_list:
                if n is node:
                    return parent_list
                found = find(n.children)
                if found is not None:
                    return found
            return None

        return find(self.roots)

    def _on_select_item(
        self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        if self._loading or current is None:
            return
        # Persist edits on the previously selected case before switching
        if self._form_ready and self._selected_id is not None:
            self.flush_current_node(rebuild=False, allow_rebuild=False)
        node = current.data(0, _ROLE_NODE)
        if not isinstance(node, StateNode):
            self._form_ready = False
            self._clear_form()
            return
        self._load_node_into_form(node)

    def _load_node_into_form(self, node: StateNode) -> None:
        self._loading = True
        self._selected_id = node.id
        self.ed_name.setText(node.display_name())
        self.ed_id.setText(node.id)
        self.spin_pri.setValue(node.priority)
        self.ed_when_var.setText(node.when_var or "")
        lp = node.layer_params
        has_lp = any(
            v is not None for v in (lp.threshold, lp.near, lp.margin)
        )
        self.chk_layer_params.setChecked(has_lp)
        self.spin_layer_thr.setValue(lp.threshold if lp.threshold is not None else 0.72)
        self.spin_layer_near.setValue(lp.near if lp.near is not None else 0.03)
        self.spin_layer_margin.setValue(lp.margin if lp.margin is not None else 0.03)
        self._on_layer_params_toggled(has_lp)
        self.chk_else.setChecked(node.is_else)
        spec = node.score or ScoreSpec()
        ki = self.cmb_score_kind.findData(spec.kind)
        self.cmb_score_kind.setCurrentIndex(max(0, ki))
        si = self.cmb_source.findData(spec.source)
        self.cmb_source.setCurrentIndex(max(0, si))
        self.cmb_key.bind(
            self._project_for_tpl,
            self._page_id,
            str(spec.source or "detect"),
            selected=spec.key,
        )
        self.ed_roi.setText(",".join(str(x) for x in spec.roi) if spec.roi else "")
        self.spin_const.setValue(spec.constant)
        self.steps.set_steps(node.actions)
        self.chk_post.setChecked(node.post is not None)
        if node.post:
            from screenflow.models import normalize_post_mode

            mi = self.cmb_post_mode.findData(normalize_post_mode(node.post.mode))
            self.cmb_post_mode.setCurrentIndex(max(0, mi))
            if node.post.frames:
                self.spin_frames.setValue(node.post.frames)
            self.spin_settle.setValue(float(node.post.settle or 0.0))
            self.chk_end_unknown.setChecked(bool(node.post.end_on_unknown))
        else:
            self.spin_settle.setValue(0.0)
            self.chk_end_unknown.setChecked(False)
        leaf = node.is_leaf()
        # ELSE leaves still run actions / post-listen in the engine.
        self.grp_actions.setEnabled(leaf)
        self.grp_post.setEnabled(leaf)
        self._on_else_toggled_ui(node.is_else)
        self._update_score_visibility()
        self._update_post_visibility()
        self._loading = False
        self._form_ready = True

    def _clear_form(self) -> None:
        self._form_ready = False
        self.ed_name.clear()
        self.ed_id.clear()
        self.ed_when_var.clear()
        self.steps.set_steps([])
        self.grp_actions.setEnabled(False)
        self.grp_post.setEnabled(False)

    def _on_layer_params_toggled(self, on: bool) -> None:
        for w in (self.spin_layer_thr, self.spin_layer_near, self.spin_layer_margin):
            w.setEnabled(on)

    def _on_else_toggled_ui(self, checked: bool) -> None:
        for w in (
            self.cmb_score_kind,
            self.cmb_source,
            self.cmb_key,
            self.ed_roi,
            self.spin_const,
        ):
            w.setEnabled(not checked)

    def _update_score_visibility(self) -> None:
        kind = self.cmb_score_kind.currentData() or "template"
        is_const = kind == "constant"
        self.cmb_key.setEnabled(not is_const and not self.chk_else.isChecked())
        self.cmb_source.setEnabled(not is_const and not self.chk_else.isChecked())
        self.ed_roi.setEnabled(not is_const and not self.chk_else.isChecked())
        self.spin_const.setEnabled(is_const and not self.chk_else.isChecked())

    def _update_post_visibility(self) -> None:
        mode = self.cmb_post_mode.currentData() or "once"
        self.spin_frames.setEnabled(mode == "frames")

    def _on_drop_rejected(self, key: str) -> None:
        QMessageBox.information(self, self.t("err_title"), self.t(key))

    def _on_structure_changed(self) -> None:
        if self._loading:
            return
        self._sync_roots_from_widget()
        normalize_tree(self.roots)
        # Deduplicate ELSE: keep first ELSE at each level, unset extras
        self._fix_else_unique(self.roots)
        normalize_tree(self.roots)
        sel = self._selected_id
        self._rebuild_tree()
        if sel:
            self._select_by_id(sel)
        self.changed.emit()

    def _fix_else_unique(self, siblings: list[StateNode]) -> None:
        seen = False
        for n in siblings:
            if n.is_else:
                if seen:
                    n.is_else = False
                    if n.score is None:
                        n.score = ScoreSpec(key=n.id, source="detect")
                else:
                    seen = True
            if n.children:
                self._fix_else_unique(n.children)

    def _sync_roots_from_widget(self) -> None:
        def read(parent: QTreeWidgetItem | None) -> list[StateNode]:
            count = (
                parent.childCount() if parent is not None else self.tree.topLevelItemCount()
            )
            out: list[StateNode] = []
            for i in range(count):
                item = parent.child(i) if parent is not None else self.tree.topLevelItem(i)
                node = item.data(0, _ROLE_NODE)
                if not isinstance(node, StateNode):
                    continue
                node.children = read(item)
                out.append(node)
            return out

        self.roots[:] = read(None)

    def _default_detect_key(self) -> str | None:
        if self._project_for_tpl and self._page_id:
            assets = list_page_assets(self._project_for_tpl, self._page_id, "detect")
            if assets:
                return assets[0].name
        return self.cmb_key.first_asset_name()

    def _new_node(self, base: str) -> StateNode:
        nid = _unique_id(base, self._ids())
        key = self._default_detect_key()
        return StateNode(
            id=nid,
            name=nid,
            score=ScoreSpec(key=key, source="detect"),
        )

    def _add_sibling(self) -> None:
        node = self._current_node()
        new = self._new_node("state")
        if node is None:
            self.roots.append(new)
        else:
            sibs = self._sibling_list_of(node)
            if sibs is None:
                self.roots.append(new)
            else:
                # Insert before trailing ELSE if present
                insert_at = len(sibs)
                for i, s in enumerate(sibs):
                    if s.is_else:
                        insert_at = i
                        break
                sibs.insert(insert_at, new)
        normalize_tree(self.roots)
        self._selected_id = new.id
        self._rebuild_tree()
        self.changed.emit()

    def _add_child(self) -> None:
        parent = self._current_node()
        if parent is None:
            return
        if parent.is_else:
            QMessageBox.warning(self, self.t("err_title"), self.t("st_err_else_child"))
            return
        if parent.actions or parent.post:
            QMessageBox.warning(self, self.t("err_title"), self.t("st_err_branch"))
            return
        new = self._new_node("child")
        parent.children.append(new)
        normalize_tree(self.roots)
        self._selected_id = new.id
        self._rebuild_tree()
        self.changed.emit()

    def _delete(self) -> None:
        node = self._current_node()
        if node is None:
            return
        sibs = self._sibling_list_of(node)
        if sibs is None:
            return
        sibs.remove(node)
        normalize_tree(self.roots)
        self._selected_id = None
        self._rebuild_tree()
        self.changed.emit()

    def _move(self, delta: int) -> None:
        node = self._current_node()
        if node is None:
            return
        sibs = self._sibling_list_of(node)
        if sibs is None:
            return
        i = sibs.index(node)
        j = i + delta
        if j < 0 or j >= len(sibs):
            return
        # Don't move non-ELSE below ELSE or ELSE above others via button —
        # normalize will fix ELSE position anyway
        sibs[i], sibs[j] = sibs[j], sibs[i]
        normalize_tree(self.roots)
        self._selected_id = node.id
        self._rebuild_tree()
        self.changed.emit()

    def _parse_roi(self) -> list[float] | None:
        text = self.ed_roi.text().strip()
        if not text:
            return None
        parts = [float(x.strip()) for x in text.replace(" ", "").split(",")]
        if len(parts) != 4:
            return None
        return parts

    def _node_by_id(self, node_id: str | None) -> StateNode | None:
        if not node_id:
            return None
        from screenflow.project import iter_tree

        for n in iter_tree(self.roots):
            if n.id == node_id:
                return n
        return None

    def _on_steps_changed(self) -> None:
        if self._loading:
            return
        node = self._node_by_id(self._selected_id)
        if node is None or not node.is_leaf():
            return
        node.actions = self.steps.get_steps()
        self._refresh_item_labels(node)
        self.changed.emit()

    def _on_form_changed(self, *_args) -> None:
        if self._loading:
            return
        self.flush_current_node(rebuild=False)

    def _on_form_changed_rebuild(self, *_args) -> None:
        if self._loading:
            return
        self.flush_current_node(rebuild=True)

    def flush_current_node(
        self, *, rebuild: bool = False, allow_rebuild: bool = True
    ) -> None:
        """Write the form into the currently selected case (in-memory)."""
        if not self._form_ready and self._selected_id is None:
            return
        node = self._node_by_id(self._selected_id) or self._current_node()
        if node is None:
            return
        before = self._page_snapshot()
        node.name = self.ed_name.text().strip() or node.id
        new_id = self.ed_id.text().strip() or node.id
        old_pri = node.priority
        node.id = new_id
        node.priority = int(self.spin_pri.value())
        pri_changed = node.priority != old_pri
        wv = self.ed_when_var.text().strip()
        node.when_var = wv or None
        if self.chk_layer_params.isChecked():
            node.layer_params = DecideParams(
                threshold=self.spin_layer_thr.value(),
                near=self.spin_layer_near.value(),
                margin=self.spin_layer_margin.value(),
            )
        else:
            node.layer_params = DecideParams()
        node.is_else = self.chk_else.isChecked()
        if node.is_else:
            # ELSE does not compete on score; keep actions / post-listen.
            node.score = None
        else:
            kind = str(self.cmb_score_kind.currentData() or "template")
            node.score = ScoreSpec(
                kind=kind,
                key=self.cmb_key.current_name(),
                source=str(self.cmb_source.currentData() or "detect"),
                roi=self._parse_roi(),
                constant=self.spin_const.value(),
            )
        if node.is_leaf():
            node.actions = self.steps.get_steps()
            if self.chk_post.isChecked():
                if node.post is None:
                    node.post = PostListen(
                        mode=str(self.cmb_post_mode.currentData() or "once"), tree=[]
                    )
                from screenflow.models import normalize_post_mode

                node.post.mode = normalize_post_mode(
                    str(self.cmb_post_mode.currentData() or "once")
                )
                if node.post.mode == "frames":
                    node.post.frames = int(self.spin_frames.value())
                else:
                    node.post.frames = None
                node.post.settle = float(self.spin_settle.value())
                node.post.end_on_unknown = self.chk_end_unknown.isChecked()
            else:
                node.post = None

        need_rebuild = allow_rebuild and (rebuild or pri_changed)
        sibs = self._sibling_list_of(node)
        if sibs is not None:
            if pri_changed and not node.is_else:
                sort_siblings_by_priority(sibs)
                if allow_rebuild:
                    need_rebuild = True
            else:
                normalize_sibling_order(sibs)
            normalize_tree(self.roots)

        self._selected_id = node.id
        if need_rebuild:
            self._rebuild_tree()
        else:
            self._refresh_item_labels(node)
        # Switching tabs / closing flushes the form; only mark dirty if data changed.
        if self._page_snapshot() != before:
            self.changed.emit()

    def _refresh_item_labels(self, node: StateNode) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        cur = item.data(0, _ROLE_NODE)
        if cur is not node:
            return
        name, detail = self._item_label(node)
        item.setText(0, name)
        item.setText(1, detail)

    def _save_template(self) -> None:
        if not self._project_for_tpl:
            return
        from PySide6.QtWidgets import QInputDialog
        from studio.layer_templates import save_template

        name, ok = QInputDialog.getText(self, self.t("st_save_template"), self.t("st_name"))
        if ok and name.strip():
            save_template(self._project_for_tpl, name.strip(), self.roots)
            QMessageBox.information(
                self, self.t("st_save_template"), self.t("st_template_saved")
            )

    def _load_template(self) -> None:
        if not self._project_for_tpl:
            return
        from PySide6.QtWidgets import QInputDialog
        from studio.layer_templates import list_templates, load_template

        names = list_templates(self._project_for_tpl)
        if not names:
            QMessageBox.information(self, self.t("err_title"), self.t("st_no_templates"))
            return
        name, ok = QInputDialog.getItem(
            self, self.t("st_load_template"), self.t("st_name"), names, 0, False
        )
        if ok and name:
            loaded = load_template(self._project_for_tpl, name)
            self.roots[:] = loaded
            order_tree_from_priority(self.roots)
            self._selected_id = None
            self._rebuild_tree()
            self.changed.emit()

    def _edit_post_tree(self) -> None:
        node = self._current_node()
        if node is None or not node.is_leaf():
            return
        if node.post is None:
            node.post = PostListen(tree=[])
            self.chk_post.setChecked(True)
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

        dlg = QDialog(self)
        dlg.setWindowTitle(self.t("st_edit_post_tree"))
        dlg.resize(720, 560)
        lay = QVBoxLayout(dlg)
        editor = StateTreeEditor(self._t)
        editor.set_catalog(self._catalog_macros, self._catalog_clicks)
        editor.set_page_context(self._project_for_tpl, self._page_id)
        editor.bind(node.post.tree)
        lay.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dlg.accept)
        lay.addWidget(buttons)
        dlg.exec()
        self.changed.emit()
        self._rebuild_tree()
