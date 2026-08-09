"""FastAPI application for ScreenFlow Web Studio."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from screenflow.assets import (
    add_page_feature,
    add_page_source,
    add_page_visual,
    bind_feature,
    clear_page_source,
    delete_page_asset,
    delete_page_feature,
    delete_page_source,
    delete_page_visual,
    ensure_page_asset_dirs,
    list_page_assets,
    rename_page_feature,
    select_feature_visual,
    unbind_feature,
    update_page_source,
    update_page_visual,
    upload_page_asset,
)
from screenflow.project import (
    load_project,
    new_blank_project,
    rebuild_resource_index,
    save_project,
    slugify_id,
)
from screenflow.models import PageDef
from studio_api import settings as ui_settings
from studio_api.i18n import I18n

from studio_api.engine_bridge import bridge
from studio_api.serialize import (
    apply_full_project_dto,
    full_project_dto,
    resolve_under_root,
)

app = FastAPI(title="ScreenFlow Web Studio API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_i18n = I18n(lang="en")


def _sync_ui_lang() -> str:
    """Keep API translate language aligned with saved UI language (Issues / validate)."""
    lang = (ui_settings.load_ui_settings().get("lang") or "en").strip().lower()
    if lang not in ("en", "zh"):
        lang = "en"
    _i18n.lang = lang
    return lang


_sync_ui_lang()


def _t(key: str, **kwargs: object) -> str:
    return _i18n.t(key, **kwargs)


class OpenBody(BaseModel):
    path: str


class NewBody(BaseModel):
    parent: str
    name: str = "Untitled Project"


class SaveBody(BaseModel):
    project: dict[str, Any]


class RuntimeBody(BaseModel):
    runtime: dict[str, Any]


class AddPageBody(BaseModel):
    name: str


class AddMacroBody(BaseModel):
    name: str
    id: str | None = None


class FeatureCreateBody(BaseModel):
    label: str = ""
    id: str | None = None
    notes: str = ""


class FeaturePatchBody(BaseModel):
    label: str | None = None
    notes: str | None = None
    recognize: bool | None = None
    id: str | None = None


class FeatureBindBody(BaseModel):
    """Legacy: create/update a Visual from template+ROI and select it."""

    asset: str
    search_roi: list[float] | None = None
    content_roi: list[float] | None = None


class FeatureSelectVisualBody(BaseModel):
    visual_id: str | None = None


class VisualCreateBody(BaseModel):
    template: str
    label: str = ""
    id: str | None = None
    search_roi: list[float] | None = None
    content_roi: list[float] | None = None
    source_id: str | None = None


class VisualPatchBody(BaseModel):
    label: str | None = None
    template: str | None = None
    search_roi: list[float] | None = None
    content_roi: list[float] | None = None
    clear_search_roi: bool = False
    clear_content_roi: bool = False
    source_id: str | None = None
    clear_source_id: bool = False


class SourcePatchBody(BaseModel):
    label: str | None = None


class LangBody(BaseModel):
    lang: str = "en"


class SettingsPatch(BaseModel):
    runner_mode: str | None = None
    reopen_last_project: bool | None = None


class StartBody(BaseModel):
    mode: str | None = None
    allow_warnings: bool = False


class FolderBody(BaseModel):
    initial: str | None = None
    title: str | None = None


class TemplateSaveBody(BaseModel):
    name: str
    tree: list[dict[str, Any]]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def add_api_root_hint() -> None:
    """Register GET / only when UI is not mounted (avoids clashing with StaticFiles)."""

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "service": "ScreenFlow Web Studio API",
            "health": "/api/health",
            "ui_dev": "http://127.0.0.1:5173/",
            "hint": "In --dev mode open the Vite URL, not this API port.",
        }


@app.get("/api/settings")
def get_settings() -> dict[str, Any]:
    data = ui_settings.load_ui_settings()
    lang = _sync_ui_lang()
    return {
        "lang": lang,
        "recent": ui_settings.get_recent(),
        "runner_mode": bridge.runner_mode,
        "reopen_last_project": bool(data.get("reopen_last_project", True)),
        "reopen_path": (
            str(p) if (p := ui_settings.resolve_reopen_project_path()) is not None else None
        ),
    }


@app.post("/api/settings/lang")
def set_lang(body: LangBody) -> dict[str, str]:
    lang = body.lang if body.lang in ("en", "zh") else "en"
    ui_settings.update_ui_settings(lang=lang)
    _i18n.lang = lang
    return {"lang": lang}


@app.patch("/api/settings")
def patch_settings(body: SettingsPatch) -> dict[str, Any]:
    if body.runner_mode is not None:
        try:
            bridge.set_runner_mode(body.runner_mode)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    if body.reopen_last_project is not None:
        ui_settings.set_reopen_last_project(body.reopen_last_project)
    return get_settings()


@app.post("/api/settings/clear-recent")
def clear_recent() -> dict[str, Any]:
    ui_settings.clear_recent()
    return get_settings()


@app.post("/api/dialog/folder")
def pick_folder(body: FolderBody | None = None) -> dict[str, str | None]:
    """Native folder picker (tkinter). Blocks until user chooses or cancels."""
    import tkinter as tk
    from tkinter import filedialog

    initial = (body.initial if body else None) or str(Path.home())
    title = (body.title if body else None) or "Select folder"
    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    try:
        path = filedialog.askdirectory(initialdir=initial, title=title, parent=root)
    finally:
        root.destroy()
    return {"path": path or None}


@app.post("/api/project/open")
def open_project(body: OpenBody) -> dict[str, Any]:
    path = Path(body.path).expanduser().resolve()
    if not (path / "project.json").is_file():
        raise HTTPException(400, f"project.json not found in {path}")
    try:
        project = load_project(path)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    bridge.set_project(project)
    ui_settings.touch_recent(str(path), project.name)
    return full_project_dto(project)


@app.post("/api/project/new")
def create_project(body: NewBody) -> dict[str, Any]:
    parent = Path(body.parent).expanduser().resolve()
    parent.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in body.name).strip()
    folder = parent / (safe or "Untitled Project")
    if folder.exists() and any(folder.iterdir()):
        raise HTTPException(400, f"Directory not empty: {folder}")
    root = new_blank_project(folder, name=body.name)
    project = load_project(root)
    bridge.set_project(project)
    ui_settings.touch_recent(str(root), project.name)
    return full_project_dto(project)


@app.get("/api/project")
def get_project() -> dict[str, Any]:
    if bridge.project is None:
        raise HTTPException(404, "No project open")
    return full_project_dto(bridge.project)


@app.put("/api/project")
def save_project_api(body: SaveBody) -> dict[str, Any]:
    if bridge.project is None:
        raise HTTPException(404, "No project open")
    try:
        apply_full_project_dto(bridge.project, body.project)
        save_project(bridge.project)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return full_project_dto(bridge.project)


@app.post("/api/project/add-page")
def add_page(body: AddPageBody) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    pid = slugify_id(body.name, project.pages.keys())
    page = PageDef(
        page_id=pid,
        name=body.name.strip() or pid,
    )
    project.pages[pid] = page
    ensure_page_asset_dirs(project, pid)
    rebuild_resource_index(project)
    save_project(project)
    return full_project_dto(project)


@app.delete("/api/project/pages/{page_id}")
def delete_page(page_id: str) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    if page_id not in project.pages:
        raise HTTPException(404, "page not found")
    del project.pages[page_id]
    save_project(project)
    return full_project_dto(project)


@app.post("/api/project/add-macro")
def add_macro(body: AddMacroBody) -> dict[str, Any]:
    from screenflow.models import MacroDef

    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    mid = body.id or slugify_id(body.name, project.macros.keys(), fallback="macro")
    if mid in project.macros:
        raise HTTPException(400, "macro id exists")
    project.macros[mid] = MacroDef(id=mid, name=body.name.strip() or mid, steps=[])
    save_project(project)
    return full_project_dto(project)


@app.delete("/api/project/macros/{macro_id}")
def delete_macro(macro_id: str) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    project.macros.pop(macro_id, None)
    save_project(project)
    return full_project_dto(project)


@app.get("/api/project/pages/{page_id}/assets")
def page_assets(page_id: str) -> list[dict[str, Any]]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    if page_id not in project.pages:
        raise HTTPException(404, "page not found")
    return [
        {"name": a.name, "relpath": a.relpath}
        for a in list_page_assets(project, page_id)
    ]


@app.post("/api/project/pages/{page_id}/assets")
async def upload_asset(
    page_id: str,
    file: UploadFile = File(...),
    preferred_name: str | None = None,
) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    if page_id not in project.pages:
        raise HTTPException(404, "page not found")
    suffix = Path(file.filename or "asset.png").suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        content = await file.read()
        tmp.write(content)
    try:
        asset = upload_page_asset(
            project,
            page_id,
            tmp_path,
            preferred_name=preferred_name or Path(file.filename or "asset").stem,
        )
        save_project(project)
    finally:
        tmp_path.unlink(missing_ok=True)
    return {"name": asset.name, "relpath": asset.relpath}


@app.post("/api/project/pages/{page_id}/sources")
async def upload_page_source_item(
    page_id: str,
    file: UploadFile = File(...),
    label: str | None = None,
) -> dict[str, Any]:
    """Append a page original screenshot (Studio material for match setups)."""
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    if page_id not in project.pages:
        raise HTTPException(404, "page not found")
    suffix = Path(file.filename or "source.png").suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        content = await file.read()
        tmp.write(content)
    try:
        add_page_source(
            project,
            page_id,
            tmp_path,
            label=label or Path(file.filename or "source").stem,
        )
        save_project(project)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)
    return full_project_dto(project)


@app.patch("/api/project/pages/{page_id}/sources/{source_id}")
def patch_page_source(
    page_id: str, source_id: str, body: SourcePatchBody
) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    page = project.pages.get(page_id)
    if page is None:
        raise HTTPException(404, "page not found")
    try:
        update_page_source(page, source_id, label=body.label)
    except KeyError as exc:
        raise HTTPException(404, "source not found") from exc
    save_project(project)
    return full_project_dto(project)


@app.delete("/api/project/pages/{page_id}/sources/{source_id}")
def remove_page_source_item(page_id: str, source_id: str) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    if page_id not in project.pages:
        raise HTTPException(404, "page not found")
    try:
        if not delete_page_source(project, page_id, source_id):
            raise HTTPException(404, "source not found")
        rebuild_resource_index(project)
        save_project(project)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return full_project_dto(project)


@app.post("/api/project/pages/{page_id}/source")
async def upload_page_source(
    page_id: str,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Back-compat: append an original (same as POST .../sources)."""
    return await upload_page_source_item(page_id, file)


