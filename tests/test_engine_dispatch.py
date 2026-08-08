"""FlowEngine.dispatch: main leaf → arm post → sticky once / until_case / page change."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from screenflow.engine import FlowEngine
from tests.page_helpers import make_page
from screenflow.models import (
    ActionStep,
    MatchResult,
    PageDef,
    PostListen,
    Project,
    RuntimeConfig,
    ScoreSpec,
    StateNode,
)
from screenflow.project import rebuild_resource_index


@pytest.fixture()
def project_root(tmp_path: Path):
    det = tmp_path / "pages" / "p" / "features"
    det.mkdir(parents=True)
    # minimal valid PNG via numpy+cv2 if available, else raw bytes may fail load —
    # put a real tiny PNG
    import cv2

    cv2.imwrite(str(det / "main.png"), np.zeros((8, 8, 3), dtype=np.uint8))
    return tmp_path


def _project(root: Path, pages: dict[str, PageDef]) -> Project:
    p = Project(
        name="t",
        root=root,
        runtime=RuntimeConfig(match_threshold=0.5, action_delay=0, action_cooldown=0),
        pages=pages,
        feature_files={},
    )
    rebuild_resource_index(p)
    return p


def _engine(project: Project) -> FlowEngine:
    eng = FlowEngine(project, log=lambda _m: None)
    eng.matcher.match_feature = MagicMock(return_value=(0.99, (1, 1)))
    eng.matcher.match_detect = eng.matcher.match_feature
    eng.matcher.capture_screen = MagicMock(
        return_value=np.zeros((8, 8, 3), dtype=np.uint8)
    )
    eng.matcher.detect_page = MagicMock(
        return_value=MatchResult(page_id="p", confidence=0.99, center=(1, 1))
    )
    eng.actions.run_steps = MagicMock(return_value=True)
    return eng


def test_dispatch_arms_until_case_then_else_ends(project_root):
    post = PostListen(
        mode="until_case",
        tree=[
            StateNode(
                id="popup",
                name="Popup",
                score=ScoreSpec(kind="constant", constant=0.99),
                actions=[ActionStep("wait", 0.01)],
            ),
            StateNode(id="e", name="Else", is_else=True, actions=[]),
        ],
    )
    page = make_page("p", name="Page",
        detect="pages/p/features/main.png",
        state_tree=[
            StateNode(
                id="main",
                name="Main",
                is_else=True,
                actions=[ActionStep("wait", 0.01)],
                post=post,
            )
        ],
    )
    eng = _engine(_project(project_root, {"p": page}))
    screen = np.zeros((8, 8, 3), dtype=np.uint8)
    pr = MatchResult(page_id="p", confidence=0.9, center=(1, 1))

    path = eng.dispatch(screen, pr)
    assert path and "Main" in path
    assert eng._sticky is not None
    assert eng._sticky.mode == "until_case"

    path2 = eng.dispatch(screen, pr)
    assert eng._sticky is not None
    assert path2 and "post" in path2

    eng._sticky.listen.tree[0].score = ScoreSpec(kind="constant", constant=0.0)
    eng.project.runtime.match_threshold = 0.5
    path3 = eng.dispatch(screen, pr)
    assert eng._sticky is None
    assert path3 is not None


def test_dispatch_once_clears_sticky_same_frame(project_root):
    post = PostListen(
        mode="once",
        tree=[
            StateNode(
                id="p1",
                name="P1",
                is_else=True,
                actions=[ActionStep("wait", 0.01)],
            )
        ],
    )
    page = make_page("p", name="Page",
        detect="pages/p/features/main.png",
        state_tree=[
            StateNode(
                id="main",
                name="Main",
                is_else=True,
                actions=[],
                post=post)
        ],
    )
    eng = _engine(_project(project_root, {"p": page}))
    path = eng.dispatch(
        np.zeros((8, 8, 3), dtype=np.uint8),
        MatchResult(page_id="p", confidence=0.9, center=(1, 1)),
    )
    assert "Main" in (path or "")
    assert eng._sticky is None


def test_dispatch_page_change_ends_sticky(project_root):
    post = PostListen(
        mode="until_page",
        tree=[
            StateNode(
                id="hit",
                name="Hit",
                score=ScoreSpec(kind="constant", constant=0.99),
                actions=[],
            ),
            StateNode(id="e", name="E", is_else=True, actions=[]),
        ],
    )
    page = make_page("p", name="Page",
        detect="pages/p/features/main.png",
        state_tree=[
            StateNode(
                id="main",
                name="Main",
                is_else=True,
                actions=[],
                post=post)
        ],
    )
    eng = _engine(_project(project_root, {"p": page}))
    # Sticky post always force_full — one detect_page per sticky dispatch.
    results = [
        MatchResult(page_id="p", confidence=0.9, center=(1, 1)),
        MatchResult(page_id="other", confidence=0.9, center=(1, 1)),
    ]
    eng.matcher.detect_page = MagicMock(side_effect=results)
    eng.dispatch(
        np.zeros((4, 4, 3), dtype=np.uint8),
        MatchResult(page_id="p", confidence=0.9, center=(1, 1)),
    )
    assert eng._sticky is not None
    eng.dispatch(
        np.zeros((4, 4, 3), dtype=np.uint8),
        MatchResult(page_id="p", confidence=0.9, center=(1, 1)),
    )
    assert eng._sticky is None


def test_post_uses_full_detect(project_root):
    """Sticky post detect scans all page templates (force_full)."""
    import cv2

    for pid, seed in (("p", 1), ("q", 2), ("r", 3)):
        d = project_root / "pages" / pid / "features"
        d.mkdir(parents=True, exist_ok=True)
        rng = np.random.RandomState(seed)
        cv2.imwrite(
            str(d / "main.png"), rng.randint(0, 255, (32, 32, 3), dtype=np.uint8)
        )

    pages = {
        "p": make_page("p", name="P",
            detect="pages/p/features/main.png",
            state_tree=[
                StateNode(
                    id="main",
                    name="Main",
                    is_else=True,
                    actions=[],
                    post=PostListen(
                        mode="once",
                        settle=0.0,
                        tree=[
                            StateNode(id="e", name="E", is_else=True, actions=[]),
                        ],
                    ),
                )
            ],
        ),
        "q": make_page("q", name="Q",
            detect="pages/q/features/main.png",
            state_tree=[]),
        "r": make_page("r", name="R",
            detect="pages/r/features/main.png",
            state_tree=[]),
    }
    project = Project(
        name="t",
        root=project_root,
        runtime=RuntimeConfig(
            match_threshold=0.8,
            action_delay=0,
            action_cooldown=0,
            ref_width=32,
            ref_height=32,
        ),
        pages=pages,
        feature_files={},
    )
    rebuild_resource_index(project)
    eng = FlowEngine(project, log=lambda _m: None)
    eng.actions.run_steps = MagicMock(return_value=True)
    screen = cv2.imread(str(project_root / "pages/p/features/main.png"))
    assert screen is not None
    eng.matcher.capture_screen = MagicMock(return_value=screen)

    calls = {"n": 0}
    real_match = eng.matcher.match_template

    def counting_match(s, template, **kwargs):
        calls["n"] += 1
        return real_match(s, template, **kwargs)

    with patch.object(eng.matcher, "match_template", side_effect=counting_match):
        eng.dispatch(
            screen, MatchResult(page_id="p", confidence=0.99, center=(1, 1))
        )

    assert calls["n"] == 3, f"expected full post detect, got {calls['n']} matches"
    assert eng._sticky is None  # once mode ends in same frame


def test_dispatch_does_not_arm_post_when_actions_fail(project_root):
    post = PostListen(
        mode="until_page",
        tree=[],
    )
    page = make_page("p", name="Page",
        detect="pages/p/features/main.png",
        state_tree=[
            StateNode(
                id="main",
                name="Main",
                is_else=True,
                actions=[ActionStep("wait", 0.01)],
                post=post,
            )
        ],
    )
    eng = _engine(_project(project_root, {"p": page}))
    eng.actions.run_steps = MagicMock(return_value=False)
    eng.dispatch(
        np.zeros((8, 8, 3), dtype=np.uint8),
        MatchResult(page_id="p", confidence=0.9, center=(1, 1)),
    )
    assert eng._sticky is None


def test_status_payload_marks_sticky_followup(project_root):
    payloads: list[dict] = []
    page = make_page("p", name="Page",
        detect="pages/p/features/main.png",
        state_tree=[
            StateNode(
                id="main",
                name="Main",
                is_else=True,
                actions=[],
                post=PostListen(mode="until_page", tree=[]),
            )
        ],
    )
    project = _project(project_root, {"p": page})
    eng = FlowEngine(project, log=lambda _m: None, status=payloads.append)
    eng.actions.run_steps = MagicMock(return_value=True)
    eng.matcher.detect_page = MagicMock(
        return_value=MatchResult(page_id="p", confidence=0.9, center=(1, 1))
    )
    eng.matcher.capture_screen = MagicMock(
        return_value=np.zeros((8, 8, 3), dtype=np.uint8)
    )
    eng.dispatch(
        np.zeros((8, 8, 3), dtype=np.uint8),
        MatchResult(page_id="p", confidence=0.9, center=(1, 1)),
    )
    eng._emit_status("running", page_id="p", state="Main › post")
    assert payloads
    last = payloads[-1]
    assert last.get("sticky") is True
    assert last.get("post_mode") == "until_page"


def test_dispatch_arms_until_page_empty_tree(project_root):
    page = make_page("p", name="Page",
        detect="pages/p/features/main.png",
        state_tree=[
            StateNode(
                id="main",
                name="Main",
                is_else=True,
                actions=[],
                post=PostListen(mode="until_page", tree=[]),
            )
        ],
    )
    eng = _engine(_project(project_root, {"p": page}))
    eng.dispatch(
        np.zeros((8, 8, 3), dtype=np.uint8),
        MatchResult(page_id="p", confidence=0.9, center=(1, 1)),
    )
    assert eng._sticky is not None
    assert eng._sticky.mode == "until_page"
    assert eng._sticky.listen.tree == []


def test_default_post_fallback(project_root):
    page = make_page("p", name="Page",
        detect="pages/p/features/main.png",
        state_tree=[
            StateNode(id="main", name="Main", is_else=True, actions=[]),
        ],
        default_post=PostListen(
            mode="until_case",
            tree=[
                StateNode(
                    id="hit",
                    name="Hit",
                    score=ScoreSpec(kind="constant", constant=0.99),
                    actions=[],
                ),
                StateNode(id="e", name="E", is_else=True, actions=[]),
            ],
        ),
    )
    eng = _engine(_project(project_root, {"p": page}))
    eng.dispatch(
        np.zeros((4, 4, 3), dtype=np.uint8),
        MatchResult(page_id="p", confidence=0.9, center=(1, 1)),
    )
    assert eng._sticky is not None
    assert eng._sticky.mode == "until_case"
