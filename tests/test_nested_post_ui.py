"""Follow-up tree editor hides nested post UI."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from studio.i18n import I18n
from studio.state_tree_ui import StateTreeEditor


def test_nested_post_hidden_when_disallowed():
    app = QApplication.instance() or QApplication(sys.argv)
    editor = StateTreeEditor(I18n().t, allow_nested_post=False)
    assert not editor.grp_post.isVisibleTo(editor)
    assert not editor._allow_nested_post
