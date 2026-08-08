"""allow_redecide_during_action aborts pack when page changes between steps."""

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from screenflow.actions import ActionRunner
from screenflow.logfmt import EngineLog
from screenflow.models import (
    ActionStep,
    MatchResult,
    Project,
    RuntimeConfig,
)


def test_abort_pack_on_page_change():
    rt = RuntimeConfig(allow_redecide_during_action=True, action_delay=0, action_cooldown=0)
    project = Project(
        name="t",
        root=Path("."),
        runtime=rt,
        pages={},
        feature_files={},
    )
    matcher = MagicMock()
    matcher.capture_screen.return_value = np.zeros((4, 4, 3), dtype=np.uint8)
    matcher.detect_page.return_value = MatchResult(
        page_id="other", confidence=0.9, center=(1, 1)
    )
    input_ctrl = MagicMock()
    runner = ActionRunner(
        project, matcher, input_ctrl, EngineLog(None), is_running=lambda: True
    )
    ok = runner.run_steps(
        [ActionStep("wait", 0.0), ActionStep("wait", 0.0)],
        np.zeros((4, 4, 3), dtype=np.uint8),
        {},
        page_id="p",
    )
    assert ok is False


def test_no_abort_when_flag_off():
    rt = RuntimeConfig(allow_redecide_during_action=False, action_delay=0, action_cooldown=0)
    project = Project(
        name="t",
        root=Path("."),
        runtime=rt,
        pages={},
        feature_files={},
    )
    matcher = MagicMock()
    matcher.capture_screen.return_value = np.zeros((4, 4, 3), dtype=np.uint8)
    matcher.detect_page.return_value = MatchResult(
        page_id="other", confidence=0.9, center=(1, 1)
    )
    runner = ActionRunner(
        project, matcher, MagicMock(), EngineLog(None), is_running=lambda: True
    )
    ok = runner.run_steps(
        [ActionStep("wait", 0.0), ActionStep("wait", 0.0)],
        np.zeros((4, 4, 3), dtype=np.uint8),
        {},
        page_id="p",
    )
    assert ok is True
