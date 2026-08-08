from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np

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
    normalize_post_mode,
)
from screenflow.post import StickyPost, run_post_listen
from screenflow.validate import validate_project_structure
from studio_api.i18n import I18n


def _proj(**kwargs):
    return Project(
        name="t",
        root=MagicMock(),
        runtime=kwargs.pop("runtime", RuntimeConfig(match_threshold=0.9)),
        pages={},
        feature_files={},
        **kwargs,
    )


def test_normalize_post_mode_legacy():
    assert normalize_post_mode("until_miss") == "until_case"
    assert normalize_post_mode("until_page") == "until_page"


def test_until_case_ends_on_else():
    listen = PostListen(
        mode="until_case",
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
    sticky = StickyPost(page_id="p", listen=listen, mode="until_case")
    project = _proj()
    matcher = MagicMock()
    matcher.runtime = project.runtime
    matcher.match_feature.return_value = (0.0, None)
    matcher.match_detect.return_value = (0.0, None)
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
    assert out.detail.get("reason") == "else_ends_until_case"


def test_until_miss_alias_ends_on_else():
    listen = PostListen(
        mode="until_miss",
        tree=[
            StateNode(
                id="hit",
                score=ScoreSpec(kind="constant", constant=0.1),
                actions=[],
            ),
            StateNode(id="e", is_else=True, actions=[]),
        ],
    )
    sticky = StickyPost(page_id="p", listen=listen, mode="until_miss")
    project = _proj()
    matcher = MagicMock()
    matcher.runtime = project.runtime
    matcher.match_feature.return_value = (0.0, None)
    matcher.match_detect.return_value = (0.0, None)
    engine = SimpleNamespace(
        vars={},
        actions=SimpleNamespace(run_steps=MagicMock(return_value=True)),
        project=project,
    )
    out = run_post_listen(
        project,
        matcher,
        engine,
        sticky,
        np.zeros((4, 4, 3), dtype=np.uint8),
        current_page_id="p",
    )
    assert out.ended and out.used_else


def test_until_page_else_skips_actions():
    """until_page + ELSE must not re-fire actions every poll."""
    listen = PostListen(
        mode="until_page",
        tree=[
            StateNode(
                id="hit",
                score=ScoreSpec(kind="constant", constant=0.1),
                actions=[],
            ),
            StateNode(id="e", is_else=True, actions=[ActionStep("wait", 0.0)]),
        ],
    )
    sticky = StickyPost(page_id="p", listen=listen, mode="until_page")
    project = _proj()
    matcher = MagicMock()
    matcher.runtime = project.runtime
    matcher.match_feature.return_value = (0.0, None)
    matcher.match_detect.return_value = (0.0, None)
    run_steps = MagicMock(return_value=True)
    engine = SimpleNamespace(vars={}, actions=SimpleNamespace(run_steps=run_steps), project=project)
    out = run_post_listen(
        project,
        matcher,
        engine,
        sticky,
        np.zeros((4, 4, 3), dtype=np.uint8),
        current_page_id="p",
    )
    assert not out.ended
    assert out.skipped
    assert out.used_else
    assert out.detail.get("reason") == "until_page_else_wait"
    run_steps.assert_not_called()


def test_until_page_empty_tree_waits_then_ends_on_page_change():
    listen = PostListen(mode="until_page", tree=[])
    sticky = StickyPost(page_id="p", listen=listen, mode="until_page")
    project = _proj(runtime=RuntimeConfig())
    engine = SimpleNamespace(vars={}, actions=MagicMock(), project=project)
    screen = np.zeros((2, 2, 3), dtype=np.uint8)
    out = run_post_listen(
        project, MagicMock(), engine, sticky, screen, current_page_id="p"
    )
    assert out.skipped and not out.ended
    assert out.detail.get("reason") == "until_page_wait"
    out2 = run_post_listen(
        project, MagicMock(), engine, sticky, screen, current_page_id="other"
    )
    assert out2.ended
    assert out2.detail.get("reason") == "page_changed"


def test_validate_until_page_allows_empty_tree():
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        page = make_page("p", detect="x.png",
            state_tree=[
                StateNode(
                    id="a",
                    is_else=True,
                    actions=[],
                    post=PostListen(mode="until_page", tree=[]),
                )
            ],
        )
        proj = Project(
            name="t",
            root=root,
            runtime=RuntimeConfig(),
            pages={"p": page},
            feature_files={},
        )
        issues = validate_project_structure(proj, I18n().t)
        assert not any(
            i.level == "error"
            and ("后续观察没有情况" in i.text or "no cases" in i.text)
            for i in issues
        )


def test_until_page_skips_when_no_match():
    listen = PostListen(
        mode="until_page",
        tree=[
            StateNode(
                id="hit",
                score=ScoreSpec(kind="constant", constant=0.1),
                actions=[],
            ),
        ],
    )
    sticky = StickyPost(page_id="p", listen=listen, mode="until_page")
    project = _proj()
    matcher = MagicMock()
    matcher.runtime = project.runtime
    out = run_post_listen(
        project,
        matcher,
        SimpleNamespace(vars={}, actions=MagicMock(), project=project),
        sticky,
        np.zeros((4, 4, 3), dtype=np.uint8),
        current_page_id="p",
    )
    assert out.skipped
    assert not out.ended
    assert out.detail.get("reason") == "no_match_skip"


def test_page_change_ends():
    listen = PostListen(
        mode="until_page",
        tree=[StateNode(id="e", name="E", is_else=True, actions=[])],
    )
    sticky = StickyPost(page_id="p", listen=listen, mode="until_page")
    out = run_post_listen(
        _proj(runtime=RuntimeConfig()),
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
        mode="until_case",
        end_on_unknown=False,
        tree=[StateNode(id="e", is_else=True, actions=[])],
    )
    sticky = StickyPost(page_id="p", listen=listen, mode="until_case")
    out = run_post_listen(
        _proj(runtime=RuntimeConfig()),
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
        mode="until_case",
        end_on_unknown=True,
        tree=[StateNode(id="e", is_else=True, actions=[])],
    )
    sticky = StickyPost(page_id="p", listen=listen, mode="until_case")
    out = run_post_listen(
        _proj(runtime=RuntimeConfig()),
        MagicMock(),
        SimpleNamespace(vars={}, actions=MagicMock()),
        sticky,
        np.zeros((2, 2, 3), dtype=np.uint8),
        current_page_id="UNKNOWN",
    )
    assert out.ended
    assert out.detail.get("reason") == "unknown_page"


def test_validate_post_empty_and_until_case():
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        page = make_page("p", detect="x.png",
            state_tree=[
                StateNode(
                    id="a",
                    is_else=True,
                    actions=[],
                    post=PostListen(mode="until_case", tree=[]),
                )
            ],
        )
        proj = Project(
            name="t",
            root=root,
            runtime=RuntimeConfig(),
            pages={"p": page},
            feature_files={},
        )
        issues = validate_project_structure(proj, I18n().t)
        assert any(i.level == "error" for i in issues)


def test_engine_settle_before_first_post(tmp_path):
    import cv2
    from screenflow.engine import FlowEngine
    from screenflow.project import rebuild_resource_index

    det = tmp_path / "pages" / "p" / "features"
    det.mkdir(parents=True)
    cv2.imwrite(str(det / "main.png"), np.zeros((8, 8, 3), dtype=np.uint8))

    post = PostListen(
        mode="until_case",
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
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(match_threshold=0.5, action_delay=0, action_cooldown=0),
        pages={"p": page},
        feature_files={},
    )
    rebuild_resource_index(project)
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
    settles: list[float] = []

    def _settle(seconds, is_running=None, **kwargs):
        settles.append(float(seconds))
        return True

    eng.input.interruptible_sleep = _settle  # type: ignore[method-assign]

    eng.dispatch(
        np.zeros((8, 8, 3), dtype=np.uint8),
        MatchResult(page_id="p", confidence=0.9, center=(1, 1)),
    )
    assert 0.8 in settles
    assert eng._sticky is not None


def test_until_case_else_runs_actions_and_ends():
    listen = PostListen(
        mode="until_case",
        tree=[
            StateNode(
                id="hit",
                score=ScoreSpec(kind="constant", constant=0.1),
                actions=[],
            ),
            StateNode(
                id="e",
                is_else=True,
                actions=[ActionStep("wait", 0.0)],
            ),
        ],
    )
    sticky = StickyPost(page_id="p", listen=listen, mode="until_case")
    project = _proj()
    matcher = MagicMock()
    matcher.runtime = project.runtime
    matcher.match_feature.return_value = (0.0, None)
    matcher.match_detect.return_value = (0.0, None)
    run_steps = MagicMock(return_value=True)
    engine = SimpleNamespace(
        vars={}, actions=SimpleNamespace(run_steps=run_steps), project=project
    )
    out = run_post_listen(
        project,
        matcher,
        engine,
        sticky,
        np.zeros((4, 4, 3), dtype=np.uint8),
        current_page_id="p",
    )
    assert out.ended
    assert out.used_else
    assert out.leaf is not None and out.leaf.is_else
    run_steps.assert_called_once()
    assert run_steps.call_args.args[0][0].op == "wait"


def test_frames_no_match_consumes_budget():
    listen = PostListen(
        mode="frames",
        frames=2,
        tree=[
            StateNode(
                id="hit",
                score=ScoreSpec(kind="constant", constant=0.99),
                actions=[],
            )
        ],
    )
    sticky = StickyPost(page_id="p", listen=listen, mode="frames", frames_left=2)
    project = _proj(runtime=RuntimeConfig(match_threshold=0.99))
    matcher = MagicMock()
    matcher.runtime = project.runtime
    # Force no leaf: constant 0.99 but threshold 0.99 with compete may still win...
    # Use below-threshold constant via high threshold and no ELSE.
    listen.tree[0].score = ScoreSpec(kind="constant", constant=0.1)
    engine = SimpleNamespace(
        vars={},
        actions=SimpleNamespace(run_steps=MagicMock(return_value=True)),
        project=project,
    )
    out1 = run_post_listen(
        project,
        matcher,
        engine,
        sticky,
        np.zeros((3, 3, 3), dtype=np.uint8),
        current_page_id="p",
    )
    assert not out1.ended
    assert out1.skipped
    assert sticky.frames_left == 1
    out2 = run_post_listen(
        project,
        matcher,
        engine,
        sticky,
        np.zeros((3, 3, 3), dtype=np.uint8),
        current_page_id="p",
    )
    assert out2.ended
    assert out2.detail.get("reason") == "frames_exhausted"
    assert sticky.frames_left == 0


def test_until_case_ends_on_nested_leaf_else():
    """Parent layer may not be ELSE; leaf is_else still ends until_case."""
    listen = PostListen(
        mode="until_case",
        tree=[
            StateNode(
                id="branch",
                score=ScoreSpec(kind="constant", constant=0.99),
                children=[
                    StateNode(
                        id="child_miss",
                        score=ScoreSpec(kind="constant", constant=0.1),
                        actions=[],
                    ),
                    StateNode(
                        id="child_else",
                        is_else=True,
                        actions=[ActionStep("wait", 0.0)],
                    ),
                ],
            ),
        ],
    )
    sticky = StickyPost(page_id="p", listen=listen, mode="until_case")
    project = _proj(runtime=RuntimeConfig(match_threshold=0.5))
    matcher = MagicMock()
    matcher.runtime = project.runtime
    matcher.match_feature.return_value = (0.0, None)
    matcher.match_detect.return_value = (0.0, None)
    run_steps = MagicMock(return_value=True)
    engine = SimpleNamespace(
        vars={}, actions=SimpleNamespace(run_steps=run_steps), project=project
    )
    out = run_post_listen(
        project,
        matcher,
        engine,
        sticky,
        np.zeros((4, 4, 3), dtype=np.uint8),
        current_page_id="p",
    )
    assert out.ended
    assert out.used_else
    assert out.leaf and out.leaf.id == "child_else"
    run_steps.assert_called_once()
