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
    delete_page_asset,
    ensure_page_asset_dirs,
    list_page_assets,
    sync_page_asset_maps,
    upload_page_asset,
)
from screenflow.project import (
    load_project,
    new_blank_project,
    save_project,
    slugify_id,
)
from screenflow.models import PageDef
from studio import settings as ui_settings
from studio.i18n import I18n

from studio_api.engine_bridge import bridge
from studio_api.serialize import (
    apply_full_project_dto,
    full_project_dto,
    resolve_under_root,
)

app = FastAPI(title="ScreenFlow Web Studio API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_i18n = I18n(lang="en")


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


class RoiBody(BaseModel):
    roi: list[float] | None = None


class LangBody(BaseModel):
    lang: str = "en"


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
    return {
        "lang": data.get("lang") or "en",
        "recent": ui_settings.get_recent(),
        "runner_mode": data.get("runner_mode") or ui_settings.RUNNER_INLINE,
        "reopen_last_project": bool(data.get("reopen_last_project", True)),
    }


@app.post("/api/settings/lang")
def set_lang(body: LangBody) -> dict[str, str]:
    lang = body.lang if body.lang in ("en", "zh") else "en"
    ui_settings.update_ui_settings(lang=lang)
    _i18n.lang = lang
    return {"lang": lang}


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
        detect_relpath=f"pages/{pid}/features/main.png",
        name=body.name.strip() or pid,
    )
    project.pages[pid] = page
    ensure_page_asset_dirs(project, pid)
    sync_page_asset_maps(project, page)
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
        {"name": a.name, "relpath": a.relpath, "roi": a.roi}
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
        # If no detect yet, use first upload as detect
        page = project.pages[page_id]
        detect_path = Path(project.root) / page.detect_relpath
        if not detect_path.is_file():
            page.detect_relpath = asset.relpath
        sync_page_asset_maps(project, page)
        save_project(project)
    finally:
        tmp_path.unlink(missing_ok=True)
    return {"name": asset.name, "relpath": asset.relpath, "roi": asset.roi}


@app.delete("/api/project/pages/{page_id}/assets/{name}")
def remove_asset(page_id: str, name: str) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    try:
        delete_page_asset(project, page_id, name)
        save_project(project)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return full_project_dto(project)


@app.put("/api/project/pages/{page_id}/assets/{name}/roi")
def set_asset_roi(page_id: str, name: str, body: RoiBody) -> dict[str, Any]:
    project = bridge.project
    if project is None:
        raise HTTPException(404, "No project open")
    page = project.pages.get(page_id)
    if page is None:
        raise HTTPException(404, "page not found")
    if body.roi is None:
        page.feature_rois.pop(name, None)
        if Path(page.detect_relpath).stem == name:
            page.detect_roi = None
    else:
        page.feature_rois[name] = list(body.roi)
        if Path(page.detect_relpath).stem == name:
            page.detect_roi = list(body.roi)
    sync_page_asset_maps(project, page)
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
    issues = bridge.validate(_t)
    return {
        "issues": [{"level": i.level, "text": i.text} for i in issues],
        "ok": not any(i.level == "error" for i in issues),
    }


@app.post("/api/engine/start")
def engine_start() -> dict[str, Any]:
    issues = bridge.validate(_t)
    errors = [i for i in issues if i.level == "error"]
    if errors:
        raise HTTPException(
            400,
            {
                "message": "Validation failed",
                "issues": [{"level": i.level, "text": i.text} for i in issues],
            },
        )
    try:
        bridge.start(persist=True)
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
