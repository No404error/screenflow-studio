import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from screenflow.decide import decide_tree, score_node
from screenflow.models import (
    DecideParams,
    RuntimeConfig,
    ScoreSpec,
    StateNode,
)
from screenflow.post import StickyPost, run_post_listen
from screenflow.project import Project, RuntimeConfig as RC
from unittest.mock import MagicMock


def test_invert_score():
    node = StateNode(
        id="i",
        score=ScoreSpec(kind="invert", key="k", source="detect"),
    )

    class M:
        runtime = SimpleNamespace(match_threshold=0.72)
        detect = {"p/k": object()}

        def match_detect(self, screen, key, *, roi=None):
            return 0.2, None

        def match_click(self, screen, key, *, roi=None):
            return 0.0, None

    assert abs(score_node(node, np.zeros((4, 4, 3), dtype=np.uint8), M(), "p") - 0.8) < 1e-6


def test_invert_missing_template_scores_zero():
    node = StateNode(
        id="i",
        score=ScoreSpec(kind="invert", key="missing", source="detect"),
    )

    class M:
        runtime = SimpleNamespace(match_threshold=0.72)
        detect = {}

        def match_detect(self, screen, key, *, roi=None):
            return 0.0, None

        def match_click(self, screen, key, *, roi=None):
            return 0.0, None

    assert score_node(node, np.zeros((4, 4, 3), dtype=np.uint8), M(), "p") == 0.0


def test_when_var_filters():
    roots = [
        StateNode(
            id="a",
            name="A",
            score=ScoreSpec(kind="constant", constant=0.99),
            when_var="ready=true",
            actions=[],
        ),
        StateNode(id="e", name="E", is_else=True, actions=[]),
    ]
    m = SimpleNamespace(
        runtime=SimpleNamespace(match_threshold=0.5),
        match_detect=lambda *a, **k: (0.0, None),
        match_click=lambda *a, **k: (0.0, None),
    )
    screen = np.zeros((4, 4, 3), dtype=np.uint8)
    rt = RuntimeConfig()
    res = decide_tree(roots, screen, m, "p", rt, None, vars={})
    assert res.leaf and res.leaf.is_else
    res2 = decide_tree(roots, screen, m, "p", rt, None, vars={"ready": True})
    assert res2.leaf_id == "a"


def test_frames_post_expires():
    listen = MagicMock()
    listen.mode = "frames"
    listen.frames = 2
    listen.tree = [
        StateNode(
            id="x",
            name="X",
            score=ScoreSpec(kind="constant", constant=0.99),
            actions=[],
        )
    ]
    listen.params = DecideParams()
    sticky = StickyPost(page_id="p", listen=listen, mode="frames", frames_left=1)
    project = Project(
        name="t",
        root=MagicMock(),
        runtime=RuntimeConfig(match_threshold=0.5),
        pages={},
        detect_files={},
        click_files={},
    )
    engine = SimpleNamespace(
        vars={},
        actions=SimpleNamespace(run_steps=MagicMock(return_value=True)),
        project=project,
    )
    out = run_post_listen(
        project,
        MagicMock(runtime=project.runtime, match_detect=MagicMock(return_value=(0, None)), match_click=MagicMock(return_value=(0, None))),
        engine,
        sticky,
        np.zeros((3, 3, 3), dtype=np.uint8),
        current_page_id="p",
    )
    assert out.ended
