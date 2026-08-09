from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from screenflow.models import FeatureDef, PageDef, Project, SourceDef, StateNode, VisualDef
from screenflow.roi import normalize_roi

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
FEATURES_DIR = "features"
SOURCES_DIR = "sources"
LEGACY_SOURCE_STEM = "source"


@dataclass
class PageAsset:
    """One derived template crop under a page's features/ folder."""

    name: str  # stem
    relpath: str  # relative to project root


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


def page_sources_dir(project: Project, page_id: str) -> Path:
    return page_dir(project, page_id) / SOURCES_DIR


def page_source_relpath(page_id: str, filename: str) -> str:
    return f"pages/{page_id}/{SOURCES_DIR}/{filename}"


def ensure_page_asset_dirs(project: Project, page_id: str) -> None:
    page_asset_dir(project, page_id).mkdir(parents=True, exist_ok=True)
    page_sources_dir(project, page_id).mkdir(parents=True, exist_ok=True)
    page_dir(project, page_id).mkdir(parents=True, exist_ok=True)


def _safe_stem(name: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name.strip())
    return safe.strip("_") or "asset"


def new_feature_id(page: PageDef, *, prefix: str = "f") -> str:
    n = 1
    while f"{prefix}{n}" in page.features:
        n += 1
    return f"{prefix}{n}"


def add_page_feature(
    page: PageDef,
    *,
    label: str = "",
    feature_id: str | None = None,
    notes: str = "",
) -> FeatureDef:
    fid = (feature_id or "").strip() or new_feature_id(page)
    if fid in page.features:
        raise ValueError(f"feature id exists: {fid}")
    feat = FeatureDef(id=fid, label=(label or fid).strip(), notes=notes or "")
    page.features[fid] = feat
    return feat


def new_visual_id(page: PageDef, preferred: str | None = None) -> str:
    base = _safe_stem(preferred or "setup") or "setup"
    if base not in page.visuals:
        return base
    n = 2
    while f"{base}_{n}" in page.visuals:
        n += 1
    return f"{base}_{n}"


def add_page_visual(
    page: PageDef,
    *,
    template: str,
    label: str = "",
    visual_id: str | None = None,
    search_roi: list[float] | None = None,
    content_roi: list[float] | None = None,
    source_id: str | None = None,
) -> VisualDef:
    """Create a match setup (Visual). Does not select it on any feature."""
    rel = str(template).replace("\\", "/").strip()
    if not rel:
        raise ValueError("empty template")
    sid = str(source_id).strip() if source_id else None
    if sid and sid not in page.sources:
        raise ValueError(f"unknown source_id: {sid}")
    vid = (visual_id or "").strip() or new_visual_id(page, preferred=Path(rel).stem)
    if vid in page.visuals:
        raise ValueError(f"visual id exists: {vid}")
    norm = normalize_roi(search_roi)
    cnorm = normalize_roi(content_roi) if content_roi is not None else None
    vis = VisualDef(
        id=vid,
        label=(label or vid).strip() or vid,
        asset=rel,
        search_roi=list(norm) if norm else None,
        content_roi=list(cnorm) if cnorm else None,
        source_id=sid,
    )
    page.visuals[vid] = vis
    return vis


def update_page_visual(
    page: PageDef,
    visual_id: str,
    *,
    label: str | None = None,
    template: str | None = None,
    search_roi: list[float] | None | object = ...,
    content_roi: list[float] | None | object = ...,
    source_id: str | None | object = ...,
) -> VisualDef:
    vis = page.visuals.get(visual_id)
    if vis is None:
        raise KeyError(visual_id)
    if label is not None:
        vis.label = label.strip() or vis.id
    if template is not None:
        rel = str(template).replace("\\", "/").strip()
        if not rel:
            raise ValueError("empty template")
        vis.asset = rel
    if search_roi is not ...:
        norm = normalize_roi(search_roi) if search_roi is not None else None
        vis.search_roi = list(norm) if norm else None
    if content_roi is not ...:
        if content_roi is None:
            vis.content_roi = None
        else:
            cnorm = normalize_roi(content_roi)
            vis.content_roi = list(cnorm) if cnorm else None
    if source_id is not ...:
        if source_id is None or not str(source_id).strip():
            vis.source_id = None
        else:
            sid = str(source_id).strip()
            if sid not in page.sources:
                raise ValueError(f"unknown source_id: {sid}")
            vis.source_id = sid
    return vis


