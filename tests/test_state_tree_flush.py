"""StateTreeEditor.flush_current_node writes form fields without Apply."""

from screenflow.models import ScoreSpec, StateNode
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
