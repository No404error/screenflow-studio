"""Phase 3: save/load reusable state-tree snippets under project/layer_templates/."""

from __future__ import annotations

import json
from pathlib import Path

from screenflow.models import Project, StateNode
from screenflow.project import _node_from_json, _node_to_json


def templates_dir(project: Project) -> Path:
    d = project.root / "layer_templates"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_templates(project: Project) -> list[str]:
    return sorted(p.stem for p in templates_dir(project).glob("*.json"))


def save_template(project: Project, name: str, roots: list[StateNode]) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name) or "layer"
    path = templates_dir(project) / f"{safe}.json"
    path.write_text(
        json.dumps({"tree": [_node_to_json(n) for n in roots]}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    return path


def load_template(project: Project, name: str) -> list[StateNode]:
    path = templates_dir(project) / f"{name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return [_node_from_json(n) for n in data.get("tree") or []]
