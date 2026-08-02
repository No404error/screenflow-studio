from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from screenflow.models import PageDef, Project

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


@dataclass
class PageAsset:
    """One image under a page's detect/ or click/ folder."""

    name: str  # stem / logical key
    kind: str  # detect | click
    relpath: str  # relative to project root, e.g. pages/{id}/detect/main.png


def resolve_asset_path(project: Project, relpath: str | Path) -> Path:
    """Resolve an asset relpath against the project root."""
    rel = Path(str(relpath).replace("\\", "/"))
    if rel.is_absolute():
        return rel
    return (project.root / rel).resolve()


def page_dir(project: Project, page_id: str) -> Path:
    return project.root / "pages" / page_id


def page_json_path(project: Project, page_id: str) -> Path:
    return page_dir(project, page_id) / "page.json"


def page_templates_root(project: Project, page_id: str) -> Path:
    return page_dir(project, page_id)


def page_asset_dir(project: Project, page_id: str, kind: str) -> Path:
    if kind not in ("detect", "click"):
        raise ValueError(f"kind must be detect|click, got {kind!r}")
    return page_templates_root(project, page_id) / kind


def page_asset_relpath(page_id: str, kind: str, filename: str) -> str:
    return f"pages/{page_id}/{kind}/{filename}"


def ensure_page_asset_dirs(project: Project, page_id: str) -> None:
    for kind in ("detect", "click"):
        page_asset_dir(project, page_id, kind).mkdir(parents=True, exist_ok=True)


def _safe_stem(name: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name.strip())
    return safe.strip("_") or "asset"


def list_page_assets(project: Project, page_id: str, kind: str) -> list[PageAsset]:
    """List image assets on disk for a page (detect or click)."""
    folder = page_asset_dir(project, page_id, kind)
    if not folder.is_dir():
        return []
    out: list[PageAsset] = []
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        out.append(
            PageAsset(
                name=path.stem,
                kind=kind,
                relpath=page_asset_relpath(page_id, kind, path.name),
            )
        )
    return out


def upload_page_asset(
    project: Project,
    page_id: str,
    kind: str,
    src: str | Path,
    *,
    preferred_name: str | None = None,
) -> PageAsset:
    """
    Copy an image into the page's detect/ or click/ folder.
    Returns the asset descriptor (logical name + relative path).
    """
    src_path = Path(src)
    if not src_path.exists():
        raise FileNotFoundError(src_path)
    ensure_page_asset_dirs(project, page_id)
    stem = _safe_stem(preferred_name or src_path.stem)
    ext = src_path.suffix.lower() or ".png"
    if ext not in IMAGE_SUFFIXES:
        ext = ".png"
    dest_dir = page_asset_dir(project, page_id, kind)
    dest = dest_dir / f"{stem}{ext}"
    n = 2
    while dest.exists():
        dest = dest_dir / f"{stem}_{n}{ext}"
        n += 1
    shutil.copy2(src_path, dest)
    return PageAsset(
        name=dest.stem,
        kind=kind,
        relpath=page_asset_relpath(page_id, kind, dest.name),
    )


def delete_page_asset(project: Project, page_id: str, kind: str, name: str) -> bool:
    folder = page_asset_dir(project, page_id, kind)
    if not folder.is_dir():
        return False
    removed = False
    for path in folder.iterdir():
        if path.is_file() and path.stem == name:
            path.unlink(missing_ok=True)
            removed = True
    return removed


def sync_page_asset_maps(project: Project, page: PageDef) -> None:
    """
    Rebuild click_map / detect_extras from the page asset folders.
    Keeps map entries whose files still exist elsewhere under the project root.
    """
    page_id = page.page_id
    ensure_page_asset_dirs(project, page_id)

    detect_assets = {a.name: a.relpath for a in list_page_assets(project, page_id, "detect")}
    click_assets = {a.name: a.relpath for a in list_page_assets(project, page_id, "click")}

    legacy_detect = {
        k: v
        for k, v in page.detect_extras.items()
        if k not in detect_assets and resolve_asset_path(project, v).is_file()
    }
    legacy_click = {
        k: v
        for k, v in page.click_map.items()
        if k not in click_assets and resolve_asset_path(project, v).is_file()
    }

    page.detect_extras = {**legacy_detect, **detect_assets}
    page.click_map = {**legacy_click, **click_assets}

    detect_path = resolve_asset_path(project, page.detect_relpath)
    if not detect_path.is_file():
        if detect_assets:
            page.detect_relpath = detect_assets.get(
                "main", next(iter(detect_assets.values()))
            )
        else:
            page.detect_relpath = page_asset_relpath(page_id, "detect", "main.png")


def asset_name_from_relpath(relpath: str) -> str:
    return Path(relpath).stem


def scoped_asset_key(page_id: str, name: str) -> str:
    """Global matcher key so the same asset name can exist on multiple pages."""
    name = name.strip()
    if not name:
        return name
    if name.startswith(f"{page_id}/"):
        return name
    if "/" in name:
        return name
    return f"{page_id}/{name}"
