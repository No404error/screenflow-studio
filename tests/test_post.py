from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np

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
from screenflow.post import StickyPost, run_post_listen
from screenflow.validate import validate_project_structure
from studio.i18n import I18n


def test_until_miss_ends_on_else():
    listen = PostListen(
        mode="until_miss",
        tree=[
            StateNode(
                id="hit",
                name="Hit",
                score=ScoreSpec(kind="constant", constant=0.1),
                actions=[],
            ),
            StateNode(id="e", name="E", is_else=True, actions=[]),
        ],
    )
    sticky = StickyPost(page_id="p", listen=listen, mode="until_miss")
    project = Project(
        name="t",
        root=MagicMock(),
        runtime=RuntimeConfig(match_threshold=0.9),
        pages={},
        detect_files={},
        click_files={},
    )
    matcher = MagicMock()
    matcher.runtime = project.runtime
    matcher.match_detect.return_value = (0.0, None)
    matcher.match_click.return_value = (0.0, None)
    engine = SimpleNamespace(
        vars={},
        actions=SimpleNamespace(run_steps=MagicMock(return_value=True)),
        project=project,
    )
    screen = np.zeros((4, 4, 3), dtype=np.uint8)
    out = run_post_listen(
        project, matcher, engine, sticky, screen, current_page_id="p"
    )
    assert out.ended
    assert out.used_else


def test_page_change_ends():
    listen = PostListen(
        mode="once",
        tree=[StateNode(id="e", name="E", is_else=True, actions=[])],
    )
    sticky = StickyPost(page_id="p", listen=listen, mode="once")
    project = Project(
        name="t",
        root=MagicMock(),
        runtime=RuntimeConfig(),
        pages={},
        detect_files={},
        click_files={},
    )
    out = run_post_listen(
        project,
        MagicMock(),
        SimpleNamespace(vars={}, actions=MagicMock()),
        sticky,
        np.zeros((2, 2, 3), dtype=np.uint8),
        current_page_id="other",
    )
    assert out.ended
    assert out.detail.get("reason") == "page_changed"


def test_unknown_skips_by_default():
    listen = PostListen(
        mode="until_miss",
        end_on_unknown=False,
        tree=[StateNode(id="e", is_else=True, actions=[])],
    )
    sticky = StickyPost(page_id="p", listen=listen, mode="until_miss")
    out = run_post_listen(
        Project(
            name="t",
            root=MagicMock(),
            runtime=RuntimeConfig(),
            pages={},
            detect_files={},
            click_files={},
        ),
        MagicMock(),
        SimpleNamespace(vars={}, actions=MagicMock()),
        sticky,
        np.zeros((2, 2, 3), dtype=np.uint8),
        current_page_id="UNKNOWN",
    )
    assert out.skipped
    assert not out.ended


def test_unknown_ends_when_configured():
    listen = PostListen(
        mode="until_miss",
        end_on_unknown=True,
        tree=[StateNode(id="e", is_else=True, actions=[])],
    )
    sticky = StickyPost(page_id="p", listen=listen, mode="until_miss")
    out = run_post_listen(
        Project(
            name="t",
            root=MagicMock(),
            runtime=RuntimeConfig(),
            pages={},
            detect_files={},
            click_files={},
        ),
        MagicMock(),
        SimpleNamespace(vars={}, actions=MagicMock()),
        sticky,
        np.zeros((2, 2, 3), dtype=np.uint8),
        current_page_id="UNKNOWN",
    )
    assert out.ended
    assert out.detail.get("reason") == "unknown_page"


def test_validate_post_empty_and_until_miss():
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        page = PageDef(
            page_id="p",
            detect_relpath="x.png",
            state_tree=[
                StateNode(
                    id="a",
                    is_else=True,
                    actions=[],
                    post=PostListen(mode="until_miss", tree=[]),
                )
            ],
        )
        proj = Project(
            name="t",
            root=root,
            runtime=RuntimeConfig(),
            pages={"p": page},
            detect_files={},
            click_files={},
        )
        issues = validate_project_structure(proj, I18n().t)
        assert any(i.level == "error" for i in issues)


@patch("screenflow.engine.time.sleep")
def test_engine_settle_before_first_post(mock_sleep, tmp_path):
    import cv2
    from screenflow.engine import FlowEngine
    from screenflow.project import rebuild_resource_index

    det = tmp_path / "pages" / "p" / "detect"
    det.mkdir(parents=True)
    cv2.imwrite(str(det / "main.png"), np.zeros((8, 8, 3), dtype=np.uint8))

    post = PostListen(
        mode="until_miss",
        settle=0.8,
        tree=[
            StateNode(
                id="hit",
                name="Hit",
                score=ScoreSpec(kind="constant", constant=0.99),
                actions=[ActionStep("wait", 0.0)],
            ),
            StateNode(id="e", name="E", is_else=True, actions=[]),
        ],
    )
    page = PageDef(
        page_id="p",
        name="Page",
        detect_relpath="pages/p/detect/main.png",
        state_tree=[
            StateNode(
                id="main",
                name="Main",
                is_else=True,
                actions=[],
                post=post,
            )
        ],
    )
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(match_threshold=0.5, action_delay=0, action_cooldown=0),
        pages={"p": page},
        detect_files={},
        click_files={},
    )
    rebuild_resource_index(project)
    eng = FlowEngine(project, log=lambda _m: None)
    eng.matcher.match_detect = MagicMock(return_value=(0.99, (1, 1)))
    eng.matcher.match_click = MagicMock(return_value=(0.99, (1, 1)))
    eng.matcher.capture_screen = MagicMock(
        return_value=np.zeros((8, 8, 3), dtype=np.uint8)
    )
    eng.matcher.detect_page = MagicMock(
        return_value=MatchResult(page_id="p", confidence=0.99, center=(1, 1))
    )
    eng.actions.run_steps = MagicMock(return_value=True)

    eng.dispatch(
        np.zeros((8, 8, 3), dtype=np.uint8),
        MatchResult(page_id="p", confidence=0.9, center=(1, 1)),
    )
    mock_sleep.assert_called_with(0.8)
    assert eng._sticky is not None  # until_miss continues after hit
