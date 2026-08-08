"""P1: sticky page detect + early stop."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from screenflow.matcher import ScreenMatcher
from screenflow.models import PageDef, Project, RuntimeConfig
from screenflow.project import list_page_pairs, rebuild_resource_index, set_page_pair


def _write_pattern(path: Path, seed: int, size: int = 48) -> None:
    """Deterministic unique pattern so templates do not cross-match."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.RandomState(seed)
    img = rng.randint(0, 255, (size, size, 3), dtype=np.uint8)
    # Strong unique marker block
    img[0:12, 0:12] = ((seed * 37) % 255, (seed * 91) % 255, (seed * 13) % 255)
    cv2.imwrite(str(path), img)


def _project(root: Path, page_ids: list[str]) -> Project:
    pages: dict[str, PageDef] = {}
    for i, pid in enumerate(page_ids):
        rel = f"pages/{pid}/features/main.png"
        _write_pattern(root / rel, seed=100 + i)
        pages[pid] = PageDef(
            page_id=pid,
            name=pid,
            detect_relpath=rel,
            state_tree=[],
        )
    p = Project(
        name="t",
        root=root,
        runtime=RuntimeConfig(
            match_threshold=0.85,
            page_detect_near=0.08,
            page_pair_margin=0.05,
            ref_width=48,
            ref_height=48,
        ),
        pages=pages,
        feature_files={},
    )
    rebuild_resource_index(p)
    return p


def _screen(root: Path, pid: str) -> np.ndarray:
    img = cv2.imread(str(root / f"pages/{pid}/features/main.png"))
    assert img is not None
    return img


def test_sticky_second_frame_skips_full_scan(tmp_path: Path):
    proj = _project(tmp_path, ["a", "b", "c"])
    m = ScreenMatcher(proj)
    screen_a = _screen(tmp_path, "a")

    r1 = m.detect_page(screen_a)
    assert r1.page_id == "a"

    calls = {"n": 0}
    real_match = m.match_template

    def counting_match(screen, template, **kwargs):
        calls["n"] += 1
        return real_match(screen, template, **kwargs)

    with patch.object(m, "match_template", side_effect=counting_match):
        r2 = m.detect_page(screen_a)
    assert r2.page_id == "a"
    assert calls["n"] == 1


def test_sticky_miss_falls_back_to_full(tmp_path: Path):
    proj = _project(tmp_path, ["a", "b"])
    m = ScreenMatcher(proj)
    assert m.detect_page(_screen(tmp_path, "a")).page_id == "a"
    assert m.detect_page(_screen(tmp_path, "b")).page_id == "b"
    assert m._sticky_page_id == "b"


def test_sticky_pair_compares_sibling(tmp_path: Path):
    proj = _project(tmp_path, ["cultivate", "forge", "main"])
    set_page_pair(proj, "cultivate", "forge")
    proj.page_pairs = list_page_pairs(proj)

    m = ScreenMatcher(proj)
    screen_c = _screen(tmp_path, "cultivate")
    assert m.detect_page(screen_c).page_id == "cultivate"

    calls: list[str] = []
    real_match = m.match_template

    def counting_match(screen, template, **kwargs):
        for pid, tpl in m.page_templates.items():
            if tpl is template:
                calls.append(pid)
                break
        return real_match(screen, template, **kwargs)

    with patch.object(m, "match_template", side_effect=counting_match):
        r = m.detect_page(screen_c)
    assert r.page_id == "cultivate"
    assert set(calls) == {"cultivate", "forge"}


def test_full_scan_matches_all_page_templates(tmp_path: Path):
    ids = [f"p{i}" for i in range(5)]
    proj = _project(tmp_path, ids)
    m = ScreenMatcher(proj)
    m.clear_page_sticky()
    screen = _screen(tmp_path, "p0")

    calls = {"n": 0}
    real_match = m.match_template

    def counting_match(screen, template, **kwargs):
        calls["n"] += 1
        return real_match(screen, template, **kwargs)

    with patch.object(m, "match_template", side_effect=counting_match):
        r = m.detect_page(screen, force_full=True)

    assert r.page_id == "p0"
    assert calls["n"] == len(ids)


def test_prefer_unknown_falls_through_to_full(tmp_path: Path):
    proj = _project(tmp_path, ["a", "b", "c"])
    set_page_pair(proj, "a", "b")
    proj.page_pairs = list_page_pairs(proj)
    m = ScreenMatcher(proj)

    # Force prefer path to produce UNKNOWN via compete_page_pair
    with patch.object(
        m,
        "match_template",
        side_effect=[(0.99, (1, 1)), (0.98, (1, 1))],
    ):
        with patch(
            "screenflow.matcher.compete_page_pair", return_value=None
        ):
            hit = m._detect_prefer(_screen(tmp_path, "a"), "a")
    assert hit is None


def test_prefer_weak_hit_falls_through(tmp_path: Path):
    proj = _project(tmp_path, ["a", "b"])
    m = ScreenMatcher(proj)
    # Just above threshold but below threshold+near → must fall through
    thr = proj.runtime.match_threshold
    near = proj.runtime.page_detect_near
    weak = thr + near * 0.5
    with patch.object(m, "match_template", return_value=(weak, (1, 1))):
        assert m._detect_prefer(_screen(tmp_path, "a"), "a") is None


def test_clear_page_sticky(tmp_path: Path):
    proj = _project(tmp_path, ["a", "b"])
    m = ScreenMatcher(proj)
    m.detect_page(_screen(tmp_path, "a"))
    assert m._sticky_page_id == "a"
    m.clear_page_sticky()
    assert m._sticky_page_id is None


def test_prefer_kwarg_overrides_sticky(tmp_path: Path):
    proj = _project(tmp_path, ["a", "b", "c"])
    m = ScreenMatcher(proj)
    m.detect_page(_screen(tmp_path, "a"))
    assert m._sticky_page_id == "a"

    calls: list[str] = []
    real_match = m.match_template

    def counting_match(screen, template, **kwargs):
        for pid, tpl in m.page_templates.items():
            if tpl is template:
                calls.append(pid)
                break
        return real_match(screen, template, **kwargs)

    with patch.object(m, "match_template", side_effect=counting_match):
        r = m.detect_page(_screen(tmp_path, "b"), prefer="b")
    assert r.page_id == "b"
    assert calls == ["b"]
