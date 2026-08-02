"""StepsEditor: add/commit must not recurse through changed → get_steps."""

from screenflow.models import ActionStep
from studio.steps_editor import StepsEditor


class _T:
    def __call__(self, key: str, **kwargs: object) -> str:
        return key


def test_add_step_with_changed_handler_calling_get_steps():
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    ed = StepsEditor(_T())
    hits = {"n": 0}

    def on_changed() -> None:
        hits["n"] += 1
        # Same pattern as StateTreeEditor / EditorPanel
        steps = ed.get_steps()
        assert len(steps) == hits["n"]

    ed.changed.connect(on_changed)
    ed.set_steps([])
    ed._add()
    assert hits["n"] == 1
    assert len(ed.get_steps()) == 1
    assert ed.get_steps()[0].op == "wait"

    ed._add()
    assert hits["n"] == 2
    assert len(ed.get_steps()) == 2


def test_commit_then_get_steps_does_not_reemit():
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    ed = StepsEditor(_T())
    ed.set_steps([ActionStep(op="wait", target=0.5)])
    count = {"n": 0}
    ed.changed.connect(lambda: count.__setitem__("n", count["n"] + 1))
    ed.get_steps()
    assert count["n"] == 0
