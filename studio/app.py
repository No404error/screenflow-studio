from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QByteArray, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QAction, QActionGroup, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
    QSpinBox,
)

from screenflow.engine import FlowEngine
from screenflow.models import DEFAULT_STATE, EngineStatus
from screenflow.assets import ensure_page_asset_dirs, upload_page_asset
from screenflow.project import (
    load_project,
    new_blank_project,
    rebuild_resource_index,
    save_project,
    slugify_id,
)
from studio.editor_panel import (
    KIND_MACRO,
    KIND_MACROS,
    KIND_PAGE,
    KIND_PAGE_PAIRS,
    KIND_PAGES,
    KIND_STATE_NODE,
    KIND_STATE_TREE,
    EditorPanel,
    make_macro,
    make_page,
)
from screenflow.project import clear_pairs_involving
from studio.i18n import LANG_EN, LANG_ZH, I18n
from studio.page_wizard import NewPageWizard
from studio.runner_client import RunnerClient
from studio.settings import (
    DEFAULT_SPLITTER_SIZES,
    RUNNER_ELEVATE,
    RUNNER_INLINE,
    clear_recent,
    get_last_dir,
    get_main_splitter_sizes,
    get_recent,
    get_runner_mode,
    get_window_geometry,
    remove_recent,
    resolve_reopen_project_path,
    safe_folder_name,
    set_last_dir,
    set_main_splitter_sizes,
    set_runner_mode,
    set_window_geometry,
    touch_recent,
)
from studio.section_help import SectionHelpButton, section_title_row, toolbutton_with_help
from studio.validate import validate_for_start
from studio.welcome import WelcomePage


class LogBridge(QObject):
    message = Signal(str)


class StatusBridge(QObject):
    status = Signal(object)


class StudioWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.i18n = I18n()

        self.project = None
        self.engine: FlowEngine | None = None
        self.runner: RunnerClient | None = None
        self._project_root: Path | None = None
        self._dirty = False
        self._filling_tree = False
        self._engine_launching = False
        self._log_bridge = LogBridge()
        self._log_bridge.message.connect(self._append_log)
        self._status_bridge = StatusBridge()
        self._status_bridge.status.connect(self._on_engine_status)
        self._status_payload: dict[str, Any] | None = None
        self.main_splitter: QSplitter | None = None
        self._splitter_save_timer = QTimer(self)
        self._splitter_save_timer.setSingleShot(True)
        self._splitter_save_timer.setInterval(400)
        self._splitter_save_timer.timeout.connect(self._persist_splitter_sizes)

        self._build_ui()
        self._restore_window_geometry()
        self._build_menu()
        self._retranslate()
        self._set_controls_enabled(False)
        self._show_welcome(True)
        self._set_status_idle()
        self._try_reopen_last_project()

    def t(self, key: str, **kwargs: object) -> str:
        return self.i18n.t(key, **kwargs)

    def _build_menu(self) -> None:
        self._menu_file = self.menuBar().addMenu("")
        self.act_new = QAction(self)
        self.act_new.triggered.connect(self.new_project)
        self.act_open = QAction(self)
        self.act_open.triggered.connect(self.open_project)
        self.act_save = QAction(self)
        self.act_save.setShortcut("Ctrl+S")
        self.act_save.triggered.connect(self.save_project_ui)
        self.act_quit = QAction(self)
        self.act_quit.triggered.connect(self.close)
        self._menu_file.addAction(self.act_new)
        self._menu_file.addAction(self.act_open)
        self._menu_recent = QMenu(self)
        self._menu_file.addMenu(self._menu_recent)
        self._menu_file.addAction(self.act_save)
        self._menu_file.addSeparator()
        self._menu_file.addAction(self.act_quit)

        self._menu_lang = self.menuBar().addMenu("")
        self._lang_group = QActionGroup(self)
        self._lang_group.setExclusive(True)
        self.act_lang_en = QAction(self)
        self.act_lang_en.setCheckable(True)
        self.act_lang_zh = QAction(self)
        self.act_lang_zh.setCheckable(True)
        self._lang_group.addAction(self.act_lang_en)
        self._lang_group.addAction(self.act_lang_zh)
        self._menu_lang.addAction(self.act_lang_en)
        self._menu_lang.addAction(self.act_lang_zh)
        self.act_lang_en.triggered.connect(lambda: self._switch_lang(LANG_EN))
        self.act_lang_zh.triggered.connect(lambda: self._switch_lang(LANG_ZH))

        self._menu_help = self.menuBar().addMenu("")
        self.act_about = QAction(self)
        self.act_about.triggered.connect(self._about)
        self._menu_help.addAction(self.act_about)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        self.lbl_project = QLabel()
        self.lbl_project.setStyleSheet("font-size: 15px; font-weight: 600;")
        layout.addWidget(self.lbl_project)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.main_splitter, stretch=1)

        left = QWidget()
        left_l = QVBoxLayout(left)
        self.lbl_tree_title = QLabel()
        left_l.addWidget(self.lbl_tree_title)
        self.tree = QTreeWidget()
        self.tree.itemSelectionChanged.connect(self._on_tree_select)
        self.tree.itemExpanded.connect(self._on_nav_item_expanded)
        left_l.addWidget(self.tree, stretch=1)
        tree_btns = QHBoxLayout()
        self.btn_add_page = QPushButton()
        self.btn_add_page.clicked.connect(self.add_page)
        self.btn_add_macro = QPushButton()
        self.btn_add_macro.clicked.connect(self.add_macro)
        self.btn_del_sel = QPushButton()
        self.btn_del_sel.clicked.connect(self.delete_selection)
        for b in (self.btn_add_page, self.btn_add_macro, self.btn_del_sel):
            tree_btns.addWidget(b)
        left_l.addLayout(tree_btns)
        self.main_splitter.addWidget(left)

        self.center_stack = QStackedWidget()
        self.welcome = WelcomePage(self.t)
        self.welcome.new_requested.connect(self.new_project)
        self.welcome.open_requested.connect(self.open_project)
        self.welcome.open_path_requested.connect(self.open_recent_path)
        self.welcome.clear_recent_requested.connect(self.clear_recent_projects)
        self.editor = EditorPanel(self.t)
        self.editor.project_changed.connect(self._mark_dirty)
        self.editor.request_refresh_tree.connect(self._fill_tree)
        self.editor.request_select_ctx.connect(self._select_ctx)
        self.center_stack.addWidget(self.welcome)
        self.center_stack.addWidget(self.editor)
        self.main_splitter.addWidget(self.center_stack)

        right = QWidget()
        right_l = QVBoxLayout(right)

        self.runtime_header, self.lbl_runtime_title, self.help_runtime = section_title_row(
            self.t, "params_group", "help_runtime"
        )
        right_l.addWidget(self.runtime_header)

        self.params_group = QGroupBox()
        self.params_group.setTitle("")
        self.form_params = QFormLayout(self.params_group)
        self.spin_threshold = QDoubleSpinBox()
        self.spin_threshold.setRange(0.1, 1.0)
        self.spin_threshold.setSingleStep(0.01)
        self.spin_poll = QDoubleSpinBox()
        self.spin_poll.setRange(0.05, 5.0)
        self.spin_poll.setSingleStep(0.05)
        self.spin_ref_w = QSpinBox()
        self.spin_ref_w.setRange(640, 7680)
        self.spin_ref_h = QSpinBox()
        self.spin_ref_h.setRange(480, 4320)
        self.chk_verbose = QCheckBox()
        self.spin_state_near = QDoubleSpinBox()
        self.spin_state_near.setRange(0.0, 1.0)
        self.spin_state_near.setSingleStep(0.01)
        self.spin_state_margin = QDoubleSpinBox()
        self.spin_state_margin.setRange(0.0, 1.0)
        self.spin_state_margin.setSingleStep(0.01)
        self.cmb_log_lang = QComboBox()
        self.cmb_log_lang.addItem("English", "en")
        self.cmb_log_lang.addItem("中文", "zh")
        self.chk_redecide = QCheckBox()
        self.cmb_runner_mode = QComboBox()
        self.cmb_runner_mode.currentIndexChanged.connect(self._on_runner_mode_changed)
        self.lbl_threshold = QLabel()
        self.lbl_poll = QLabel()
        self.lbl_ref_w = QLabel()
        self.lbl_ref_h = QLabel()
        self.lbl_verbose = QLabel()
        self.lbl_state_near = QLabel()
        self.lbl_state_margin = QLabel()
        self.lbl_log_lang = QLabel()
        self.lbl_redecide = QLabel()
        self.lbl_runner_mode = QLabel()
        self.form_params.addRow(self.lbl_threshold, self.spin_threshold)
        self.form_params.addRow(self.lbl_poll, self.spin_poll)

        self.btn_params_advanced = QToolButton()
        self.btn_params_advanced.setCheckable(True)
        self.btn_params_advanced.setChecked(False)
        self.btn_params_advanced.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.btn_params_advanced.setArrowType(Qt.ArrowType.RightArrow)
        self.help_runtime_advanced = SectionHelpButton(self.t, "help_runtime_advanced")
        self.params_advanced = QWidget()
        self.params_advanced.setVisible(False)
        adv_params = QFormLayout(self.params_advanced)
        adv_params.setContentsMargins(0, 0, 0, 0)
        adv_params.addRow(self.lbl_ref_w, self.spin_ref_w)
        adv_params.addRow(self.lbl_ref_h, self.spin_ref_h)
        adv_params.addRow(self.lbl_state_near, self.spin_state_near)
        adv_params.addRow(self.lbl_state_margin, self.spin_state_margin)
        adv_params.addRow(self.lbl_log_lang, self.cmb_log_lang)
        adv_params.addRow(self.lbl_redecide, self.chk_redecide)
        adv_params.addRow(self.lbl_verbose, self.chk_verbose)
        adv_params.addRow(self.lbl_runner_mode, self.cmb_runner_mode)

        def _toggle_params_adv(on: bool) -> None:
            self.params_advanced.setVisible(on)
            self.btn_params_advanced.setArrowType(
                Qt.ArrowType.DownArrow if on else Qt.ArrowType.RightArrow
            )

        self.btn_params_advanced.toggled.connect(_toggle_params_adv)
        self.form_params.addRow(
            toolbutton_with_help(self.btn_params_advanced, self.help_runtime_advanced)
        )
        self.form_params.addRow(self.params_advanced)
        right_l.addWidget(self.params_group)

        btn_row = QHBoxLayout()
        self.btn_apply = QPushButton()
        self.btn_apply.clicked.connect(self.apply_params)
        self.btn_start = QPushButton()
        self.btn_start.clicked.connect(self.start_engine)
        self.btn_pause = QPushButton()
        self.btn_pause.clicked.connect(self.pause_engine)
        self.btn_stop = QPushButton()
        self.btn_stop.clicked.connect(self.stop_engine)
        for b in (self.btn_apply, self.btn_start, self.btn_pause, self.btn_stop):
            btn_row.addWidget(b)
        right_l.addLayout(btn_row)

        self.lbl_status = QLabel()
        self.lbl_status.setStyleSheet(
            "padding: 6px 8px; background: #eef2f6; border: 1px solid #d0d7de;"
            " border-radius: 4px; font-weight: 600;"
        )
        right_l.addWidget(self.lbl_status)

        self.lbl_log = QLabel()
        right_l.addWidget(self.lbl_log)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 10))
        right_l.addWidget(self.log_view, stretch=1)

        self.main_splitter.addWidget(right)
        sizes = get_main_splitter_sizes() or list(DEFAULT_SPLITTER_SIZES)
        self.main_splitter.setSizes(sizes)
        self.main_splitter.splitterMoved.connect(self._on_splitter_moved)

        self.lbl_tip = QLabel()
        self.lbl_tip.setWordWrap(True)
        self.lbl_tip.setStyleSheet("color: #666;")
        layout.addWidget(self.lbl_tip)

    def _on_splitter_moved(self, *_args) -> None:
        self._splitter_save_timer.start()

    def _persist_splitter_sizes(self) -> None:
        if self.main_splitter is None:
            return
        sizes = self.main_splitter.sizes()
        if len(sizes) == 3 and sum(sizes) > 0:
            set_main_splitter_sizes(sizes)

    def _restore_window_geometry(self) -> None:
        raw = get_window_geometry()
        if raw:
            ok = self.restoreGeometry(QByteArray.fromBase64(raw.encode("ascii")))
            if ok:
                return
        self.resize(1280, 800)

    def _persist_window_geometry(self) -> None:
        data = bytes(self.saveGeometry().toBase64()).decode("ascii")
        set_window_geometry(data)

    def _persist_session_ui(self) -> None:
        self._splitter_save_timer.stop()
        self._persist_splitter_sizes()
        self._persist_window_geometry()

    def _try_reopen_last_project(self) -> None:
        """Open the most recent valid project; stay on welcome if none."""
        root = resolve_reopen_project_path()
        if root is None:
            return
        try:
            load_project(root)
        except Exception:
            remove_recent(root)
            self._rebuild_recent_menu()
            self.welcome.refresh()
            return
        self._load_path(root)

    def _window_title(self) -> str:
        t = self.t
        base = t("app_title")
        if not self.project:
            return base
        name = self.project.name or t("no_project")
        star = " *" if self._dirty else ""
        return f"{base} — {name}{star}"

    def _refresh_window_title(self) -> None:
        self.setWindowTitle(self._window_title())

    def _retranslate(self) -> None:
        t = self.t
        self._refresh_window_title()
        self._menu_file.setTitle(t("menu_file"))
        self._menu_lang.setTitle(t("menu_language"))
        self._menu_help.setTitle(t("menu_help"))
        self.act_new.setText(t("act_new"))
        self.act_open.setText(t("act_open"))
        self.act_save.setText(t("act_save"))
        self.act_quit.setText(t("act_exit"))
        self.act_about.setText(t("act_about"))
        self._menu_recent.setTitle(t("menu_recent"))
        self.act_lang_en.setText(t("lang_en"))
        self.act_lang_zh.setText(t("lang_zh"))
        self.act_lang_en.setChecked(self.i18n.lang == LANG_EN)
        self.act_lang_zh.setChecked(self.i18n.lang == LANG_ZH)
        self._rebuild_recent_menu()
        self.welcome.retranslate()

        if self.project and self._project_root:
            self.lbl_project.setText(
                t(
                    "project_label",
                    name=self.project.name,
                    path=str(self._project_root),
                )
            )
        else:
            self.lbl_project.setText(t("no_project"))

        self.lbl_tree_title.setText(t("tree_title"))
        self.tree.setHeaderLabels([t("tree_col_item"), t("tree_col_detail")])
        self.btn_add_page.setText(t("btn_add_page"))
        self.btn_add_macro.setText(t("btn_add_macro"))
        self.btn_del_sel.setText(t("btn_del_sel"))
        self.params_group.setTitle("")
        self.runtime_header.retranslate()  # type: ignore[attr-defined]
        self.help_runtime.retranslate()
        self.help_runtime_advanced.retranslate()
        self.lbl_threshold.setText(t("param_threshold"))
        self.lbl_poll.setText(t("param_poll"))
        self.lbl_ref_w.setText(t("param_ref_w"))
        self.lbl_ref_h.setText(t("param_ref_h"))
        self.lbl_state_near.setText(t("param_state_near"))
        self.lbl_state_margin.setText(t("param_state_margin"))
        self.lbl_log_lang.setText(t("param_log_lang"))
        self.lbl_redecide.setText(t("param_redecide"))
        self.chk_redecide.setText(t("param_redecide_hint"))
        self.lbl_verbose.setText(t("param_verbose"))
        self.chk_verbose.setText(t("param_verbose_hint"))
        self.lbl_runner_mode.setText(t("param_runner_mode"))
        self._fill_runner_mode_combo()
        self.btn_params_advanced.setText(t("params_advanced"))
        self.btn_apply.setText(t("btn_apply"))
        self.btn_start.setText(t("btn_start"))
        self.btn_stop.setText(t("btn_stop"))
        self.lbl_log.setText(t("log_label"))
        self.lbl_tip.setText(t("tip"))
        self.editor.retranslate()
        self._fill_tree()
        self._refresh_status_text()  # also sets Pause / Continue

    def _fill_runner_mode_combo(self) -> None:
        self.cmb_runner_mode.blockSignals(True)
        cur = get_runner_mode()
        # Env override: show effective mode but keep combo reflecting saved preference
        # when env is unset; if env set, still show effective.
        self.cmb_runner_mode.clear()
        self.cmb_runner_mode.addItem(self.t("runner_mode_elevate"), RUNNER_ELEVATE)
        self.cmb_runner_mode.addItem(self.t("runner_mode_inline"), RUNNER_INLINE)
        idx = self.cmb_runner_mode.findData(cur)
        self.cmb_runner_mode.setCurrentIndex(max(0, idx))
        self.cmb_runner_mode.blockSignals(False)

    def _on_runner_mode_changed(self, *_args) -> None:
        data = self.cmb_runner_mode.currentData()
        if data in (RUNNER_ELEVATE, RUNNER_INLINE):
            set_runner_mode(str(data))

    def _switch_lang(self, lang: str) -> None:
        if lang == self.i18n.lang:
            return
        self.i18n.set_lang(lang)
        self._retranslate()
        self._append_log(self.t("log_lang"))

    def _set_controls_enabled(self, on: bool) -> None:
        for w in (
            self.btn_apply,
            self.spin_threshold,
            self.spin_poll,
            self.spin_ref_w,
            self.spin_ref_h,
            self.chk_verbose,
            self.cmb_runner_mode,
            self.btn_add_page,
            self.btn_add_macro,
            self.btn_del_sel,
            self.act_save,
            self.editor,
        ):
            w.setEnabled(on)
        if not on:
            self.btn_start.setEnabled(False)
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)
        else:
            self._refresh_run_buttons()

    def _append_log(self, msg: str) -> None:
        self.log_view.appendPlainText(msg)
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)

    def _engine_log(self, msg: str) -> None:
        self._log_bridge.message.emit(msg)

    def _engine_status(self, payload: dict[str, Any]) -> None:
        self._status_bridge.status.emit(payload)

    def _set_status_idle(self) -> None:
        self._status_payload = None
        self._engine_launching = False
        self._refresh_status_text()

    def _on_engine_status(self, payload: object) -> None:
        if isinstance(payload, dict):
            # Stopped → idle bar (ignore late "stopped" after local clear).
            if payload.get("mode") == "stopped":
                self._status_payload = None
                self._engine_launching = False
            else:
                self._status_payload = payload
                if payload.get("mode") in ("running", "paused"):
                    self._engine_launching = False
        self._refresh_status_text()

    def _engine_is_paused(self) -> bool:
        payload = self._status_payload
        return bool(payload and payload.get("mode") == "paused")

    def _engine_session_active(self) -> bool:
        """True while running, paused, or still launching the Runner."""
        if getattr(self, "_engine_launching", False):
            return True
        payload = self._status_payload
        if payload and payload.get("mode") in ("running", "paused"):
            return True
        if self.runner is not None and self.runner.is_alive:
            return True
        if self.engine is not None and self.engine.status != EngineStatus.STOPPED:
            return True
        return False

    def _refresh_pause_button(self) -> None:
        key = "btn_resume" if self._engine_is_paused() else "btn_pause"
        self.btn_pause.setText(self.t(key))

    def _refresh_run_buttons(self) -> None:
        """Start only when idle; Pause/Stop while a session is active."""
        has_project = self.project is not None
        active = has_project and self._engine_session_active()
        launching = bool(getattr(self, "_engine_launching", False))
        self.btn_start.setEnabled(has_project and not active)
        self.btn_pause.setEnabled(has_project and active and not launching)
        self.btn_stop.setEnabled(has_project and active)
        self._refresh_pause_button()

    def _refresh_status_text(self) -> None:
        t = self.t
        payload = self._status_payload
        self._refresh_run_buttons()
        if not payload:
            self.lbl_status.setText(t("status_idle"))
            return
        mode = str(payload.get("mode") or "")
        page = payload.get("page_label") or payload.get("page_id")
        state = payload.get("state")
        if mode == "running":
            if page and state:
                self.lbl_status.setText(
                    t("status_running", page=page, state=state)
                )
            elif page:
                self.lbl_status.setText(
                    t(
                        "status_running",
                        page=page,
                        state=t("status_na"),
                    )
                )
            else:
                self.lbl_status.setText(t("status_running_unknown"))
        elif mode == "paused":
            if page and state:
                self.lbl_status.setText(
                    t("status_paused", page=page, state=state)
                )
            elif page:
                self.lbl_status.setText(
                    t(
                        "status_paused",
                        page=page,
                        state=t("status_na"),
                    )
                )
            else:
                self.lbl_status.setText(t("status_paused_unknown"))
        else:
            self.lbl_status.setText(t("status_idle"))

    def _about(self) -> None:
        QMessageBox.about(self, self.t("about_title"), self.t("about_body"))

    def _mark_dirty(self) -> None:
        if not self._dirty:
            self._dirty = True
            self._append_log(self.t("log_dirty"))
        self._refresh_window_title()

    def _ask_save_if_dirty(self) -> bool:
        """Return False if user cancels."""
        if self.project:
            self.editor.flush_all()
        if not self._dirty or not self.project:
            return True
        ans = QMessageBox.question(
            self,
            self.t("app_title"),
            self.t("confirm_unsaved"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if ans == QMessageBox.StandardButton.Cancel:
            return False
        if ans == QMessageBox.StandardButton.Save:
            return self.save_project_ui()
        return True

    def _show_welcome(self, show: bool) -> None:
        self.center_stack.setCurrentWidget(self.welcome if show else self.editor)
        if show:
            self.welcome.refresh()

    def _rebuild_recent_menu(self) -> None:
        self._menu_recent.clear()
        recent = get_recent()
        if not recent:
            empty = QAction(self.t("recent_empty"), self)
            empty.setEnabled(False)
            self._menu_recent.addAction(empty)
        else:
            for entry in recent:
                label = f"{entry['name']}    {entry['path']}"
                act = QAction(label, self)
                act.setData(entry["path"])
                act.triggered.connect(
                    lambda checked=False, p=entry["path"]: self.open_recent_path(p)
                )
                self._menu_recent.addAction(act)
            self._menu_recent.addSeparator()
            act_clear = QAction(self.t("recent_clear"), self)
            act_clear.triggered.connect(self.clear_recent_projects)
            self._menu_recent.addAction(act_clear)

    def clear_recent_projects(self) -> None:
        clear_recent()
        self._rebuild_recent_menu()
        self.welcome.refresh()

    def open_recent_path(self, path: str) -> None:
        if not self._ask_save_if_dirty():
            return
        root = Path(path)
        if not root.is_dir() or not (root / "project.json").exists():
            remove_recent(root)
            self._rebuild_recent_menu()
            self.welcome.refresh()
            QMessageBox.warning(
                self, self.t("err_title"), self.t("err_recent_missing", path=path)
            )
            return
        self._load_path(root)

    def new_project(self) -> None:
        if not self._ask_save_if_dirty():
            return
        name, ok = QInputDialog.getText(
            self, self.t("dlg_new_name"), self.t("dlg_new_name_label")
        )
        if not ok:
            return
        name = name.strip() or self.t("dlg_new_name_default")
        parent = QFileDialog.getExistingDirectory(
            self,
            self.t("dlg_new_parent"),
            get_last_dir("new"),
        )
        if not parent:
            return
        folder = safe_folder_name(name, fallback=self.t("dlg_new_name_default"))
        root = Path(parent) / folder
        if root.exists():
            if (root / "project.json").exists():
                ans = QMessageBox.question(
                    self,
                    self.t("dlg_new_name"),
                    self.t("confirm_open_existing", path=str(root)),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if ans == QMessageBox.StandardButton.Yes:
                    set_last_dir("new", parent)
                    self._load_path(root)
                return
            if any(root.iterdir()):
                QMessageBox.warning(
                    self,
                    self.t("err_title"),
                    self.t("err_folder_not_empty", path=str(root)),
                )
                return
        try:
            set_last_dir("new", parent)
            created = new_blank_project(root, name=name)
            self._load_path(created)
        except Exception as exc:
            QMessageBox.critical(self, self.t("err_title"), str(exc))

    def open_project(self) -> None:
        if not self._ask_save_if_dirty():
            return
        path = QFileDialog.getExistingDirectory(
            self, self.t("dlg_open_title"), get_last_dir("open")
        )
        if not path:
            return
        set_last_dir("open", path)
        self._load_path(Path(path))

    def save_project_ui(self) -> bool:
        if not self.project:
            return False
        try:
            self.editor.flush_all()
            self.apply_params(persist=False)
            path = save_project(self.project)
            self._dirty = False
            self._refresh_window_title()
            self._append_log(self.t("log_saved", path=str(path)))
            if self._is_engine_active():
                QMessageBox.information(
                    self,
                    self.t("err_title"),
                    self.t("save_reload_hint"),
                )
            return True
        except Exception as exc:
            QMessageBox.critical(self, self.t("err_save_title"), str(exc))
            return False

    def _is_engine_active(self) -> bool:
        return self._engine_session_active()

    def _load_path(self, root: Path) -> None:
        try:
            self.stop_engine()
            self.project = load_project(root)
            self._project_root = root
            self._dirty = False
            self._refresh_window_title()
        except Exception as exc:
            QMessageBox.critical(self, self.t("err_open_title"), str(exc))
            return

        self.editor.set_project(self.project)
        touch_recent(root, self.project.name)
        self._show_welcome(False)
        self._retranslate()
        rt = self.project.runtime
        self.spin_threshold.setValue(rt.match_threshold)
        self.spin_poll.setValue(rt.poll_interval)
        self.spin_ref_w.setValue(rt.ref_width)
        self.spin_ref_h.setValue(rt.ref_height)
        self.spin_state_near.setValue(rt.state_near)
        self.spin_state_margin.setValue(rt.state_conf_margin)
        li = self.cmb_log_lang.findData(rt.log_language or "en")
        self.cmb_log_lang.setCurrentIndex(max(0, li))
        self.chk_redecide.setChecked(rt.allow_redecide_during_action)
        self.chk_verbose.setChecked(rt.verbose_log)
        self._set_controls_enabled(True)
        self._append_log(self.t("log_opened", path=str(root)))

    def _item_ctx(self, item: QTreeWidgetItem | None) -> dict[str, Any] | None:
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        return data if isinstance(data, dict) else None

    def _nav_state_detail(self, node) -> str:
        t = self.t
        if node.is_else:
            return t("tree_state_else")
        if node.children:
            return t("tree_state_branch", n=len(node.children))
        extra = t("st_detail_post") if node.post else ""
        base = t("st_detail_leaf", n=len(node.actions))
        return f"{base} · {extra}" if extra else base

    def _add_nav_state_items(
        self, parent_item: QTreeWidgetItem, page_id: str, nodes: list
    ) -> None:
        t = self.t
        for node in nodes:
            tag = t("st_else_tag") if node.is_else else ""
            child = QTreeWidgetItem(
                [f"{node.display_name()}{tag}", self._nav_state_detail(node)]
            )
            child.setData(
                0,
                Qt.ItemDataRole.UserRole,
                {
                    "kind": KIND_STATE_NODE,
                    "page_id": page_id,
                    "node_id": node.id,
                },
            )
            parent_item.addChild(child)
            if node.children:
                self._add_nav_state_items(child, page_id, node.children)

    @staticmethod
    def _expand_item_recursive(item: QTreeWidgetItem) -> None:
        item.setExpanded(True)
        for i in range(item.childCount()):
            StudioWindow._expand_item_recursive(item.child(i))

    def _on_nav_item_expanded(self, item: QTreeWidgetItem) -> None:
        """Opening a page expands its full state subtree for browsing."""
        if self._filling_tree:
            return
        ctx = self._item_ctx(item)
        if not ctx or ctx.get("kind") != KIND_PAGE:
            return
        for i in range(item.childCount()):
            self._expand_item_recursive(item.child(i))

    def _fill_tree(self) -> None:
        """Pages + nested state nav; click a state to focus it in the center editor."""
        self._filling_tree = True
        selected = self._item_ctx(self.tree.currentItem())
        self.tree.clear()
        if not self.project:
            self._filling_tree = False
            return
        t = self.t

        macros_root = QTreeWidgetItem(
            [t("tree_macros"), t("tree_group_count", n=len(self.project.macros))]
        )
        macros_root.setData(0, Qt.ItemDataRole.UserRole, {"kind": KIND_MACROS})
        self.tree.addTopLevelItem(macros_root)
        for mid, macro in self.project.macros.items():
            n_steps = len(macro.steps or [])
            m_item = QTreeWidgetItem(
                [macro.name or mid, t("tree_macro_detail_short", n=n_steps)]
            )
            m_item.setData(
                0, Qt.ItemDataRole.UserRole, {"kind": KIND_MACRO, "macro_id": mid}
            )
            macros_root.addChild(m_item)
        macros_root.setExpanded(True)

        pages_root = QTreeWidgetItem(
            [t("tree_pages"), t("tree_group_count", n=len(self.project.pages))]
        )
        pages_root.setData(0, Qt.ItemDataRole.UserRole, {"kind": KIND_PAGES})
        self.tree.addTopLevelItem(pages_root)

        pairs_item = QTreeWidgetItem([t("tree_page_pairs"), ""])
        pairs_item.setData(
            0, Qt.ItemDataRole.UserRole, {"kind": KIND_PAGE_PAIRS}
        )
        pages_root.addChild(pairs_item)

        expand_page_id: str | None = None
        if selected and selected.get("kind") in (
            KIND_PAGE,
            KIND_STATE_TREE,
            KIND_STATE_NODE,
        ):
            expand_page_id = str(selected.get("page_id") or "")

        for page_id, page in self.project.pages.items():
            detail = ""
            if page.pair_with:
                sibling = self.project.pages.get(page.pair_with)
                other = sibling.display_name() if sibling else page.pair_with
                detail = t("tree_page_pair_hint", name=other)
            page_item = QTreeWidgetItem([page.display_name(), detail])
            page_item.setData(
                0, Qt.ItemDataRole.UserRole, {"kind": KIND_PAGE, "page_id": page_id}
            )
            pages_root.addChild(page_item)

            self._add_nav_state_items(page_item, page_id, page.state_tree)
            if page_id == expand_page_id:
                self._expand_item_recursive(page_item)
            else:
                page_item.setExpanded(False)

        pages_root.setExpanded(True)

        if selected:
            self._reselect(selected)
        self._filling_tree = False

    def _reselect(self, ctx: dict[str, Any]) -> None:
        def walk(item: QTreeWidgetItem) -> bool:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, dict) and data == ctx:
                self.tree.setCurrentItem(item)
                return True
            for i in range(item.childCount()):
                if walk(item.child(i)):
                    return True
            return False

        for i in range(self.tree.topLevelItemCount()):
            if walk(self.tree.topLevelItem(i)):
                return

    def _select_ctx(self, ctx: object) -> None:
        if not isinstance(ctx, dict):
            return
        self._reselect(ctx)
        # If tree had no matching item (e.g. stale id), still open the editor.
        if self._item_ctx(self.tree.currentItem()) != ctx:
            self.editor.show_selection(ctx)

    def _on_tree_select(self) -> None:
        if self._filling_tree or not self.project:
            return
        item = self.tree.currentItem()
        ctx = self._item_ctx(item)
        if not ctx:
            self.editor.show_empty()
            return
        kind = ctx.get("kind")
        # Selecting a page expands its full state list for browsing
        if kind == KIND_PAGE and item is not None:
            self._expand_item_recursive(item)
        if kind in (
            KIND_PAGE,
            KIND_STATE_TREE,
            KIND_STATE_NODE,
            KIND_MACRO,
            KIND_MACROS,
            KIND_PAGES,
            KIND_PAGE_PAIRS,
        ):
            self.editor.show_selection(ctx)
        else:
            self.editor.show_empty()

    def add_page(self) -> None:
        if not self.project:
            return
        wiz = NewPageWizard(self.t, self)
        if wiz.exec() != NewPageWizard.DialogCode.Accepted:
            return
        name = wiz.page_name.strip()
        if not name:
            return
        page_id = slugify_id(name, self.project.pages.keys(), fallback="page")
        self.project.pages[page_id] = make_page(page_id, name=name)
        ensure_page_asset_dirs(self.project, page_id)
        if wiz.image_path:
            try:
                asset = upload_page_asset(
                    self.project,
                    page_id,
                    "detect",
                    wiz.image_path,
                    preferred_name="main",
                )
                self.project.pages[page_id].detect_relpath = asset.relpath
            except Exception as exc:
                QMessageBox.warning(self, self.t("err_title"), str(exc))
        self._mark_dirty()
        self._fill_tree()
        if wiz.edit_actions:
            self.editor.show_selection(
                {"kind": KIND_STATE_TREE, "page_id": page_id}
            )
        else:
            self.editor.show_selection({"kind": KIND_PAGE, "page_id": page_id})

    def add_macro(self) -> None:
        if not self.project:
            return
        text, ok = QInputDialog.getText(
            self, self.t("dlg_macro_name"), self.t("dlg_macro_name_label")
        )
        if not ok or not text.strip():
            return
        name = text.strip()
        mid = slugify_id(name, self.project.macros.keys(), fallback="macro")
        self.project.macros[mid] = make_macro(mid, name=name)
        self._mark_dirty()
        self._fill_tree()
        self.editor.show_selection({"kind": KIND_MACRO, "macro_id": mid})

    def delete_selection(self) -> None:
        if not self.project:
            return
        ctx = self._item_ctx(self.tree.currentItem())
        if not ctx:
            return
        kind = ctx.get("kind")
        if kind == KIND_PAGE:
            page_id = str(ctx["page_id"])
            label = self.project.pages[page_id].display_name()
            if (
                QMessageBox.question(
                    self,
                    self.t("err_title"),
                    self.t("confirm_delete", name=label),
                )
                != QMessageBox.StandardButton.Yes
            ):
                return
            clear_pairs_involving(self.project, page_id)
            del self.project.pages[page_id]
            self._mark_dirty()
            self.editor.show_empty()
            self._fill_tree()
        elif kind == KIND_MACRO:
            mid = str(ctx["macro_id"])
            label = self.project.macros[mid].name or mid
            if (
                QMessageBox.question(
                    self,
                    self.t("err_title"),
                    self.t("confirm_delete", name=label),
                )
                != QMessageBox.StandardButton.Yes
            ):
                return
            del self.project.macros[mid]
            self._mark_dirty()
            self.editor.show_empty()
            self._fill_tree()
    def apply_params(self, persist: bool = True) -> None:
        if not self.project:
            return
        rt = self.project.runtime
        rt.match_threshold = self.spin_threshold.value()
        rt.poll_interval = self.spin_poll.value()
        rt.ref_width = self.spin_ref_w.value()
        rt.ref_height = self.spin_ref_h.value()
        rt.state_near = self.spin_state_near.value()
        rt.state_conf_margin = self.spin_state_margin.value()
        rt.log_language = str(self.cmb_log_lang.currentData() or "en")
        rt.allow_redecide_during_action = self.chk_redecide.isChecked()
        rt.verbose_log = self.chk_verbose.isChecked()
        if self.engine:
            self.engine.runtime = rt
            self.engine.sync_runtime()
        elif self.runner is not None and self.runner.is_alive:
            self.runner.send_set_runtime(
                {
                    "match_threshold": rt.match_threshold,
                    "poll_interval": rt.poll_interval,
                    "ref_width": rt.ref_width,
                    "ref_height": rt.ref_height,
                    "state_near": rt.state_near,
                    "state_conf_margin": rt.state_conf_margin,
                    "log_language": rt.log_language,
                    "allow_redecide_during_action": rt.allow_redecide_during_action,
                    "verbose_log": rt.verbose_log,
                }
            )
        if persist:
            self._mark_dirty()
        self._append_log(self.t("log_params"))

    def start_engine(self) -> None:
        if not self.project or not self._project_root:
            return
        # Already running/paused: use Pause/Continue or Stop — do not re-Start.
        if self._engine_session_active():
            return
        self.editor.flush_all()
        issues = validate_for_start(self.project, self.t)
        errors = [i.text for i in issues if i.level == "error"]
        warnings = [i.text for i in issues if i.level == "warning"]
        if errors:
            QMessageBox.warning(
                self,
                self.t("val_title"),
                "\n".join(errors),
            )
            return
        if warnings:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle(self.t("val_warn_title"))
            box.setText("\n".join(warnings))
            btn_go = box.addButton(
                self.t("val_continue"), QMessageBox.ButtonRole.AcceptRole
            )
            box.addButton(self.t("val_abort"), QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is not btn_go:
                return
        self.apply_params(persist=False)
        rebuild_resource_index(self.project)
        # Runner loads from disk — always save so memory and files match.
        try:
            save_project(self.project)
            self._dirty = False
            self._refresh_window_title()
        except Exception as exc:
            QMessageBox.critical(self, self.t("err_save_title"), str(exc))
            return
        self._engine_launching = True
        self._refresh_run_buttons()
        mode = get_runner_mode()
        # Tests / explicit override
        if (os.environ.get("SCREENFLOW_RUNNER") or "").strip().lower() == RUNNER_INLINE:
            mode = RUNNER_INLINE
        if mode == RUNNER_INLINE:
            try:
                self.engine = FlowEngine(
                    self.project,
                    log=self._engine_log,
                    status=self._engine_status,
                )
                self.engine.start()
            except Exception as exc:
                QMessageBox.critical(self, self.t("err_title"), str(exc))
                self.engine = None
                self._set_status_idle()
            return
        self.lbl_status.setText(self.t("status_waiting_admin"))
        QApplication.processEvents()
        try:
            client = RunnerClient(self)
            client.log_message.connect(self._engine_log)
            client.status_payload.connect(self._engine_status)
            client.failed.connect(self._on_runner_failed)
            client.exited.connect(lambda _c: self._on_runner_exited())
            self.runner = client
            client.start_session(self._project_root, elevate=True)
            client.send_start()
        except Exception as exc:
            msg = str(exc) or self.t("err_runner_uac")
            QMessageBox.critical(self, self.t("err_title"), msg)
            self.runner = None
            self._set_status_idle()

    def _on_runner_failed(self, text: str) -> None:
        self._engine_launching = False
        self._append_log(text)
        QMessageBox.warning(self, self.t("err_title"), text or self.t("err_runner"))
        self._refresh_run_buttons()

    def _on_runner_exited(self) -> None:
        if self.runner is not None:
            self.runner.stop_session(send_stop=False)
            self.runner = None
        self._set_status_idle()

    def _set_run_mode_ui(self, mode: str) -> None:
        """Optimistic status for Pause/Continue button (runner may lag one frame)."""
        base = dict(self._status_payload or {})
        base["mode"] = mode
        self._status_payload = base
        self._refresh_status_text()

    def pause_engine(self) -> None:
        """Pause when running; resume (Continue) when paused."""
        if self._engine_is_paused():
            if self.runner is not None and self.runner.is_alive:
                self.runner.send_start()
                self._set_run_mode_ui("running")
                return
            if self.engine:
                self.engine.start()
                self._set_run_mode_ui("running")
            return
        if self.runner is not None and self.runner.is_alive:
            self.runner.send_pause()
            self._set_run_mode_ui("paused")
            return
        if self.engine:
            self.engine.pause()
            self._set_run_mode_ui("paused")

    def stop_engine(self) -> None:
        self._engine_launching = False
        if self.runner is not None:
            self.runner.stop_session(send_stop=True)
            self.runner = None
        if self.engine:
            self.engine.stop()
            self.engine = None
        self._set_status_idle()

    def closeEvent(self, event) -> None:  # noqa: N802
        if not self._ask_save_if_dirty():
            event.ignore()
            return
        self._persist_session_ui()
        self.stop_engine()
        super().closeEvent(event)


def run_studio() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("ScreenFlow")
    app.setStyle("Fusion")
    from studio.no_wheel import install_no_wheel_value_change

    # Keep filter alive for the app lifetime (parented to app)
    install_no_wheel_value_change(app)
    win = StudioWindow()
    # Backup if the window close path is skipped: still tear down the Runner.
    app.aboutToQuit.connect(win.stop_engine)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_studio()
