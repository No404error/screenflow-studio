import json
import tempfile
from pathlib import Path

import pytest

from screenflow.models import ActionStep, PageDef, Project, RuntimeConfig, ScoreSpec, StateNode
from screenflow.project import ProjectLoadError, load_project, save_project


def _blank(root: Path) -> Project:
    (root / "pages").mkdir(parents=True)
    return Project(
        name="t",
        root=root,
        runtime=RuntimeConfig(),
        pages={},
        detect_files={},
        click_files={},
    )


def _write_page(root: Path, page_id: str, raw: dict) -> None:
    d = root / "pages" / page_id
    d.mkdir(parents=True, exist_ok=True)
    raw = dict(raw)
    raw.setdefault("id", page_id)
    (d / "page.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def test_reject_probe():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _blank(root)
        _write_page(
            root,
            "p",
            {
                "detect": "pages/p/detect/main.png",
                "probe_steps": [{"op": "wait", "target": 0.1}],
                "state_tree": [],
            },
        )
        (root / "project.json").write_text(
            json.dumps({"name": "x", "version": 3, "pages": ["p"]}),
            encoding="utf-8",
        )
        with pytest.raises(ProjectLoadError):
            load_project(root)


def test_legacy_flat_static_ok():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _blank(root)
        _write_page(
            root,
            "p",
            {
                "detect": "pages/p/detect/main.png",
                "states": [
                    {
                        "name": "A",
                        "kind": "STATIC",
                        "priority": 1,
                        "detect_key": "a",
                    }
                ],
                "actions": {"A": [{"op": "wait", "target": 0.1}]},
            },
        )
        (root / "project.json").write_text(
            json.dumps({"name": "x", "version": 3, "pages": ["p"]}),
            encoding="utf-8",
        )
        proj = load_project(root)
        assert len(proj.pages["p"].state_tree) == 1
        assert proj.pages["p"].state_tree[0].actions[0].op == "wait"


def test_legacy_dynamic_rejected():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _blank(root)
        _write_page(
            root,
            "p",
            {
                "detect": "x.png",
                "states": [
                    {
                        "name": "D",
                        "kind": "DYNAMIC",
                        "when_field": "x",
                    }
                ],
                "actions": {},
            },
        )
        (root / "project.json").write_text(
            json.dumps({"name": "x", "version": 3, "pages": ["p"]}),
            encoding="utf-8",
        )
        with pytest.raises(ProjectLoadError):
            load_project(root)


def test_monolith_pages_rejected():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _blank(root)
        (root / "project.json").write_text(
            json.dumps(
                {
                    "name": "x",
                    "pages": [
                        {
                            "id": "p",
                            "detect": "pages/p/detect/main.png",
                            "state_tree": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ProjectLoadError):
            load_project(root)


def test_roundtrip_tree():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        proj = _blank(root)
        proj.pages["p"] = PageDef(
            page_id="p",
            detect_relpath="pages/p/detect/main.png",
            state_tree=[
                StateNode(
                    id="leaf",
                    name="Leaf",
                    score=ScoreSpec(key="k", source="detect"),
                    actions=[ActionStep("wait", 0.2)],
                )
            ],
        )
        save_project(proj)
        assert (root / "pages" / "p" / "page.json").is_file()
        loaded = load_project(root)
        assert loaded.pages["p"].state_tree[0].id == "leaf"
        assert loaded.pages["p"].state_tree[0].actions[0].target == 0.2


def test_invert_score_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        proj = _blank(root)
        proj.pages["p"] = PageDef(
            page_id="p",
            detect_relpath="pages/p/detect/main.png",
            state_tree=[
                StateNode(
                    id="inv",
                    name="Inv",
                    score=ScoreSpec(
                        kind="invert",
                        key="gone",
                        source="detect",
                        roi=[0.1, 0.9, 0.1, 0.9],
                    ),
                    actions=[],
                )
            ],
        )
        save_project(proj)
        loaded = load_project(root)
        spec = loaded.pages["p"].state_tree[0].score
        assert spec is not None
        assert spec.kind == "invert"
        assert spec.key == "gone"
        assert spec.roi == [0.1, 0.9, 0.1, 0.9]


def test_decide_params_on_close_roundtrip():
    from screenflow.models import DecideParams
    from screenflow.project import merge_decide_params

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        proj = _blank(root)
        proj.pages["p"] = PageDef(
            page_id="p",
            detect_relpath="pages/p/detect/main.png",
            decide_params=DecideParams(margin=0.05, on_close="abstain"),
            state_tree=[StateNode(id="DEFAULT", is_else=True, actions=[])],
        )
        save_project(proj)
        loaded = load_project(root)
        dp = loaded.pages["p"].decide_params
        assert dp.on_close == "abstain"
        assert dp.margin == 0.05
        merged = merge_decide_params(loaded.runtime, dp)
        assert merged.on_close == "abstain"
        assert merged.margin == 0.05
        # default merge stays priority
        assert merge_decide_params(loaded.runtime).on_close == "priority"