def delete_page_visual(page: PageDef, visual_id: str) -> bool:
    if visual_id not in page.visuals:
        return False
    del page.visuals[visual_id]
    for feat in page.features.values():
        if feat.visual_id == visual_id:
            feat.visual_id = None
    return True


def select_feature_visual(page: PageDef, feature_id: str, visual_id: str | None) -> FeatureDef:
    """Bind or clear a feature's selected match setup."""
    feat = page.features.get(feature_id)
    if feat is None:
        raise KeyError(feature_id)
    if visual_id is None or not str(visual_id).strip():
        feat.visual_id = None
        return feat
    vid = str(visual_id).strip()
    if vid not in page.visuals:
        raise KeyError(vid)
    feat.visual_id = vid
    return feat


def bind_feature(
    page: PageDef,
    feature_id: str,
    asset: str,
    *,
    search_roi: list[float] | None = None,
    content_roi: list[float] | None = None,
    source_id: str | None = None,
) -> FeatureDef:
    """
    Always create a new Visual and select it on the feature.
    Never mutates an existing Visual (safe when setups are shared).
    Use update_page_visual to edit a setup in place.
    """
    feat = page.features.get(feature_id)
    if feat is None:
        raise KeyError(feature_id)
    rel = str(asset).replace("\\", "/").strip()
    if not rel:
        raise ValueError("empty asset")
    norm = normalize_roi(search_roi)
    cnorm = normalize_roi(content_roi) if content_roi is not None else None
    vis = add_page_visual(
        page,
        template=rel,
        label=feat.label or feature_id,
        visual_id=new_visual_id(page, preferred=feature_id),
        search_roi=list(norm) if norm else None,
        content_roi=list(cnorm) if cnorm else None,
        source_id=source_id,
    )
    feat.visual_id = vis.id
    return feat


def new_source_id(page: PageDef, *, preferred: str | None = None) -> str:
    base = _safe_stem(preferred or "s") or "s"
    if not base.startswith("s"):
        base = f"s_{base}"
    if base not in page.sources:
        return base
    n = 2
    while f"{base}_{n}" in page.sources:
        n += 1
    return f"{base}_{n}"


def add_page_source(
    project: Project,
    page_id: str,
    src: str | Path,
    *,
    label: str = "",
    source_id: str | None = None,
) -> SourceDef:
    """Append a page original (never replaces other originals)."""
    page = project.pages.get(page_id)
    if page is None:
        raise KeyError(page_id)
    src_path = Path(src)
    if not src_path.exists():
        raise FileNotFoundError(src_path)
    ensure_page_asset_dirs(project, page_id)
    preferred = (source_id or "").strip() or None
    sid = preferred or new_source_id(page, preferred=src_path.stem)
    if preferred and sid in page.sources:
        raise ValueError(f"source id exists: {sid}")
    ext = src_path.suffix.lower() or ".png"
    if ext not in IMAGE_SUFFIXES:
        ext = ".png"
    dest_dir = page_sources_dir(project, page_id)
    dest = dest_dir / f"{sid}{ext}"
    n = 2
    base = sid
    while dest.exists() or sid in page.sources:
        sid = f"{base}_{n}"
        dest = dest_dir / f"{sid}{ext}"
        n += 1
    shutil.copy2(src_path, dest)
    rel = page_source_relpath(page_id, dest.name)
    src_def = SourceDef(
        id=sid,
        label=(label or sid).strip() or sid,
        path=rel,
    )
    page.sources[sid] = src_def
    return src_def


def update_page_source(
    page: PageDef,
    source_id: str,
    *,
    label: str | None = None,
) -> SourceDef:
    src = page.sources.get(source_id)
    if src is None:
        raise KeyError(source_id)
    if label is not None:
        src.label = label.strip() or src.id
    return src


def delete_page_source(project: Project, page_id: str, source_id: str) -> bool:
    """Delete an original and cascade-delete visuals that use it."""
    page = project.pages.get(page_id)
    if page is None:
        raise KeyError(page_id)
    src = page.sources.get(source_id)
    if src is None:
        return False
    dead = [vid for vid, v in page.visuals.items() if v.source_id == source_id]
    for vid in dead:
        delete_page_visual(page, vid)
    path = resolve_asset_path(project, src.path)
    if path.is_file():
        path.unlink(missing_ok=True)
    del page.sources[source_id]
    return True


