from pathlib import Path

import pytest

from screenflow.assets import delete_page_source, page_dir, resolve_asset_path
from screenflow.models import PageDef, Project, RuntimeConfig, SourceDef
from screenflow.path_policy import resolve_project_path, validate_page_id


def test_project_path_rejects_sibling_with_same_prefix(tmp_path: Path) -> None:
    root = tmp_path / "project"
    with pytest.raises(ValueError, match="escapes"):
        resolve_project_path(root, "../project_private/secret.txt")


@pytest.mark.parametrize("page_id", ["../outside", "a/b", "a\\b", "C:other", "."])
def test_page_id_cannot_escape_page_directory(tmp_path: Path, page_id: str) -> None:
    project = Project("test", tmp_path, RuntimeConfig(), {})
    with pytest.raises(ValueError, match="invalid page id"):
        validate_page_id(page_id)
    with pytest.raises(ValueError, match="invalid page id"):
        page_dir(project, page_id)


def test_external_source_path_is_not_deleted(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"keep")
    page = PageDef(page_id="page", sources={"s": SourceDef("s", path=str(outside))})
    project = Project("test", root, RuntimeConfig(), {"page": page})
    with pytest.raises(ValueError):
        resolve_asset_path(project, outside)
    assert delete_page_source(project, "page", "s") is True
    assert outside.read_bytes() == b"keep"
