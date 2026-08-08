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
