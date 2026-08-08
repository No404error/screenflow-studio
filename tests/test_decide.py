from types import SimpleNamespace

import numpy as np

from screenflow.decide import decide_tree, score_node
from screenflow.models import (
    DecideParams,
    RuntimeConfig,
    ScoreSpec,
    StateNode,
)


class FakeMatcher:
    def __init__(self, scores: dict[str, float]):
        self.scores = scores
        self.runtime = SimpleNamespace(match_threshold=0.72)
        # Membership drives scoped resolve; values are placeholders.
        self.detect = {k: object() for k in scores}
        self.click = {k: object() for k in scores}

    def match_detect(self, screen, key, *, roi=None):
        return self.scores.get(key, 0.0), (1, 1)

    def match_click(self, screen, key, *, roi=None):
        return self.scores.get(key, 0.0), (1, 1)


def test_decide_path_and_else():
    roots = [
        StateNode(
            id="a",
            name="A",
            priority=10,
            score=ScoreSpec(key="page/a", source="detect"),
        ),
        StateNode(id="e", name="Else", is_else=True, actions=[]),
    ]
    m = FakeMatcher({"page/a": 0.1})
    rt = RuntimeConfig(match_threshold=0.72)
    screen = np.zeros((10, 10, 3), dtype=np.uint8)
    res = decide_tree(roots, screen, m, "page", rt, DecideParams())
    assert res.leaf and res.leaf.is_else
    assert res.short_path() == "Else"


def test_decide_children():
    roots = [
        StateNode(
            id="parent",
            name="Parent",
            priority=10,
            score=ScoreSpec(key="page/p", source="detect"),
            children=[
                StateNode(
                    id="child",
                    name="Child",
                    priority=1,
                    score=ScoreSpec(key="page/c", source="detect"),
                    actions=[],
                )
            ],
        ),
    ]
    m = FakeMatcher({"page/p": 0.95, "page/c": 0.95})
    rt = RuntimeConfig()
    screen = np.zeros((8, 8, 3), dtype=np.uint8)
    res = decide_tree(roots, screen, m, "page", rt, None)
    assert res.leaf_id == "child"
    assert res.path == ["Parent", "Child"]


def test_constant_score():
    node = StateNode(
        id="c", name="C", score=ScoreSpec(kind="constant", constant=0.88)
    )
    m = FakeMatcher({})
    assert score_node(node, np.zeros((4, 4, 3), dtype=np.uint8), m, "p") == 0.88


def test_sole_unscored_leaf_wins():
    """Legacy DEFAULT: single sibling with no score acts like ELSE."""
    roots = [StateNode(id="DEFAULT", name="DEFAULT", actions=[])]
    m = FakeMatcher({})
    rt = RuntimeConfig(match_threshold=0.72)
    screen = np.zeros((10, 10, 3), dtype=np.uint8)
    res = decide_tree(roots, screen, m, "page", rt, DecideParams())
    assert res.leaf is not None
    assert res.leaf.id == "DEFAULT"
    assert res.detail["layers"][0].get("implicit_else") or res.detail["layers"][0].get(
        "used_else"
    )
