"""P2: sticky commit flag, loop auto-pause, empty-macro / mode edges."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import cv2
import numpy as np

from screenflow.engine import FlowEngine
from screenflow.matcher import ScreenMatcher
from tests.page_helpers import make_page
from screenflow.models import (
    ActionStep,
    EngineStatus,
    MatchResult,
    PageDef,
    PostListen,
    Project,
    RuntimeConfig,
    StateNode,
)
from screenflow.project import rebuild_resource_index


def _write(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), np.zeros((16, 16, 3), dtype=np.uint8))


def test_detect_page_commit_sticky_false(tmp_path: Path):
    rel = "pages/a/features/main.png"
    _write(tmp_path / rel)
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(
            match_threshold=0.5, ref_width=16, ref_height=16
        ),
        pages={
            "a": make_page("a", detect=rel, state_tree=[]),
        },
        feature_files={},
    )
    rebuild_resource_index(project)
    m = ScreenMatcher(project)
    screen = cv2.imread(str(tmp_path / rel))
    assert m._sticky_page_id is None
    r = m.detect_page(screen, force_full=True, commit_sticky=False)
    assert r.page_id == "a"
    assert m._sticky_page_id is None
    r2 = m.detect_page(screen, force_full=True, commit_sticky=True)
    assert r2.page_id == "a"
    assert m._sticky_page_id == "a"


def test_loop_exception_auto_pauses(tmp_path: Path):
    rel = "pages/a/features/main.png"
    _write(tmp_path / rel)
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(
            match_threshold=0.5,
            poll_interval=0.05,
            ref_width=16,
            ref_height=16,
        ),
        pages={
            "a": make_page("a", detect=rel,
                state_tree=[StateNode(id="e", is_else=True, actions=[])],
            ),
        },
        feature_files={},
    )
    rebuild_resource_index(project)
    statuses: list[dict] = []
    eng = FlowEngine(project, log=lambda _m: None, status=statuses.append)
    eng.matcher.capture_screen = MagicMock(side_effect=RuntimeError("boom"))
    eng.start()
    deadline = time.time() + 2.0
    while time.time() < deadline:
        if eng.status == EngineStatus.PAUSED:
            break
        time.sleep(0.05)
    assert eng.status == EngineStatus.PAUSED
    eng.stop()
    assert any(s.get("mode") == "paused" and s.get("error") for s in statuses)


def test_dispatch_broken_macro_does_not_arm_post(tmp_path: Path):
    rel = "pages/a/features/main.png"
    _write(tmp_path / rel)
    post = PostListen(
        mode="once",
        tree=[StateNode(id="pe", is_else=True, actions=[])],
    )
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(
            match_threshold=0.5, ref_width=16, ref_height=16
        ),
        pages={
            "a": make_page("a", detect=rel,
                state_tree=[
                    StateNode(
                        id="leaf",
                        is_else=True,
                        actions=[ActionStep("macro", "gone")],
                        post=post,
                    )
                ],
            ),
        },
        feature_files={},
        macros={},
    )
    rebuild_resource_index(project)
    eng = FlowEngine(project, log=lambda _m: None)
    eng.matcher.capture_screen = MagicMock(
        return_value=np.zeros((16, 16, 3), dtype=np.uint8)
    )
    eng.dispatch(
        np.zeros((16, 16, 3), dtype=np.uint8),
        MatchResult(page_id="a", confidence=0.99, center=(1, 1)),
    )
    assert eng._sticky is None
