from pathlib import Path
import json

import pytest

import screenflow.project as project_module
from screenflow.models import PageDef
from screenflow.project import new_blank_project, load_project, save_project


def test_save_restores_previous_files_when_replace_fails(tmp_path: Path, monkeypatch) -> None:
    root = new_blank_project(tmp_path / "project")
    original = (root / "project.json").read_bytes()
    project = load_project(root)
    project.pages["new_page"] = PageDef(page_id="new_page", name="New")
    replace = project_module.os.replace
    calls = 0

    def fail_second_replace(src, dst):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated disk failure")
        return replace(src, dst)

    with monkeypatch.context() as patch:
        patch.setattr(project_module.os, "replace", fail_second_replace)
        with pytest.raises(OSError, match="simulated disk failure"):
            save_project(project)

    assert (root / "project.json").read_bytes() == original
    assert not (root / "pages" / "new_page" / "page.json").exists()
    assert load_project(root).pages == {}


def test_save_preserves_unregistered_page_folders(tmp_path: Path) -> None:
    root = new_blank_project(tmp_path / "project")
    notes = root / "pages" / "notes"
    notes.mkdir()
    (notes / "readme.txt").write_text("keep", encoding="utf-8")
    save_project(load_project(root))
    assert (notes / "readme.txt").read_text(encoding="utf-8") == "keep"


def test_open_restores_interrupted_save(tmp_path: Path) -> None:
    root = new_blank_project(tmp_path / "project")
    metadata = root / "project.json"
    original = metadata.read_bytes()
    stage = root / ".screenflow-save-interrupted"
    stage.mkdir()
    (stage / "old-0.json").write_bytes(original)
    (stage / "manifest.json").write_text(
        json.dumps({"targets": [{"path": "project.json", "backup": "old-0.json"}], "stale_pages": []}),
        encoding="utf-8",
    )
    metadata.write_text("interrupted", encoding="utf-8")

    assert load_project(root).name == "Untitled Project"
    assert metadata.read_bytes() == original
    assert not stage.exists()
