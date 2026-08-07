"""StateTreeEditor.flush_current_node writes form fields without Apply."""

from screenflow.models import ActionStep, ScoreSpec, StateNode
from studio.state_tree_ui import StateTreeEditor


class _T:
    def __call__(self, key: str, **kwargs: object) -> str:
        if kwargs:
            try:
                return key.format(**kwargs)
            except Exception:
                return key
        return key


def test_flush_updates_name_without_apply():
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    editor = StateTreeEditor(_T())
    a = StateNode(id="a", name="A", score=ScoreSpec(key="main"), priority=10)
    b = StateNode(id="b", name="B", is_else=True, priority=0)
    editor.bind([a, b], select_id="a")
    editor.ed_name.setText("Renamed")
    editor.flush_current_node(rebuild=False)
    assert a.name == "Renamed"


def test_flush_before_select_keeps_edits():
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    editor = StateTreeEditor(_T())
    a = StateNode(id="a", name="A", score=ScoreSpec(key="main"), priority=10)
    b = StateNode(id="b", name="B", is_else=True, priority=0)
    editor.bind([a, b], select_id="a")
    editor.ed_name.setText("Kept")
    # Simulate switching selection: flush then load B
    editor.flush_current_node(rebuild=False)
    editor._load_node_into_form(b)
    assert a.name == "Kept"
    assert editor._selected_id == "b"


def test_flush_else_keeps_actions():
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    editor = StateTreeEditor(_T())
    step = ActionStep(op="wait", target=0.5)
    a = StateNode(
        id="a",
        name="A",
        score=ScoreSpec(key="main"),
        priority=10,
        actions=[step],
    )
    editor.bind([a], select_id="a")
    editor.chk_else.setChecked(True)
    editor.flush_current_node(rebuild=True)
    assert a.is_else
    assert a.score is None
    assert len(a.actions) == 1
    assert a.actions[0].op == "wait"
