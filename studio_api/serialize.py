"""Project <-> JSON DTO for the Web Studio."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from screenflow.assets import (
    feature_link_ok,
    list_page_assets,
    resolve_asset_path,
    sync_page_asset_maps,
)
from screenflow.models import Project
from screenflow.project import (
    _macros_from_json,
    _page_from_json,
    _runtime_from_json,
    page_to_dict,
    project_to_dict,
    rebuild_resource_index,
)


def _source_dto(src) -> dict[str, Any]:
    return {
        "id": src.id,
        "label": src.label or src.id,
        "path": src.path,
    }


def _visual_dto(project: Project, vis) -> dict[str, Any]:
    file_ok = False
    if vis.is_complete():
        try:
            file_ok = resolve_asset_path(project, vis.asset).is_file()
        except Exception:
            file_ok = False
    return {
        "id": vis.id,
        "label": vis.label or vis.id,
        "asset": vis.asset,
        "template": vis.asset,
        "source_id": vis.source_id,
        "search_roi": list(vis.search_roi) if vis.search_roi else None,
        "content_roi": list(vis.content_roi) if vis.content_roi else None,
        "complete": bool(file_ok),
        "file_missing": bool(vis.is_complete() and not file_ok),
    }


def _feature_dto(project: Project, page, feat) -> dict[str, Any]:
    """Feature + selected Visual (via visual_id)."""
    vis = page.feature_visual(feat.id)
    runnable = feature_link_ok(project, page, feat.id)
    out: dict[str, Any] = {
        "id": feat.id,
        "label": feat.label or feat.id,
        "notes": feat.notes or "",
        "visual_id": feat.visual_id,
        # Runnable for Start (selection + template file present)
        "linked": runnable,
        # Selection resolves to a Visual object (may still miss file)
        "has_visual": feat.has_visual() and vis is not None,
    }
    if vis is not None:
        payload = _visual_dto(project, vis)
        out["link"] = payload  # back-compat for older UI fields
        out["visual"] = payload
    else:
        out["link"] = None
        out["visual"] = None
    return out


def full_project_dto(project: Project) -> dict[str, Any]:
    """Snapshot suitable for the Vue editor (root meta + embedded pages)."""
    root = project_to_dict(project)
    pages: dict[str, Any] = {}
    for pid, page in project.pages.items():
        sync_page_asset_maps(project, page)
        doc = page_to_dict(page)
        doc["detect"] = page.recognize_asset() or ""
        doc["detect_roi"] = page.recognize_roi()
        doc["sources"] = {sid: _source_dto(s) for sid, s in page.sources.items()}
        doc["visuals"] = {vid: _visual_dto(project, v) for vid, v in page.visuals.items()}
        doc["features"] = {
            fid: _feature_dto(project, page, f) for fid, f in page.features.items()
        }
        doc["assets"] = [
            {"name": a.name, "relpath": a.relpath}
            for a in list_page_assets(project, pid)
        ]
        pages[pid] = doc
    root["page_docs"] = pages
    root["root"] = str(project.root)
    if project.var_schema:
        root["var_schema"] = project.var_schema
    return root


def apply_full_project_dto(project: Project, data: dict[str, Any]) -> Project:
    """Mutate/rebuild in-memory project from a full DTO, keeping the same root."""
    root_path = project.root
    runtime = _runtime_from_json(data.get("runtime") or {})
    macros = _macros_from_json(data.get("macros") or [])

    page_docs = data.get("page_docs") or {}
    pages: dict[str, Any] = {}
    page_ids: list[str]
    if isinstance(page_docs, dict) and page_docs:
        page_ids = list(page_docs.keys())
    else:
        raw_pages = data.get("pages") or []
        page_ids = [str(x) for x in raw_pages]

    for pid in page_ids:
        raw = page_docs.get(pid) if isinstance(page_docs, dict) else None
        if not isinstance(raw, dict):
            if pid in project.pages:
                pages[pid] = project.pages[pid]
            continue
        raw = dict(raw)
        # Strip Studio convenience fields so nested link/detect cannot re-promote
        for junk in ("assets", "detect", "detect_roi"):
            raw.pop(junk, None)
        feats = raw.get("features")
        if isinstance(feats, dict):
            cleaned: dict[str, Any] = {}
            for k, v in feats.items():
                if isinstance(v, dict):
                    fv = dict(v)
                    for fk in ("link", "visual", "linked", "has_visual", "complete"):
                        fv.pop(fk, None)
                    cleaned[str(k)] = fv
                else:
                    cleaned[str(k)] = v
            raw["features"] = cleaned
        pages[pid] = _page_from_json(raw, page_id=pid)

    for pair in data.get("page_pairs") or []:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        a, b = str(pair[0]), str(pair[1])
        if a in pages and b in pages:
            pages[a].pair_with = b
            pages[b].pair_with = a

    var_schema_raw = data.get("var_schema") or {}
    var_schema: dict[str, dict[str, Any]] = {}
    if isinstance(var_schema_raw, dict):
        for k, v in var_schema_raw.items():
            if isinstance(v, dict):
                var_schema[str(k)] = dict(v)

    project.name = str(data.get("name") or project.name)
    project.runtime = runtime
    project.pages = pages
    project.macros = macros
    project.var_defaults = dict(data.get("vars") or {})
    project.var_schema = var_schema
    project.root = root_path
    for page in project.pages.values():
        sync_page_asset_maps(project, page)
    rebuild_resource_index(project)
    return project


def resolve_under_root(root: Path, relpath: str) -> Path:
    rel = Path(str(relpath).replace("\\", "/"))
    if rel.is_absolute():
        raise ValueError("absolute paths not allowed")
    full = (root / rel).resolve()
    if not str(full).startswith(str(root.resolve())):
        raise ValueError("path escapes project root")
    return full
