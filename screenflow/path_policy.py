"""Path boundaries for files and page folders owned by a project."""

from __future__ import annotations

import re
from pathlib import Path


_PAGE_ID = re.compile(r"[A-Za-z0-9_-]+\Z")


def validate_page_id(page_id: str) -> str:
    """Page IDs are single, portable directory names."""
    if not isinstance(page_id, str) or not _PAGE_ID.fullmatch(page_id):
        raise ValueError(f"invalid page id: {page_id!r}")
    return page_id


def resolve_project_path(root: Path, relpath: str) -> Path:
    rel = Path(str(relpath).replace("\\", "/"))
    if not str(relpath).strip() or rel.is_absolute():
        raise ValueError("project path must be relative")
    base = root.resolve()
    full = (base / rel).resolve()
    if not full.is_relative_to(base):
        raise ValueError("path escapes project root")
    return full
