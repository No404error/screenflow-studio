from pathlib import Path

import numpy as np

from screenflow.decide import decide_page_state
from screenflow.project import load_project, merge_decide_params
from screenflow.validate import validate_for_start
from studio.i18n import I18n


MR = Path(__file__).resolve().parents[2] / "mr-auto-farm"


class _FakeMatcher:
    def __init__(self, scores: dict[str, float] | None = None) -> None:
        self.scores = scores or {}

    def match_detect(self, screen, key, *, roi=None):
        # key may be scoped page/name
        name = str(key).split("/")[-1]
        conf = self.scores.get(name, self.scores.get(str(key), 0.95))
        return conf, (1, 1)

    def match_click(self, screen, key, *, roi=None):
        return 0.95, (1, 1)


def test_mr_loads_and_structure():
    assert (MR / "project.json").is_file()
    p = load_project(MR)
    assert "main" in p.pages
    main_leaf = p.pages["main"].state_tree[0]
    assert main_leaf.post is not None
    assert main_leaf.post.mode == "until_case"
    assert any(n.is_else for n in main_leaf.post.tree)
    hero = p.pages["hero_select"].state_tree
    assert any(n.children for n in hero)
    assert p.pages["cultivate"].pair_with == "forge"
    assert p.pages["melt_reward"].detect_priority == 100
    ig = p.pages["in_game"].decide_params
    assert ig.on_close == "abstain"
    assert ig.margin == 0.05
    issues = validate_for_start(p, I18n().t)
    assert not [i for i in issues if i.level == "error"]


def test_mr_every_page_decides_a_leaf():
    p = load_project(MR)
    m = _FakeMatcher()
    screen = np.zeros((32, 32, 3), dtype=np.uint8)
    for page_id, page in p.pages.items():
        # Sole DEFAULT pages must be ELSE after load normalize
        if (
            len(page.state_tree) == 1
            and page.state_tree[0].id == "DEFAULT"
        ):
            assert page.state_tree[0].is_else, page_id
        res = decide_page_state(p, page, screen, m)
        if page_id == "in_game":
            # Equal fake scores + on_close=abstain → no leaf (skip frame)
            assert res.leaf is None, res.detail
            continue
        assert res.leaf is not None, f"{page_id} got no leaf: {res.detail}"


def test_mr_in_game_abstain_vs_clear_ready():
    p = load_project(MR)
    page = p.pages["in_game"]
    screen = np.zeros((32, 32, 3), dtype=np.uint8)
    merged = merge_decide_params(p.runtime, page.decide_params)
    assert merged.on_close == "abstain"

    close = decide_page_state(
        p,
        page,
        screen,
        _FakeMatcher({"f_ready": 0.80, "f_using": 0.78, "f_cooldown": 0.50}),
    )
    assert close.leaf is None

    clear = decide_page_state(
        p,
        page,
        screen,
        _FakeMatcher({"f_ready": 0.90, "f_using": 0.70, "f_cooldown": 0.50}),
    )
    assert clear.leaf is not None
    assert clear.leaf.id == "f_ready"