@app.delete("/api/project/pages/{page_id}/source")
def remove_page_source(page_id: str) -> dict[str, Any]:
    """Back-compat: clear all page originals."""
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    if page_id not in project.pages:
        raise HTTPException(404, "page not found")
    try:
        clear_page_source(project, page_id)
        rebuild_resource_index(project)
        save_project(project)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return full_project_dto(project)


@app.delete("/api/project/pages/{page_id}/assets/{name}")
def remove_asset(page_id: str, name: str) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    try:
        delete_page_asset(project, page_id, name)
        rebuild_resource_index(project)
        save_project(project)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return full_project_dto(project)


@app.post("/api/project/pages/{page_id}/features")
def create_feature(page_id: str, body: FeatureCreateBody) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    page = project.pages.get(page_id)
    if page is None:
        raise HTTPException(404, "page not found")
    try:
        add_page_feature(
            page,
            label=body.label,
            feature_id=body.id,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    rebuild_resource_index(project)
    save_project(project)
    return full_project_dto(project)


@app.patch("/api/project/pages/{page_id}/features/{feature_id}")
def patch_feature(page_id: str, feature_id: str, body: FeaturePatchBody) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    page = project.pages.get(page_id)
    if page is None or feature_id not in page.features:
        raise HTTPException(404, "feature not found")
    feat = page.features[feature_id]
    if body.id is not None:
        try:
            feat = rename_page_feature(page, feature_id, body.id, project=project)
        except KeyError as exc:
            raise HTTPException(404, "feature not found") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    if body.label is not None:
        feat.label = body.label.strip() or feat.id
    if body.notes is not None:
        feat.notes = body.notes
    if body.recognize is True:
        page.recognize_with = feat.id
    elif body.recognize is False and page.recognize_with == feat.id:
        page.recognize_with = None
    rebuild_resource_index(project)
    save_project(project)
    return full_project_dto(project)


@app.delete("/api/project/pages/{page_id}/features/{feature_id}")
def remove_feature(page_id: str, feature_id: str) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    page = project.pages.get(page_id)
    if page is None:
        raise HTTPException(404, "page not found")
    if not delete_page_feature(page, feature_id):
        raise HTTPException(404, "feature not found")
    rebuild_resource_index(project)
    save_project(project)
    return full_project_dto(project)


@app.put("/api/project/pages/{page_id}/features/{feature_id}/bind")
def bind_feature_api(page_id: str, feature_id: str, body: FeatureBindBody) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    page = project.pages.get(page_id)
    if page is None:
        raise HTTPException(404, "page not found")
    try:
        bind_feature(
            page,
            feature_id,
            body.asset,
            search_roi=body.search_roi,
            content_roi=body.content_roi,
        )
    except KeyError as exc:
        raise HTTPException(404, "feature not found") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    rebuild_resource_index(project)
    save_project(project)
    return full_project_dto(project)


@app.put("/api/project/pages/{page_id}/features/{feature_id}/visual")
def select_feature_visual_api(
    page_id: str, feature_id: str, body: FeatureSelectVisualBody
) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    page = project.pages.get(page_id)
    if page is None:
        raise HTTPException(404, "page not found")
    try:
        select_feature_visual(page, feature_id, body.visual_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    rebuild_resource_index(project)
    save_project(project)
    return full_project_dto(project)


@app.delete("/api/project/pages/{page_id}/features/{feature_id}/bind")
def unbind_feature_api(page_id: str, feature_id: str) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    page = project.pages.get(page_id)
    if page is None:
        raise HTTPException(404, "page not found")
    try:
        unbind_feature(page, feature_id)
    except KeyError as exc:
        raise HTTPException(404, "feature not found") from exc
    rebuild_resource_index(project)
    save_project(project)
    return full_project_dto(project)


@app.post("/api/project/pages/{page_id}/visuals")
def create_visual(page_id: str, body: VisualCreateBody) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    page = project.pages.get(page_id)
    if page is None:
        raise HTTPException(404, "page not found")
    try:
        add_page_visual(
            page,
            template=body.template,
            label=body.label,
            visual_id=body.id,
            search_roi=body.search_roi,
            content_roi=body.content_roi,
            source_id=body.source_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    rebuild_resource_index(project)
    save_project(project)
    return full_project_dto(project)


@app.patch("/api/project/pages/{page_id}/visuals/{visual_id}")
def patch_visual(page_id: str, visual_id: str, body: VisualPatchBody) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    page = project.pages.get(page_id)
    if page is None:
        raise HTTPException(404, "page not found")
    kwargs: dict[str, Any] = {}
    if body.label is not None:
        kwargs["label"] = body.label
    if body.template is not None:
        kwargs["template"] = body.template
    if body.clear_search_roi:
        kwargs["search_roi"] = None
    elif body.search_roi is not None:
        kwargs["search_roi"] = body.search_roi
    if body.clear_content_roi:
        kwargs["content_roi"] = None
    elif body.content_roi is not None:
        kwargs["content_roi"] = body.content_roi
    if body.clear_source_id:
        kwargs["source_id"] = None
    elif body.source_id is not None:
        kwargs["source_id"] = body.source_id
    try:
        update_page_visual(page, visual_id, **kwargs)
    except KeyError as exc:
        raise HTTPException(404, "visual not found") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    rebuild_resource_index(project)
    save_project(project)
    return full_project_dto(project)


@app.delete("/api/project/pages/{page_id}/visuals/{visual_id}")
def remove_visual(page_id: str, visual_id: str) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    page = project.pages.get(page_id)
    if page is None:
        raise HTTPException(404, "page not found")
    if not delete_page_visual(page, visual_id):
        raise HTTPException(404, "visual not found")
    rebuild_resource_index(project)
    save_project(project)
    return full_project_dto(project)


@app.get("/api/file")
def get_file(relpath: str) -> FileResponse:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    try:
        path = resolve_under_root(project.root, relpath)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not path.is_file():
        raise HTTPException(404, "file not found")
    return FileResponse(path)


@app.post("/api/validate")
def validate_project() -> dict[str, Any]:
    _sync_ui_lang()
    issues = bridge.validate(_t)
    serialized = [{"level": i.level, "text": i.text} for i in issues]
    errors = [i for i in serialized if i["level"] == "error"]
    warnings = [i for i in serialized if i["level"] == "warning"]
    return {
        "issues": serialized,
        "errors": errors,
        "warnings": warnings,
        "ok": not errors,
        "has_warnings": bool(warnings),
    }


@app.post("/api/project/close")
def close_project() -> dict[str, str]:
    bridge.set_project(None)
    return {"status": "closed"}


@app.get("/api/templates")
def list_templates_api() -> dict[str, Any]:
    from studio_api.layer_templates import list_templates

    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    return {"templates": list_templates(project)}


@app.post("/api/templates")
def save_template_api(body: TemplateSaveBody) -> dict[str, Any]:
    from screenflow.project import _node_from_json
    from studio_api.layer_templates import save_template

    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "name required")
    roots = [_node_from_json(n) for n in body.tree]
    path = save_template(project, name, roots)
    return {"ok": True, "path": str(path), "name": path.stem}


@app.get("/api/templates/{name}")
def load_template_api(name: str) -> dict[str, Any]:
    from screenflow.project import _node_to_json
    from studio_api.layer_templates import load_template

    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    try:
        roots = load_template(project, name)
    except FileNotFoundError as exc:
        raise HTTPException(404, "template not found") from exc
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"tree": [_node_to_json(n) for n in roots]}


@app.post("/api/engine/start")
def engine_start(body: StartBody | None = None) -> dict[str, Any]:
    body = body or StartBody()
    _sync_ui_lang()
    issues = bridge.validate(_t)
    serialized = [{"level": i.level, "text": i.text} for i in issues]
    errors = [i for i in serialized if i["level"] == "error"]
    warnings = [i for i in serialized if i["level"] == "warning"]
    if errors:
        raise HTTPException(
            400,
            {
                "message": "Validation failed",
                "issues": serialized,
            },
        )
    if warnings and not body.allow_warnings:
        raise HTTPException(
            409,
            {
                "message": "Validation warnings",
                "issues": serialized,
                "warnings_only": True,
            },
        )
    try:
        bridge.start(persist=True, mode=body.mode)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    return bridge.snapshot()


@app.post("/api/engine/pause")
def engine_pause() -> dict[str, Any]:
    bridge.pause()
    return bridge.snapshot()


@app.post("/api/engine/resume")
def engine_resume() -> dict[str, Any]:
    bridge.resume()
    return bridge.snapshot()


@app.post("/api/engine/stop")
def engine_stop() -> dict[str, Any]:
    bridge.stop()
    return bridge.snapshot()


@app.get("/api/engine/status")
def engine_status() -> dict[str, Any]:
    return bridge.snapshot()


@app.patch("/api/engine/runtime")
def patch_runtime(body: RuntimeBody) -> dict[str, Any]:
    from studio_api.serialize import apply_full_project_dto

    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    dto = full_project_dto(project)
    dto["runtime"] = {**dto.get("runtime", {}), **body.runtime}
    apply_full_project_dto(project, dto)
    bridge.sync_runtime()
    return {"runtime": dto["runtime"]}


@app.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    queue: list[dict[str, Any]] = []

    def on_event(event: dict[str, Any]) -> None:
        queue.append(event)

    unsub = bridge.subscribe(on_event)
    try:
        await ws.send_json({"type": "hello", "snapshot": bridge.snapshot()})
        import asyncio

        while True:
            while queue:
                await ws.send_json(queue.pop(0))
            try:
                # Keep connection; allow client pings
                data = await asyncio.wait_for(ws.receive_text(), timeout=0.25)
                if data == "ping":
                    await ws.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        pass
    finally:
        unsub()


def mount_ui(static_dir: Path | None = None) -> None:
    """Serve built Vue app if present."""
    dist = static_dir or (Path(__file__).resolve().parent.parent / "web" / "dist")
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="ui")


def create_app(*, serve_ui: bool = False) -> FastAPI:
    if serve_ui:
        mount_ui()
    return app
