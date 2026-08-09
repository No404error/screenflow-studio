"""Asset-level ROI: persist, page/state/click match, override semantics."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from screenflow.assets import add_page_feature, bind_feature, upload_page_asset
from screenflow.decide import score_node
from screenflow.matcher import ScreenMatcher
from screenflow.models import Project, RuntimeConfig, ScoreSpec, StateNode
from screenflow.project import page_to_dict, rebuild_resource_index, _page_from_json
from screenflow.roi import (
    effective_roi,
    expand_roi_for_search,
    normalize_roi,
    roi_from_pixel_rect,
)
from tests.page_helpers import make_page


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
    page = make_page(
        "p",
        detect="pages/p/features/main.png",
        detect_roi=[0.1, 0.4, 0.2, 0.5],
        features={
            "icon": "pages/p/features/icon.png",
            "btn": "pages/p/features/btn.png",
        },
        feature_rois={
            "main": [0.1, 0.4, 0.2, 0.5],
            "icon": [0.7, 0.9, 0.7, 0.9],
            "btn": [0.8, 0.95, 0.1, 0.3],
        },
    )
    raw = page_to_dict(page)
    assert raw["recognize_with"] == "main"
    assert raw["features"]["main"]["visual_id"] == "main"
    assert raw["visuals"]["main"]["search_roi"][0] == 0.1
    assert raw["visuals"]["icon"]["search_roi"] == [0.7, 0.9, 0.7, 0.9]
    assert raw["visuals"]["btn"]["search_roi"] == [0.8, 0.95, 0.1, 0.3]
    back = _page_from_json(raw)
    assert back.recognize_roi() == [0.1, 0.4, 0.2, 0.5]
    assert back.feature_search_roi("icon") == [0.7, 0.9, 0.7, 0.9]
    assert back.feature_search_roi("btn") == [0.8, 0.95, 0.1, 0.3]


def test_legacy_page_json_without_roi():
    back = _page_from_json(
        {
            "id": "p",
            "detect": "pages/p/features/main.png",
            "features": {},
            "state_tree": [],
        }
    )
    assert back.recognize_with == "main"
    assert back.recognize_roi() is None
    vis = back.feature_visual("main")
    assert vis is not None
    assert vis.search_roi is None


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

    page = make_page(
        "a",
        detect="pages/a/features/main.png",
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

    page = make_page(
        "a",
        detect="pages/a/features/main.png",
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

    page = make_page(
        "p",
        detect="pages/p/features/main.png",
        feature_rois={"icon": [0.6, 0.85, 0.6, 0.85]},
        features={
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


def test_upload_then_bind_stores_roi(tmp_path: Path):
    src = tmp_path / "cap.png"
    _write_pattern(src, seed=3, size=40)
    page = make_page("p", detect="pages/p/features/main.png", state_tree=[])
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
    )
    feat = add_page_feature(page, label="mark", feature_id="mark")
    bind_feature(page, feat.id, asset.relpath, search_roi=[0.2, 0.5, 0.2, 0.5])
    assert page.feature_search_roi("mark") == [0.2, 0.5, 0.2, 0.5]
    bind_feature(page, feat.id, asset.relpath, search_roi=None)
    assert page.feature_search_roi("mark") is None


def test_rename_feature_id_rewrites_refs(tmp_path: Path):
    from screenflow.assets import rename_page_feature
    from screenflow.models import ActionStep, ScoreSpec, StateNode

    page = make_page(
        "p",
        detect="pages/p/features/main.png",
        features={"btn": "pages/p/features/btn.png"},
        state_tree=[
            StateNode(
                id="c1",
                name="hit",
                score=ScoreSpec(kind="template", key="btn"),
                actions=[ActionStep(op="click", target="btn")],
            )
        ],
        recognize_with="btn",
    )
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(),
        pages={"p": page},
        feature_files={},
    )
    rename_page_feature(page, "btn", "ok_btn", project=project)
    assert "btn" not in page.features
    assert "ok_btn" in page.features
    assert page.features["ok_btn"].id == "ok_btn"
    assert page.recognize_with == "ok_btn"
    assert page.state_tree[0].score.key == "ok_btn"
    assert page.state_tree[0].actions[0].target == "ok_btn"


def test_page_source_and_content_roi_roundtrip(tmp_path: Path):
    from screenflow.assets import add_page_source, list_page_assets, update_page_visual
    from screenflow.project import load_project, save_project

    src = tmp_path / "full.png"
    _write_pattern(src, seed=9, size=64)
    page = make_page("p", detect="pages/p/features/main.png", state_tree=[])
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(),
        pages={"p": page},
        feature_files={},
    )
    src_def = add_page_source(project, "p", src, label="full", source_id="s_full")
    assert src_def.path == "pages/p/sources/s_full.png"
    assert (tmp_path / "pages" / "p" / "sources" / "s_full.png").is_file()

    asset = upload_page_asset(project, "p", src, preferred_name="mark")
    assert not hasattr(asset, "roi")
    feat = add_page_feature(page, label="mark", feature_id="mark")
    assert not feat.has_visual()
    bind_feature(
        page,
        feat.id,
        asset.relpath,
        search_roi=[0.1, 0.6, 0.1, 0.6],
        content_roi=[0.2, 0.4, 0.2, 0.4],
        source_id="s_full",
    )
    assert feat.has_visual()
    vis = page.feature_visual(feat.id)
    assert vis is not None
    assert vis.template == asset.relpath
    assert vis.source_id == "s_full"
    for a in list_page_assets(project, "p"):
        assert not hasattr(a, "roi")
    save_project(project)

    back = load_project(tmp_path)
    assert "s_full" in back.pages["p"].sources
    assert back.pages["p"].sources["s_full"].path == "pages/p/sources/s_full.png"
    link = back.pages["p"].feature_visual("mark")
    assert link is not None
    assert link.search_roi == [0.1, 0.6, 0.1, 0.6]
    assert link.content_roi == [0.2, 0.4, 0.2, 0.4]
    assert link.source_id == "s_full"

    vid = back.pages["p"].features["mark"].visual_id
    assert vid
    update_page_visual(back.pages["p"], vid, search_roi=[0.0, 0.5, 0.0, 0.5])
    assert back.pages["p"].feature_visual("mark").content_roi == [0.2, 0.4, 0.2, 0.4]


def test_legacy_source_migrates_to_sources_list(tmp_path: Path):
    from screenflow.project import load_project, save_project
    import json

    page_dir = tmp_path / "pages" / "p"
    page_dir.mkdir(parents=True)
    feat_dir = page_dir / "features"
    feat_dir.mkdir()
    src = page_dir / "source.png"
    _write_pattern(src, seed=3, size=32)
    crop = feat_dir / "ok.png"
    _write_pattern(crop, seed=4, size=16)
    (page_dir / "page.json").write_text(
        json.dumps(
            {
                "id": "p",
                "name": "p",
                "source": "pages/p/source.png",
                "visuals": {
                    "v1": {
                        "id": "v1",
                        "label": "v1",
                        "template": "pages/p/features/ok.png",
                        "content_roi": [0.1, 0.5, 0.1, 0.5],
                    }
                },
                "features": {"f1": {"id": "f1", "label": "f1", "visual_id": "v1"}},
                "state_tree": [],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "project.json").write_text(
        json.dumps({"name": "t", "version": 3, "pages": ["p"]}),
        encoding="utf-8",
    )
    project = load_project(tmp_path)
    page = project.pages["p"]
    assert "s_legacy" in page.sources
    assert page.sources["s_legacy"].path.startswith("pages/p/sources/")
    assert not src.exists()
    assert (tmp_path / page.sources["s_legacy"].path).is_file()
    assert page.visuals["v1"].source_id == "s_legacy"
    save_project(project)
    raw = json.loads((page_dir / "page.json").read_text(encoding="utf-8"))
    assert "source" not in raw
    assert "s_legacy" in raw["sources"]


def test_delete_page_source_cascades_visuals(tmp_path: Path):
    from screenflow.assets import add_page_source, add_page_visual, delete_page_source

    src = tmp_path / "a.png"
    _write_pattern(src, seed=1, size=32)
    page = make_page("p", state_tree=[])
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(),
        pages={"p": page},
        feature_files={},
    )
    s = add_page_source(project, "p", src, source_id="s1")
    crop = upload_page_asset(project, "p", src, preferred_name="c")
    add_page_visual(
        page,
        template=crop.relpath,
        label="v",
        visual_id="v1",
        source_id=s.id,
        content_roi=[0.1, 0.5, 0.1, 0.5],
    )
    feat = add_page_feature(page, feature_id="f1", label="f1")
    feat.visual_id = "v1"
    assert delete_page_source(project, "p", "s1")
    assert "s1" not in page.sources
    assert "v1" not in page.visuals
    assert page.features["f1"].visual_id is None


def test_multi_sources_append(tmp_path: Path):
    from screenflow.assets import add_page_source

    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    _write_pattern(a, seed=1, size=24)
    _write_pattern(b, seed=2, size=24)
    page = make_page("p", state_tree=[])
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(),
        pages={"p": page},
        feature_files={},
    )
    s1 = add_page_source(project, "p", a, label="one")
    s2 = add_page_source(project, "p", b, label="two")
    assert len(page.sources) == 2
    assert s1.id != s2.id
    assert (tmp_path / s1.path).is_file()
    assert (tmp_path / s2.path).is_file()


def test_feature_visual_load_accepts_template_key():
    from screenflow.models import FeatureVisual
    from screenflow.project import _feature_link_from_json

    visual = _feature_link_from_json(
        {
            "template": "pages/p/features/a.png",
            "search_roi": [0.1, 0.2, 0.3, 0.4],
        }
    )
    assert isinstance(visual, FeatureVisual)
    assert visual.asset == "pages/p/features/a.png"
    assert visual.template == "pages/p/features/a.png"
    assert visual.search_roi == [0.1, 0.2, 0.3, 0.4]


def test_delete_feature_clears_score_and_click_refs():
    from screenflow.assets import delete_page_feature
    from screenflow.models import ActionStep, ScoreSpec, StateNode

    page = make_page(
        "p",
        detect="pages/p/features/main.png",
        features={"btn": "pages/p/features/btn.png"},
        state_tree=[
            StateNode(
                id="c1",
                name="hit",
                score=ScoreSpec(kind="template", key="btn"),
                actions=[ActionStep(op="click", target="btn")],
            )
        ],
    )
    assert delete_page_feature(page, "btn")
    assert "btn" not in page.features
    assert page.state_tree[0].score.key == ""
    assert page.state_tree[0].actions[0].target == ""


def test_empty_template_visual_roundtrip():
    from screenflow.models import VisualDef
    from screenflow.project import _page_from_json, page_to_dict

    page = make_page("p", state_tree=[])
    page.visuals["draft"] = VisualDef(id="draft", label="draft", asset="")
    raw = page_to_dict(page)
    back = _page_from_json(raw)
    assert "draft" in back.visuals
    assert back.visuals["draft"].asset == ""


def test_delete_asset_cascades_backslash_paths(tmp_path: Path):
    from screenflow.assets import delete_page_asset, upload_page_asset
    from screenflow.models import FeatureDef, Project, RuntimeConfig, VisualDef
    from screenflow.project import rebuild_resource_index

    src = tmp_path / "t.png"
    _write_pattern(src, seed=1, size=16)
    page = make_page("p", state_tree=[])
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(),
        pages={"p": page},
        feature_files={},
    )
    asset = upload_page_asset(project, "p", src, preferred_name="mark")
    # Store with backslashes as a hostile path form
    weird = asset.relpath.replace("/", "\\")
    page.visuals["v"] = VisualDef(id="v", label="v", asset=weird)
    page.features["f"] = FeatureDef(id="f", label="f", visual_id="v")
    rebuild_resource_index(project)
    assert delete_page_asset(project, "p", "mark")
    assert "v" not in page.visuals
    assert page.features["f"].visual_id is None


def test_bind_feature_does_not_mutate_shared_visual():
    from screenflow.assets import select_feature_visual
    from screenflow.models import FeatureDef, VisualDef

    page = make_page("p", state_tree=[])
    page.visuals["shared"] = VisualDef(
        id="shared",
        label="shared",
        asset="pages/p/features/a.png",
        search_roi=[0.1, 0.2, 0.3, 0.4],
    )
    page.features["a"] = FeatureDef(id="a", label="a", visual_id="shared")
    page.features["b"] = FeatureDef(id="b", label="b", visual_id="shared")
    select_feature_visual(page, "a", "shared")
    select_feature_visual(page, "b", "shared")

    bind_feature(
        page,
        "a",
        "pages/p/features/b.png",
        search_roi=[0.5, 0.6, 0.5, 0.6],
        content_roi=[0.5, 0.55, 0.5, 0.55],
    )
    assert page.features["a"].visual_id != "shared"
    assert page.features["b"].visual_id == "shared"
    shared = page.visuals["shared"]
    assert shared.asset == "pages/p/features/a.png"
    assert shared.search_roi == [0.1, 0.2, 0.3, 0.4]
    new_vis = page.feature_visual("a")
    assert new_vis is not None
    assert new_vis.asset == "pages/p/features/b.png"
    assert new_vis.search_roi == [0.5, 0.6, 0.5, 0.6]