def migrate_legacy_source_files(project: Project, page: PageDef) -> bool:
    """
    Move pages/{id}/source.* into sources/ and rewrite SourceDef.path.
    Returns True if anything changed.
    """
    changed = False
    folder = page_dir(project, page.page_id)
    if not folder.is_dir():
        return False
    ensure_page_asset_dirs(project, page.page_id)
    for path in list(folder.iterdir()):
        if not path.is_file():
            continue
        if path.stem != LEGACY_SOURCE_STEM or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        # Find SourceDef pointing at this legacy file, or create s_legacy
        rel_old = f"pages/{page.page_id}/{path.name}".replace("\\", "/")
        target = None
        for s in page.sources.values():
            if str(s.path).replace("\\", "/") == rel_old:
                target = s
                break
        if target is None and "s_legacy" not in page.sources:
            target = SourceDef(id="s_legacy", label="s_legacy", path=rel_old)
            page.sources["s_legacy"] = target
            for vis in page.visuals.values():
                if not vis.source_id and vis.content_roi:
                    vis.source_id = "s_legacy"
        elif target is None:
            target = page.sources.get("s_legacy")
        if target is None:
            continue
        dest = page_sources_dir(project, page.page_id) / f"{target.id}{path.suffix.lower()}"
        if not dest.exists():
            shutil.move(str(path), str(dest))
        else:
            path.unlink(missing_ok=True)
        new_rel = page_source_relpath(page.page_id, dest.name)
        if target.path != new_rel:
            target.path = new_rel
            changed = True
        elif path.exists():
            changed = True
    # Also rewrite any SourceDef still pointing at legacy stem path
    for s in page.sources.values():
        rel = str(s.path).replace("\\", "/")
        parts = rel.split("/")
        if len(parts) == 3 and parts[0] == "pages" and parts[1] == page.page_id:
            stem = Path(parts[2]).stem
            if stem == LEGACY_SOURCE_STEM:
                src_file = resolve_asset_path(project, rel)
                if src_file.is_file():
                    dest = page_sources_dir(project, page.page_id) / f"{s.id}{src_file.suffix.lower()}"
                    if not dest.exists():
                        shutil.move(str(src_file), str(dest))
                    s.path = page_source_relpath(page.page_id, dest.name)
                    changed = True
    return changed


def set_page_source(
    project: Project,
    page_id: str,
    src: str | Path,
) -> str:
    """Back-compat: append an original (replaces old replace-single semantics)."""
    src_def = add_page_source(project, page_id, src, label="source", source_id=None)
    return src_def.path


def clear_page_source(project: Project, page_id: str) -> None:
    """Back-compat: delete all page originals (cascades visuals)."""
    page = project.pages.get(page_id)
    if page is None:
        raise KeyError(page_id)
    for sid in list(page.sources.keys()):
        delete_page_source(project, page_id, sid)


def unbind_feature(page: PageDef, feature_id: str) -> FeatureDef:
    """Clear the feature's selected match setup (Visual remains on the page)."""
    return select_feature_visual(page, feature_id, None)


def _iter_nodes(nodes: list[StateNode]):
    for n in nodes:
        yield n
        yield from _iter_nodes(n.children)


def _rewrite_feature_refs(nodes: list[StateNode], old_id: str, new_id: str) -> None:
    for n in _iter_nodes(nodes):
        if n.score and (n.score.key or "").strip() == old_id:
            n.score.key = new_id
        for step in n.actions or []:
            if step.op == "click" and str(step.target or "") == old_id:
                step.target = new_id
        if n.post and n.post.tree:
            _rewrite_feature_refs(n.post.tree, old_id, new_id)


def _clear_feature_refs(nodes: list[StateNode], feature_id: str) -> None:
    """Clear score.key / click targets that referenced a deleted feature."""
    for n in _iter_nodes(nodes):
        if n.score and (n.score.key or "").strip() == feature_id:
            n.score.key = ""
        for step in n.actions or []:
            if step.op == "click" and str(step.target or "") == feature_id:
                step.target = ""
        if n.post and n.post.tree:
            _clear_feature_refs(n.post.tree, feature_id)


def delete_page_feature(page: PageDef, feature_id: str) -> bool:
    if feature_id not in page.features:
        return False
    del page.features[feature_id]
    if page.recognize_with == feature_id:
        page.recognize_with = None
    _clear_feature_refs(page.state_tree, feature_id)
    if page.default_post and page.default_post.tree:
        _clear_feature_refs(page.default_post.tree, feature_id)
    return True


