"""P0: adaptive poll sleep + verbose timing line."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from screenflow.engine import FlowEngine
from screenflow.models import (
    EngineStatus,
    MatchResult,
    PageDef,
    Project,
    RuntimeConfig,
)


@pytest.fixture()
def project_root(tmp_path: Path):
    import cv2

    det = tmp_path / "pages" / "p" / "detect"
    det.mkdir(parents=True)
    cv2.imwrite(str(det / "main.png"), np.zeros((8, 8, 3), dtype=np.uint8))
    return tmp_path


def _project(root: Path, *, poll: float, verbose: bool = False) -> Project:
    from screenflow.project import rebuild_resource_index

    pages = {
        "p": PageDef(
            page_id="p",
            name="Page",
            detect_relpath="pages/p/detect/main.png",
            state_tree=[],
        )
    }
    p = Project(
        name="t",
        root=root,
        runtime=RuntimeConfig(
            match_threshold=0.5,
            poll_interval=poll,
            action_delay=0,
            action_cooldown=0,
            verbose_log=verbose,
        ),
        pages=pages,
        detect_files={},
        click_files={},
    )
    rebuild_resource_index(p)
    return p


def _run_one_frame(eng: FlowEngine, sleeps: list[float]) -> None:
    """Start engine, let one loop iteration finish, then stop."""
    frame = {"n": 0}
    real_sleep = time.sleep

    def capture():
        frame["n"] += 1
        if frame["n"] >= 1:
            # Stop after this frame's work so the next loop iteration exits.
            eng.status = EngineStatus.STOPPED
        return np.zeros((8, 8, 3), dtype=np.uint8)

    eng.matcher.capture_screen = MagicMock(side_effect=capture)
    eng.matcher.detect_page = MagicMock(
        return_value=MatchResult(page_id="p", confidence=0.99, center=(1, 1))
    )
    eng.dispatch = MagicMock(return_value=None)  # type: ignore[method-assign]

    def record_sleep(s: float) -> None:
        sleeps.append(s)

    with patch("screenflow.engine.time.sleep", side_effect=record_sleep):
        eng.start()
        # Wait until loop notices STOPPED (no adaptive sleep needed if work was slow).
        deadline = time.time() + 2.0
        while eng._thread is not None and eng._thread.is_alive() and time.time() < deadline:
            real_sleep(0.01)
        if eng._thread is not None and eng._thread.is_alive():
            eng.stop()
            eng._thread.join(timeout=1.0)


def test_no_extra_sleep_when_work_exceeds_poll(project_root):
    sleeps: list[float] = []
    eng = FlowEngine(_project(project_root, poll=0.05), log=lambda _m: None)

    real_sleep = time.sleep

    def slow_capture():
        real_sleep(0.12)  # > poll_interval
        eng.status = EngineStatus.STOPPED
        return np.zeros((8, 8, 3), dtype=np.uint8)

    eng.matcher.capture_screen = MagicMock(side_effect=slow_capture)
    eng.matcher.detect_page = MagicMock(
        return_value=MatchResult(page_id="p", confidence=0.99, center=(1, 1))
    )
    eng.dispatch = MagicMock(return_value=None)  # type: ignore[method-assign]

    with patch("screenflow.engine.time.sleep", side_effect=lambda s: sleeps.append(s)):
        eng.start()
        deadline = time.time() + 2.0
        while eng._thread is not None and eng._thread.is_alive() and time.time() < deadline:
            real_sleep(0.01)

    assert sleeps == [], f"expected no adaptive sleep, got {sleeps}"


def test_sleep_tops_up_short_frames(project_root):
    sleeps: list[float] = []
    poll = 0.2
    eng = FlowEngine(_project(project_root, poll=poll), log=lambda _m: None)
    _run_one_frame(eng, sleeps)
    assert len(sleeps) == 1
    assert 0.05 <= sleeps[0] <= poll + 0.05


def test_verbose_timing_line(project_root):
    lines: list[str] = []
    eng = FlowEngine(
        _project(project_root, poll=0.05, verbose=True),
        log=lines.append,
    )
    sleeps: list[float] = []
    _run_one_frame(eng, sleeps)
    timing = [ln for ln in lines if "timing" in ln and "capture=" in ln]
    assert timing, f"missing timing line in {lines!r}"
    assert "match=" in timing[0]
    assert "decide=" in timing[0]
    assert "sleep=" in timing[0]
