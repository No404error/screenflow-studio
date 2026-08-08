"""Asset-level ROI: persist, page/state/click match, override semantics."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from screenflow.assets import set_asset_roi, upload_page_asset
from screenflow.decide import score_node
from screenflow.matcher import ScreenMatcher
from screenflow.models import PageDef, Project, RuntimeConfig, ScoreSpec, StateNode
from screenflow.project import page_to_dict, rebuild_resource_index, _page_from_json
from screenflow.roi import (
    effective_roi,
    expand_roi_for_search,
    normalize_roi,
    roi_from_pixel_rect,
)


def _write_pattern(path: Path, seed: int, size: int = 64) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.RandomState(seed)
    img = rng.randint(0, 255, (size, size, 3), dtype=np.uint8)
    img[8:24, 8:24] = (seed * 17 % 255, seed * 31 % 255, seed * 7 % 255)
    cv2.imwrite(str(path), img)


def test_normalize_and_pixel_roi():
    assert normalize_roi([0.1, 0.5, 0.2, 0.8]) == (0.1, 0.5, 0.2, 0.8)
    assert normalize_roi([0.5, 0.1, 0.2, 0.8]) is None
    r = roi_from_pixel_rect(10, 20, 30, 40, width=100, height=200)
    assert r is not None
    assert abs(r[0] - 0.1) < 1e-9  # y0
    assert abs(r[2] - 0.1) < 1e-9  # x0


def test_effective_roi_prefers_override():
    assert effective_roi([0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]) == (
        0.1,
        0.2,
        0.3,
        0.4,
    )
    assert effective_roi(None, [0.5, 0.6, 0.7, 0.8]) == (0.5, 0.6, 0.7, 0.8)
    assert effective_roi(None, None) is None


def test_expand_roi_for_search_pads():
    y0, y1, x0, x1 = expand_roi_for_search([0.4, 0.6, 0.4, 0.6], pad_frac=0.25)
    assert y0 < 0.4 < 0.6 < y1
    assert x0 < 0.4 < 0.6 < x1
    # Clamped to screen.
    assert expand_roi_for_search([0.0, 0.1, 0.0, 0.1])[0] == 0.0


def test_page_roi_roundtrip_json():
    page = PageDef(
        page_id="p",
        detect_relpath="pages/p/features/main.png",
        detect_roi=[0.1, 0.4, 0.2, 0.5],
        feature_rois={
            "main": [0.1, 0.4, 0.2, 0.5],
            "icon": [0.7, 0.9, 0.7, 0.9],
            "btn": [0.8, 0.95, 0.1, 0.3],
        },
    )
    raw = page_to_dict(page)
    assert raw["detect_roi"][0] == 0.1
    assert "icon" in raw["feature_rois"]
    assert "btn" in raw["feature_rois"]
    back = _page_from_json(raw)
    assert back.detect_roi == [0.1, 0.4, 0.2, 0.5]
    assert back.feature_rois["icon"] == [0.7, 0.9, 0.7, 0.9]
    assert back.feature_rois["btn"] == [0.8, 0.95, 0.1, 0.3]


def test_legacy_page_json_without_roi():
    back = _page_from_json(
        {
            "id": "p",
            "detect": "pages/p/features/main.png",
            "features": {},
            "state_tree": [],
        }
    )
    assert back.detect_roi is None
    assert back.feature_rois == {}


def _textured_patch(seed: int, size: int = 20) -> np.ndarray:
    rng = np.random.RandomState(seed)
    img = rng.randint(0, 255, (size, size, 3), dtype=np.uint8)
    img[0:6, 0:6] = (40, 200, 90)
    return img


def test_page_detect_uses_roi(tmp_path: Path):
    """Template only in bottom-right; ROI match finds it, wrong ROI misses."""
    full = np.zeros((100, 100, 3), dtype=np.uint8)
    patch = _textured_patch(9, 20)
    full[70:90, 70:90] = patch
    feat = tmp_path / "pages" / "a" / "features"
    feat.mkdir(parents=True)
    cv2.imwrite(str(feat / "main.png"), patch)

    page = PageDef(
        page_id="a",
        detect_relpath="pages/a/features/main.png",
        detect_roi=[0.7, 0.9, 0.7, 0.9],
        feature_rois={"main": [0.7, 0.9, 0.7, 0.9]},
        state_tree=[],
    )
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(
            match_threshold=0.8, ref_width=100, ref_height=100
        ),
        pages={"a": page},
        feature_files={},
    )
    rebuild_resource_index(project)
    m = ScreenMatcher(project)
    assert m.page_rois["a"] == (0.7, 0.9, 0.7, 0.9)
    hit = m.detect_page(full, force_full=True)
    assert hit.page_id == "a"

    # Restrict ROI to empty black corner — should not match strongly.
    m.page_rois["a"] = (0.0, 0.2, 0.0, 0.2)
    miss = m.detect_page(full, force_full=True, commit_sticky=False)
    assert miss.page_id == "UNKNOWN" or miss.confidence < 0.8


def test_tight_roi_still_matches_with_jitter(tmp_path: Path):
    """Crop==ROI used to lock alignment; padded search recovers ~1.0 scores."""
    full = np.zeros((100, 100, 3), dtype=np.uint8)
    patch = _textured_patch(9, 20)
    # Template was cropped at 70:90; live UI shifted by 3px.
    full[73:93, 73:93] = patch
    feat = tmp_path / "pages" / "a" / "features"
    feat.mkdir(parents=True)
    cv2.imwrite(str(feat / "main.png"), patch)

    page = PageDef(
        page_id="a",
        detect_relpath="pages/a/features/main.png",
        detect_roi=[0.7, 0.9, 0.7, 0.9],
        feature_rois={"main": [0.7, 0.9, 0.7, 0.9]},
        state_tree=[],
    )
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(
            match_threshold=0.8, ref_width=100, ref_height=100
        ),
        pages={"a": page},
        feature_files={},
    )
    rebuild_resource_index(project)
    m = ScreenMatcher(project)
    hit = m.detect_page(full, force_full=True)
    assert hit.page_id == "a"
    assert hit.confidence >= 0.9


def test_state_score_uses_asset_roi_and_override(tmp_path: Path):
    full = np.zeros((80, 80, 3), dtype=np.uint8)
    patch = _textured_patch(11, 16)
    full[50:66, 50:66] = patch
    feat = tmp_path / "pages" / "p" / "features"
    feat.mkdir(parents=True)
    cv2.imwrite(str(feat / "icon.png"), patch)
    _write_pattern(tmp_path / "pages" / "p" / "features" / "main.png", seed=1)

    page = PageDef(
        page_id="p",
        detect_relpath="pages/p/features/main.png",
        feature_rois={"icon": [0.6, 0.85, 0.6, 0.85]},
        feature_map={
            "icon": "pages/p/features/icon.png",
            "main": "pages/p/features/main.png",
        },
        state_tree=[],
    )
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(
            match_threshold=0.7, ref_width=80, ref_height=80
        ),
        pages={"p": page},
        feature_files={},
    )
    rebuild_resource_index(project)
    m = ScreenMatcher(project)
    node = StateNode(
        id="n",
        score=ScoreSpec(kind="template", key="icon"),
    )
    conf = score_node(node, full, m, "p")
    assert conf > 0.7

    # Override to a region without the patch.
    node.score = ScoreSpec(
        kind="template",
        key="icon",
        roi=[0.0, 0.25, 0.0, 0.25],
    )
    conf2 = score_node(node, full, m, "p")
    assert conf2 < 0.5


def test_upload_stores_roi(tmp_path: Path):
    src = tmp_path / "cap.png"
    _write_pattern(src, seed=3, size=40)
    page = PageDef(
        page_id="p",
        detect_relpath="pages/p/features/main.png",
        state_tree=[],
    )
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(),
        pages={"p": page},
        feature_files={},
    )
    asset = upload_page_asset(
        project,
        "p",
        src,
        preferred_name="mark",
        roi=[0.2, 0.5, 0.2, 0.5],
    )
    assert asset.roi == [0.2, 0.5, 0.2, 0.5]
    assert page.feature_rois["mark"] == [0.2, 0.5, 0.2, 0.5]
    set_asset_roi(page, "mark", None)
    assert "mark" not in page.feature_rois