def rename_page_feature(
    page: PageDef,
    old_id: str,
    new_id: str,
    *,
    project: Project | None = None,
) -> FeatureDef:
    """
    Rename a feature id and rewrite page (and optional project macro) references.
    """
    old = str(old_id).strip()
    new = _safe_stem(new_id)
    if not old or old not in page.features:
        raise KeyError(old_id)
    if not new:
        raise ValueError("empty feature id")
    if new == old:
        return page.features[old]
    if new in page.features:
        raise ValueError(f"feature id exists: {new}")

    feat = page.features.pop(old)
    if (feat.label or "").strip() == old:
        feat.label = new
    feat.id = new
    page.features[new] = feat
    if page.recognize_with == old:
        page.recognize_with = new
    _rewrite_feature_refs(page.state_tree, old, new)
    if page.default_post and page.default_post.tree:
        _rewrite_feature_refs(page.default_post.tree, old, new)
    if project is not None:
        for macro in project.macros.values():
            for step in macro.steps:
                if step.op == "click" and str(step.target or "") == old:
                    step.target = new
    return feat


def feature_setup_problem(
    project: Project, page: PageDef, feature_id: str | None
) -> str | None:
    """
    None if the feature is runnable; otherwise a validate i18n key suffix:
    - ``unselected`` — no match setup chosen / incomplete setup
    - ``file_missing`` — setup selected but template file is absent
    """
    if not feature_id:
        return "unselected"
    feat = page.features.get(str(feature_id))
    if feat is None or not feat.is_linked():
        return "unselected"
    vis = page.feature_visual(feature_id)
    if vis is None or not vis.is_complete():
        return "unselected"
    if not resolve_asset_path(project, vis.asset).is_file():
        return "file_missing"
    return None


def feature_link_ok(project: Project, page: PageDef, feature_id: str | None) -> bool:
    """True when the feature exists, has a complete Visual, and the template file is present."""
    return feature_setup_problem(project, page, feature_id) is None


def list_page_assets(project: Project, page_id: str) -> list[PageAsset]:
    """List template files on disk for a page (no ROI — ROI lives on VisualDef)."""
    folder = page_asset_dir(project, page_id)
    if not folder.is_dir():
        return []
    out: list[PageAsset] = []
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        rel = page_asset_relpath(page_id, path.name)
        out.append(PageAsset(name=path.stem, relpath=rel))
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
    Copy a template image into the page's features/ folder.
    Does not create a feature or Visual — call bind_feature / select_feature_visual.
    `roi` is ignored (templates do not own search ROI).
    """
    del roi
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
    return PageAsset(name=dest.stem, relpath=page_asset_relpath(page_id, dest.name))


def delete_page_asset(project: Project, page_id: str, name: str) -> bool:
    """Delete template file(s); remove Visuals that used them (clears feature selection)."""
    folder = page_asset_dir(project, page_id)
    if not folder.is_dir():
        return False
    removed_rels: set[str] = set()
    removed = False
    for path in folder.iterdir():
        if path.is_file() and path.stem == name:
            rel = page_asset_relpath(page_id, path.name)
            path.unlink(missing_ok=True)
            removed_rels.add(rel)
            removed = True
    page = project.pages.get(page_id)
    if page is not None and removed_rels:
        norm_removed = {r.replace("\\", "/") for r in removed_rels}
        stems = {Path(r).stem for r in norm_removed}

        def _matches(asset: str) -> bool:
            rel = str(asset or "").replace("\\", "/").strip()
            if rel in norm_removed:
                return True
            # Same page features/ folder, same stem
            if Path(rel).stem in stems and f"pages/{page_id}/{FEATURES_DIR}/" in rel.replace(
                "\\", "/"
            ):
                return True
            return False

        dead = [vid for vid, v in page.visuals.items() if _matches(v.asset)]
        for vid in dead:
            delete_page_visual(page, vid)
    return removed


def asset_name_from_relpath(relpath: str) -> str:
    return Path(relpath).stem


def scoped_asset_key(page_id: str, name: str) -> str:
    """Global matcher key so the same feature id can exist on multiple pages."""
    name = name.strip()
    if not name:
        return name
    if name.startswith(f"{page_id}/"):
        return name
    if "/" in name:
        return name
    return f"{page_id}/{name}"


def sync_page_asset_maps(project: Project, page: PageDef) -> None:
    """Ensure page dirs exist; migrate legacy source.* into sources/."""
    ensure_page_asset_dirs(project, page.page_id)
    migrate_legacy_source_files(project, page)
