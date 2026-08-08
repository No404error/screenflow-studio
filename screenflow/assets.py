from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from screenflow.models import PageDef, Project
from screenflow.roi import normalize_roi

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
FEATURES_DIR = "features"


@dataclass
class PageAsset:
    """One image under a page's features/ folder."""

    name: str  # stem / logical key
    relpath: str  # relative to project root, e.g. pages/{id}/features/main.png
    roi: list[float] | None = None  # optional [y0, y1, x0, x1]


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


def page_asset_dir(project: Project, page_id: str) -> Path:
    return page_dir(project, page_id) / FEATURES_DIR


def page_asset_relpath(page_id: str, filename: str) -> str:
    return f"pages/{page_id}/{FEATURES_DIR}/{filename}"


def ensure_page_asset_dirs(project: Project, page_id: str) -> None:
    page_asset_dir(project, page_id).mkdir(parents=True, exist_ok=True)


def _safe_stem(name: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name.strip())
    return safe.strip("_") or "asset"


def list_page_assets(project: Project, page_id: str) -> list[PageAsset]:
    """List feature images on disk for a page."""
    folder = page_asset_dir(project, page_id)
    if not folder.is_dir():
        return []
    page = project.pages.get(page_id)
    rois = page.feature_rois if page is not None else {}
    out: list[PageAsset] = []
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        stem = path.stem
        roi_raw = rois.get(stem)
        norm = normalize_roi(roi_raw)
        out.append(
            PageAsset(
                name=stem,
                relpath=page_asset_relpath(page_id, path.name),
                roi=list(norm) if norm else None,
            )
        )
    return out


def upload_page_asset(
    project: Project,
    page_id: str,
    src: str | Path,
    *,
    preferred_name: str | None = None,
    roi: list[float] | None = None,
) -> PageAsset:
    """
    Copy an image into the page's features/ folder.
    Optional roi [y0,y1,x0,x1] is stored on the page maps (None = full-frame search).
    """
    src_path = Path(src)
    if not src_path.exists():
        raise FileNotFoundError(src_path)
    ensure_page_asset_dirs(project, page_id)
    stem = _safe_stem(preferred_name or src_path.stem)
    ext = src_path.suffix.lower() or ".png"
    if ext not in IMAGE_SUFFIXES:
        ext = ".png"
    dest_dir = page_asset_dir(project, page_id)
    dest = dest_dir / f"{stem}{ext}"
    n = 2
    while dest.exists():
        dest = dest_dir / f"{stem}_{n}{ext}"
        n += 1
    shutil.copy2(src_path, dest)
    asset = PageAsset(
        name=dest.stem,
        relpath=page_asset_relpath(page_id, dest.name),
        roi=None,
    )
    page = project.pages.get(page_id)
    if page is not None:
        set_asset_roi(page, asset.name, roi)
        asset.roi = list(normalize_roi(roi)) if normalize_roi(roi) else None
    return asset


def set_asset_roi(page: PageDef, name: str, roi: list[float] | None) -> None:
    """Attach or clear search ROI for a logical asset name on the page."""
    norm = normalize_roi(roi)
    name = name.strip()
    if norm is None:
        page.feature_rois.pop(name, None)
    else:
        page.feature_rois[name] = list(norm)
    if Path(page.detect_relpath).stem == name:
        page.detect_roi = list(norm) if norm else None


def delete_page_asset(project: Project, page_id: str, name: str) -> bool:
    folder = page_asset_dir(project, page_id)
    if not folder.is_dir():
        return False
    removed = False
    for path in folder.iterdir():
        if path.is_file() and path.stem == name:
            path.unlink(missing_ok=True)
            removed = True
    page = project.pages.get(page_id)
    if page is not None and removed:
        set_asset_roi(page, name, None)
        page.feature_map.pop(name, None)
    return removed


def sync_page_asset_maps(project: Project, page: PageDef) -> None:
    """
    Rebuild feature_map from the page features/ folder.
    Keeps map entries whose files still exist elsewhere under the project root.
    Prunes ROI entries for names that no longer exist.
    """
    page_id = page.page_id
    ensure_page_asset_dirs(project, page_id)

    disk = {a.name: a.relpath for a in list_page_assets(project, page_id)}

    legacy = {
        k: v
        for k, v in page.feature_map.items()
        if k not in disk and resolve_asset_path(project, v).is_file()
    }

    page.feature_map = {**legacy, **disk}

    page.feature_rois = {
        k: list(v)
        for k, v in page.feature_rois.items()
        if k in page.feature_map and normalize_roi(v)
    }

    detect_path = resolve_asset_path(project, page.detect_relpath)
    if not detect_path.is_file():
        if disk:
            page.detect_relpath = disk.get("main", next(iter(disk.values())))
        else:
            page.detect_relpath = page_asset_relpath(page_id, "main.png")

    stem = Path(page.detect_relpath).stem
    if stem in page.feature_rois:
        page.detect_roi = list(page.feature_rois[stem])
    elif page.detect_roi is not None and not normalize_roi(page.detect_roi):
        page.detect_roi = None


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
