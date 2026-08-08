from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from screenflow.assets import PageAsset
from screenflow.models import ActionStep, Project
from studio.asset_picker import AssetNameCombo
from studio.section_help import section_title_row

COMMON_OPS = (
    "click",
    "key",
    "wait",
    "hold_key",
    "macro",
)
ADVANCED_OPS = (
    "set_var",
    "clear_var",
    "script",
)
OPS = COMMON_OPS + ADVANCED_OPS


class StepsEditor(QWidget):
    """Ordered action-step list with add / remove / reorder."""

    changed = Signal()

    def __init__(
        self,
        t,
        parent: QWidget | None = None,
        *,
        section_help: bool = True,
    ) -> None:
        super().__init__(parent)
        self._t = t
        self._steps: list[ActionStep] = []
        self._macros: list[tuple[str, str]] = []
        self._click_keys: list[str] = []
        self._click_assets: list[PageAsset] = []
        self._project: Project | None = None
        self._block = False
        self._section_help = section_help

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.hdr_steps = None
        self.help_steps = None
        if section_help:
            self.hdr_steps, _, self.help_steps = section_title_row(
                self._t, "st_actions", "help_steps"
            )
            root.addWidget(self.hdr_steps)

        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._on_select)
        root.addWidget(self.list, stretch=1)

        btns = QHBoxLayout()
        self.btn_add = QPushButton()
        self.btn_add.clicked.connect(self._add)
        self.btn_del = QPushButton()
        self.btn_del.clicked.connect(self._delete)
        self.btn_up = QPushButton()
        self.btn_up.clicked.connect(lambda: self._move(-1))
        self.btn_down = QPushButton()
        self.btn_down.clicked.connect(lambda: self._move(1))
        for b in (self.btn_add, self.btn_del, self.btn_up, self.btn_down):
            btns.addWidget(b)
        root.addLayout(btns)

        self.form_box = QWidget()
        form = QFormLayout(self.form_box)
        self.cmb_op = QComboBox()
        self.cmb_op.currentIndexChanged.connect(self._on_op_index_changed)

        self.ed_target = QLineEdit()
        self.ed_target.editingFinished.connect(self._commit_current)
        self.cmb_click = AssetNameCombo()
        self.cmb_click.selection_changed.connect(self._commit_current)
        self.cmb_target = QComboBox()
        self.cmb_target.setEditable(True)
        self.cmb_target.currentTextChanged.connect(self._commit_current)
        self.spin_target = QDoubleSpinBox()
        self.spin_target.setRange(0.0, 3600.0)
        self.spin_target.setDecimals(2)
        self.spin_target.setSingleStep(0.1)
        self.spin_target.valueChanged.connect(self._commit_current)

        self.target_stack = QWidget()
        self._target_layout = QVBoxLayout(self.target_stack)
        self._target_layout.setContentsMargins(0, 0, 0, 0)
        self._target_layout.addWidget(self.ed_target)
        self._target_layout.addWidget(self.cmb_click)
        self._target_layout.addWidget(self.cmb_target)
        self._target_layout.addWidget(self.spin_target)

        self.spin_hold = QDoubleSpinBox()
        self.spin_hold.setRange(0.0, 3600.0)
        self.spin_hold.setDecimals(2)
        self.spin_hold.setSingleStep(0.1)
        self.spin_hold.valueChanged.connect(self._commit_current)

        self.ed_reason = QLineEdit()
        self.ed_reason.editingFinished.connect(self._commit_current)

        self.ed_params = QLineEdit()
        self.ed_params.editingFinished.connect(self._commit_current)

        self.lbl_op = QLabel()
        self.lbl_target = QLabel()
        self.lbl_hold = QLabel()
        self.lbl_params = QLabel()
        self.lbl_reason = QLabel()
        form.addRow(self.lbl_op, self.cmb_op)
        form.addRow(self.lbl_target, self.target_stack)
        self._hold_row_widgets = (self.lbl_hold, self.spin_hold)
        form.addRow(self.lbl_hold, self.spin_hold)
        form.addRow(self.lbl_params, self.ed_params)
        form.addRow(self.lbl_reason, self.ed_reason)
        root.addWidget(self.form_box)

        self.retranslate()
        self._show_target_widget("wait")

    def _op_label(self, op: str) -> str:
        key = f"step_op_{op}"
        label = self._t(key)
        return label if label != key else op

    def _current_op(self) -> str:
        data = self.cmb_op.currentData()
        return str(data) if data else "wait"

    def _set_op(self, op: str) -> None:
        idx = self.cmb_op.findData(op if op in OPS else "wait")
        self.cmb_op.setCurrentIndex(max(0, idx))

    def _rebuild_op_combo(self) -> None:
        self._block = True
        op = self._current_op() if self.cmb_op.count() else "wait"
        self.cmb_op.clear()
        for key in COMMON_OPS:
            self.cmb_op.addItem(self._op_label(key), key)
        self.cmb_op.insertSeparator(self.cmb_op.count())
        # Non-selectable section header (disabled item after separator)
        hdr = self._t("step_op_advanced")
        self.cmb_op.addItem(hdr, None)
        idx_hdr = self.cmb_op.count() - 1
        model = self.cmb_op.model()
        item = getattr(model, "item", lambda _i: None)(idx_hdr)
        if item is not None:
            item.setEnabled(False)
        for key in ADVANCED_OPS:
            self.cmb_op.addItem(self._op_label(key), key)
        self._set_op(op)
        self._block = False

    def _target_label_for_op(self, op: str) -> str:
        key = f"step_target_{op}"
        label = self._t(key)
        return label if label != key else self._t("step_target")

    def _update_target_label(self, op: str | None = None) -> None:
        self.lbl_target.setText(self._target_label_for_op(op or self._current_op()))

    def retranslate(self) -> None:
        t = self._t
        if self.hdr_steps is not None:
            self.hdr_steps.retranslate()  # type: ignore[attr-defined]
        if self.help_steps is not None:
            self.help_steps.retranslate()
        self.btn_add.setText(t("step_add"))
        self.btn_del.setText(t("step_del"))
        self.btn_up.setText(t("step_up"))
        self.btn_down.setText(t("step_down"))
        self.lbl_op.setText(t("step_op"))
        self._update_target_label()
        self.lbl_hold.setText(t("step_hold"))
        self.lbl_params.setText(t("step_params"))
        self.ed_params.setPlaceholderText(t("step_ph_params"))
        self.lbl_reason.setText(t("step_reason"))
        self._rebuild_op_combo()
        self._refresh_list()

    def set_catalog(
        self,
        *,
        macro_ids: list[str] | None = None,
        macros: list[tuple[str, str]] | None = None,
        click_keys: list[str] | None = None,
        click_assets: list[PageAsset] | None = None,
        project: Project | None = None,
    ) -> None:
        if macros is not None:
            self._macros = list(macros)
        elif macro_ids is not None:
            self._macros = [(m, m) for m in macro_ids]
        else:
            self._macros = []
        if click_keys is not None:
            self._click_keys = list(click_keys)
        if click_assets is not None:
            self._click_assets = list(click_assets)
        elif click_keys is not None:
            self._click_assets = []
        if project is not None:
            self._project = project
        self._refill_click_combo()

    def set_steps(self, steps: list[ActionStep]) -> None:
        self._block = True
        self._steps = [
            ActionStep(
                op=s.op,
                target=s.target,
                reason=s.reason,
                hold=s.hold,
                params=dict(s.params) if s.params else None,
            )
            for s in steps
        ]
        self._refresh_list()
        self._block = False
        if self._steps:
            self.list.setCurrentRow(0)
        else:
            self._clear_form()

    def get_steps(self) -> list[ActionStep]:
        # Silent commit: callers often sync memory on `changed`; emitting again
        # would recurse (_on_steps_changed → get_steps → commit → changed → …).
        self._commit_current(emit=False)
        return [
            ActionStep(
                op=s.op,
                target=s.target,
                reason=s.reason,
                hold=s.hold,
                params=dict(s.params) if s.params else None,
            )
            for s in self._steps
        ]

    def _refresh_list(self) -> None:
        row = self.list.currentRow()
        self.list.clear()
        for s in self._steps:
            target = "" if s.target is None else str(s.target)
            if s.op == "hold_key":
                hold = "" if s.hold is None else str(s.hold)
                text = f"{self._op_label(s.op)}  {target} × {hold}s"
            else:
                text = f"{self._op_label(s.op)}  {target}".rstrip()
            if s.reason:
                text += f"  — {s.reason}"
            self.list.addItem(QListWidgetItem(text))
        if 0 <= row < len(self._steps):
            self.list.setCurrentRow(row)

    def _clear_form(self) -> None:
        self._block = True
        self._set_op("wait")
        self.spin_target.setValue(0.5)
        self.spin_hold.setValue(1.0)
        self.ed_target.clear()
        # Keep click catalog binding; only reset the visible selection.
        self.cmb_click.blockSignals(True)
        if self.cmb_click.count() > 0:
            self.cmb_click.setCurrentIndex(0)
        self.cmb_click.blockSignals(False)
        self.cmb_target.setCurrentText("")
        self.ed_reason.clear()
        self.ed_params.clear()
        self.form_box.setEnabled(False)
        self._block = False

    def _on_select(self, row: int) -> None:
        if row < 0 or row >= len(self._steps):
            self._clear_form()
            return
        self.form_box.setEnabled(True)
        step = self._steps[row]
        self._block = True
        self._set_op(step.op if step.op in OPS else "wait")
        self._show_target_widget(step.op)
        self._fill_target(step)
        if step.params:
            self.ed_params.setText(json.dumps(step.params, ensure_ascii=False))
        else:
            self.ed_params.clear()
        self.ed_reason.setText(step.reason or "")
        self._block = False

    def _set_hold_row_visible(self, visible: bool) -> None:
        self.lbl_hold.setVisible(visible)
        self.spin_hold.setVisible(visible)

    def _set_params_row_visible(self, visible: bool) -> None:
        self.lbl_params.setVisible(visible)
        self.ed_params.setVisible(visible)

    def _refill_click_combo(self, selected: str | None = None) -> None:
        if self._click_assets:
            self.cmb_click.fill_assets(
                self._project,
                self._click_assets,
                selected=selected,
                allow_empty=True,
                kind="click",
            )
        else:
            # Fallback: names only (no hover path)
            keep = selected if selected is not None else self.cmb_click.current_name()
            self.cmb_click.blockSignals(True)
            self.cmb_click.clear()
            self.cmb_click.addItem("—", None)
            for name in self._click_keys:
                self.cmb_click.addItem(name, name)
            if keep:
                idx = self.cmb_click.findText(keep)
                self.cmb_click.setCurrentIndex(idx if idx >= 0 else 0)
            self.cmb_click.blockSignals(False)

    def _show_target_widget(self, op: str) -> None:
        self.ed_target.setVisible(op in ("key", "hold_key", "set_var", "clear_var", "script"))
        self.cmb_click.setVisible(op == "click")
        self.cmb_target.setVisible(op == "macro")
        self.spin_target.setVisible(op == "wait")
        self._set_hold_row_visible(op == "hold_key")
        self._set_params_row_visible(op == "script")
        self._update_target_label(op)
        if op == "set_var":
            self.ed_target.setPlaceholderText(self._t("step_ph_set_var"))
        elif op == "clear_var":
            self.ed_target.setPlaceholderText(self._t("step_ph_clear_var"))
        elif op == "script":
            self.ed_target.setPlaceholderText(self._t("step_ph_script"))
        elif op == "hold_key":
            self.ed_target.setPlaceholderText(self._t("step_ph_hold_key"))
        elif op == "key":
            self.ed_target.setPlaceholderText(self._t("step_ph_key"))
        else:
            self.ed_target.setPlaceholderText("")
        if op == "click":
            self._refill_click_combo(self.cmb_click.current_name())
        elif op == "macro":
            self.cmb_target.blockSignals(True)
            cur_id = self.cmb_target.currentData()
            if cur_id is None:
                cur_id = self.cmb_target.currentText()
            self.cmb_target.clear()
            for mid, label in self._macros:
                self.cmb_target.addItem(label, mid)
            idx = self.cmb_target.findData(cur_id)
            if idx >= 0:
                self.cmb_target.setCurrentIndex(idx)
            elif cur_id:
                self.cmb_target.setEditText(str(cur_id))
            self.cmb_target.blockSignals(False)

    def _fill_target(self, step: ActionStep) -> None:
        if step.op == "wait":
            try:
                self.spin_target.setValue(float(step.target or 0))
            except (TypeError, ValueError):
                self.spin_target.setValue(0.5)
        elif step.op == "hold_key":
            self.ed_target.setText(str(step.target or "space"))
            try:
                self.spin_hold.setValue(float(step.hold if step.hold is not None else 1.0))
            except (TypeError, ValueError):
                self.spin_hold.setValue(1.0)
        elif step.op == "macro":
            mid = str(step.target or "")
            idx = self.cmb_target.findData(mid)
            if idx >= 0:
                self.cmb_target.setCurrentIndex(idx)
            else:
                self.cmb_target.setEditText(mid)
        elif step.op == "click":
            self._refill_click_combo(str(step.target or "") or None)
        else:
            self.ed_target.setText(str(step.target or ""))

    def _on_op_index_changed(self, _index: int) -> None:
        if self._block:
            return
        # Skip disabled section header
        if self.cmb_op.currentData() is None:
            row = self.list.currentRow()
            if 0 <= row < len(self._steps):
                self._block = True
                self._set_op(self._steps[row].op if self._steps[row].op in OPS else "wait")
                self._block = False
            return
        op = self._current_op()
        self._show_target_widget(op)
        self._commit_current()

    def _read_target(self, op: str):
        if op == "wait":
            return float(self.spin_target.value())
        if op == "macro":
            data = self.cmb_target.currentData()
            if data:
                return str(data)
            return self.cmb_target.currentText().strip() or None
        if op == "click":
            return self.cmb_click.current_name()
        return self.ed_target.text().strip() or None

    def _read_hold(self, op: str) -> float | None:
        if op == "hold_key":
            return float(self.spin_hold.value())
        return None

    def _read_params(self, op: str) -> dict[str, Any] | None:
        if op != "script":
            return None
        text = self.ed_params.text().strip()
        if not text:
            return None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            QMessageBox.warning(
                self, self._t("err_title"), self._t("step_params_invalid")
            )
            return self._steps[self.list.currentRow()].params
        if not isinstance(data, dict):
            QMessageBox.warning(
                self, self._t("err_title"), self._t("step_params_invalid")
            )
            return self._steps[self.list.currentRow()].params
        return dict(data)

    def _commit_current(self, *, emit: bool = True) -> None:
        if self._block:
            return
        row = self.list.currentRow()
        if row < 0 or row >= len(self._steps):
            return
        if self.cmb_op.currentData() is None:
            return
        op = self._current_op()
        reason = self.ed_reason.text().strip() or None
        target = self._read_target(op)
        if op == "hold_key" and not target:
            target = "space"
        self._steps[row] = ActionStep(
            op=op,
            target=target,
            reason=reason,
            hold=self._read_hold(op),
            params=self._read_params(op),
        )
        if not emit:
            return
        self._refresh_list()
        self.list.setCurrentRow(row)
        self.changed.emit()

    def _add(self) -> None:
        self._commit_current(emit=False)
        self._steps.append(ActionStep(op="wait", target=0.5))
        self._refresh_list()
        self.list.setCurrentRow(len(self._steps) - 1)
        self.changed.emit()

    def _delete(self) -> None:
        row = self.list.currentRow()
        if row < 0 or row >= len(self._steps):
            return
        del self._steps[row]
        self._refresh_list()
        if self._steps:
            self.list.setCurrentRow(min(row, len(self._steps) - 1))
        else:
            self._clear_form()
        self.changed.emit()

    def _move(self, delta: int) -> None:
        row = self.list.currentRow()
        new = row + delta
        if row < 0 or new < 0 or new >= len(self._steps):
            return
        self._commit_current(emit=False)
        self._steps[row], self._steps[new] = self._steps[new], self._steps[row]
        self._refresh_list()
        self.list.setCurrentRow(new)
        self.changed.emit()
