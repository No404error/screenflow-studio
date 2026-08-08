"""Scoped detect/click keys; unscoped fallback only when unique."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from screenflow.decide import score_node
from screenflow.models import PageDef, Project, RuntimeConfig, ScoreSpec, StateNode
from screenflow.project import rebuild_resource_index


def _img(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), np.zeros((8, 8, 3), dtype=np.uint8))


def test_rebuild_skips_conflicting_unscoped_keys(tmp_path):
    _img(tmp_path / "pages" / "a" / "detect" / "main.png")
    _img(tmp_path / "pages" / "a" / "detect" / "same.png")
    _img(tmp_path / "pages" / "b" / "detect" / "main.png")
    _img(tmp_path / "pages" / "b" / "detect" / "same.png")
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(),
        pages={
            "a": PageDef(page_id="a", detect_relpath="pages/a/detect/main.png"),
            "b": PageDef(page_id="b", detect_relpath="pages/b/detect/main.png"),
        },
        detect_files={},
        click_files={},
    )
    rebuild_resource_index(project)
    assert "a/same" in project.detect_files
    assert "b/same" in project.detect_files
    assert "same" not in project.detect_files
    assert "a/main" in project.detect_files
    # main is also on both pages → no bare key
    assert "main" not in project.detect_files


def test_rebuild_keeps_unique_unscoped_key(tmp_path):
    _img(tmp_path / "pages" / "a" / "detect" / "main.png")
    _img(tmp_path / "pages" / "a" / "detect" / "only_a.png")
    _img(tmp_path / "pages" / "b" / "detect" / "main.png")
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(),
        pages={
            "a": PageDef(page_id="a", detect_relpath="pages/a/detect/main.png"),
            "b": PageDef(page_id="b", detect_relpath="pages/b/detect/main.png"),
        },
        detect_files={},
        click_files={},
    )
    rebuild_resource_index(project)
    assert project.detect_files.get("only_a") == "pages/a/detect/only_a.png"


def test_score_prefers_scoped_over_foreign_bare(tmp_path):
    from screenflow.matcher import ScreenMatcher

    _img(tmp_path / "pages" / "a" / "detect" / "main.png")
    _img(tmp_path / "pages" / "a" / "detect" / "icon.png")
    _img(tmp_path / "pages" / "b" / "detect" / "main.png")
    _img(tmp_path / "pages" / "b" / "detect" / "icon.png")
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(match_threshold=0.5),
        pages={
            "a": PageDef(page_id="a", detect_relpath="pages/a/detect/main.png"),
            "b": PageDef(page_id="b", detect_relpath="pages/b/detect/main.png"),
        },
        detect_files={},
        click_files={},
    )
    rebuild_resource_index(project)
    matcher = ScreenMatcher(project)
    # Conflicting bare name not loaded — scoring page a uses a/icon only.
    assert "icon" not in matcher.detect
    assert "a/icon" in matcher.detect
    node = StateNode(
        id="n",
        score=ScoreSpec(kind="template", key="icon", source="detect"),
    )
    conf = score_node(node, np.zeros((64, 64, 3), dtype=np.uint8), matcher, "a")
    # Match against zeros template on zeros screen should be high, and found.
    assert conf > 0.5
