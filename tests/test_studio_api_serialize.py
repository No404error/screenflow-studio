"""Web Studio DTO round-trip."""

from __future__ import annotations

from pathlib import Path

from tests.page_helpers import make_page
from screenflow.models import ActionStep, PageDef, Project, RuntimeConfig, StateNode
from screenflow.project import load_project, new_blank_project, save_project
from studio_api.serialize import apply_full_project_dto, full_project_dto


def test_full_dto_roundtrip(tmp_path: Path) -> None:
    root = new_blank_project(tmp_path / "p", name="WebDTO")
    project = load_project(root)
    project.var_defaults = {"armed": False, "count": 1}
    project.var_schema = {
        "armed": {"type": "bool", "description": "ready"},
        "count": {"type": "number", "description": ""},
    }
    page = make_page("lobby", detect="pages/lobby/features/main.png",
        name="Lobby",
        state_tree=[
            StateNode(
                id="a",
                name="A",
                when_var="armed",
                score=None,
                is_else=True,
                actions=[ActionStep(op="set_var", target="count=2")],
            )
        ],
    )
    project.pages["lobby"] = page
    save_project(project)

    loaded = load_project(root)
    dto = full_project_dto(loaded)
    assert dto["vars"]["armed"] is False
    assert dto["var_schema"]["armed"]["type"] == "bool"
    assert "lobby" in dto["page_docs"]
    assert dto["page_docs"]["lobby"]["state_tree"][0]["when_var"] == "armed"

    dto["name"] = "Renamed"
    dto["vars"]["armed"] = True
    dto["page_docs"]["lobby"]["name"] = "Lobby2"
    apply_full_project_dto(loaded, dto)
    save_project(loaded)

    again = load_project(root)
    assert again.name == "Renamed"
    assert again.var_defaults["armed"] is True
    assert again.pages["lobby"].name == "Lobby2"


def test_dto_includes_sources_and_visual_source_id(tmp_path: Path) -> None:
    from screenflow.assets import add_page_source, add_page_visual, upload_page_asset
    import cv2
    import numpy as np

    root = new_blank_project(tmp_path / "src", name="Src")
    project = load_project(root)
    page = make_page("lobby", name="Lobby", state_tree=[])
    project.pages["lobby"] = page
    png = tmp_path / "o.png"
    cv2.imwrite(str(png), np.zeros((20, 20, 3), dtype=np.uint8))
    src = add_page_source(project, "lobby", png, label="orig", source_id="s1")
    asset = upload_page_asset(project, "lobby", png, preferred_name="c")
    add_page_visual(
        page,
        template=asset.relpath,
        label="v",
        visual_id="v1",
        source_id=src.id,
        content_roi=[0.1, 0.4, 0.1, 0.4],
    )
    dto = full_project_dto(project)
    doc = dto["page_docs"]["lobby"]
    assert "s1" in doc["sources"]
    assert doc["sources"]["s1"]["label"] == "orig"
    assert doc["visuals"]["v1"]["source_id"] == "s1"
    assert "source" not in doc or doc.get("source") in (None, "")


def test_dto_linked_false_when_template_file_missing(tmp_path: Path) -> None:
    root = new_blank_project(tmp_path / "miss", name="Miss")
    project = load_project(root)
    page = make_page(
        "lobby",
        detect="pages/lobby/features/missing.png",
        name="Lobby",
        state_tree=[],
    )
    project.pages["lobby"] = page
    dto = full_project_dto(project)
    feat = dto["page_docs"]["lobby"]["features"]["missing"]
    assert feat["has_visual"] is True
    assert feat["linked"] is False
    assert feat["visual"]["file_missing"] is True


def test_apply_dto_strips_nested_link_and_detect(tmp_path: Path) -> None:
    """Studio convenience fields must not re-promote or revive recognize_with."""
    root = new_blank_project(tmp_path / "p2", name="Strip")
    project = load_project(root)
    page = make_page(
        "lobby",
        detect="pages/lobby/features/main.png",
        name="Lobby",
        state_tree=[],
    )
    project.pages["lobby"] = page
    save_project(project)
    loaded = load_project(root)
    dto = full_project_dto(loaded)
    # Clear recognize; leave detect + nested link as a hostile client would
    dto["page_docs"]["lobby"]["recognize_with"] = None
    dto["page_docs"]["lobby"]["detect"] = "pages/lobby/features/main.png"
    feat = dto["page_docs"]["lobby"]["features"]["main"]
    feat["link"] = {
        "asset": "pages/lobby/features/other.png",
        "template": "pages/lobby/features/other.png",
        "search_roi": [0.1, 0.2, 0.3, 0.4],
    }
    # Keep visuals pointing at main.png
    apply_full_project_dto(loaded, dto)
    p = loaded.pages["lobby"]
    assert p.recognize_with is None
    assert p.features["main"].visual_id == "main"
    assert p.visuals["main"].asset == "pages/lobby/features/main.png"
    # Nested link must not overwrite the visual asset
    assert "other.png" not in p.visuals["main"].asset
