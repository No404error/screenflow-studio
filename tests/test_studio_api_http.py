"""HTTP smoke tests for Web Studio API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from screenflow.project import new_blank_project
from studio_api.app import app
from studio_api.engine_bridge import bridge
from studio_api import lifecycle


def test_health_and_open_save(tmp_path: Path) -> None:
    bridge.stop()
    bridge._project = None
    bridge._engine = None

    client = TestClient(app)
    assert client.get("/api/health").json()["status"] == "ok"

    root = new_blank_project(tmp_path / "webproj", name="API Test")
    r = client.post("/api/project/open", json={"path": str(root)})
    assert r.status_code == 200
    dto = r.json()
    assert dto["name"] == "API Test"
    dto["vars"] = {"flag": True}
    dto["var_schema"] = {"flag": {"type": "bool", "description": "t"}}
    r2 = client.put("/api/project", json={"project": dto})
    assert r2.status_code == 200
    assert r2.json()["vars"]["flag"] is True

    r3 = client.post("/api/validate")
    assert r3.status_code == 200
    body = r3.json()
    assert body["ok"] is False  # no pages
    assert "errors" in body and "warnings" in body

    r4 = client.get("/api/templates")
    assert r4.status_code == 200
    assert r4.json()["templates"] == []

    r5 = client.post(
        "/api/templates",
        json={"name": "demo", "tree": [{"id": "c1", "name": "A", "score": {"kind": "constant", "constant": 1}}]},
    )
    assert r5.status_code == 200
    r6 = client.get("/api/templates/demo")
    assert r6.status_code == 200
    assert len(r6.json()["tree"]) == 1

    r7 = client.patch("/api/settings", json={"runner_mode": "inline"})
    assert r7.status_code == 200
    assert r7.json()["runner_mode"] == "inline"


def test_page_sources_upload_patch_and_delete(tmp_path: Path) -> None:
    import cv2
    import numpy as np

    bridge.stop()
    bridge._project = None
    bridge._engine = None
    client = TestClient(app)
    root = new_blank_project(tmp_path / "srcproj", name="Src")
    assert client.post("/api/project/open", json={"path": str(root)}).status_code == 200
    dto = client.post("/api/project/add-page", json={"name": "Home"}).json()
    page_id = list(dto["page_docs"].keys())[-1]
    png = tmp_path / "shot.png"
    cv2.imwrite(str(png), np.zeros((32, 32, 3), dtype=np.uint8))
    with png.open("rb") as f:
        r = client.post(
            f"/api/project/pages/{page_id}/sources",
            files={"file": ("shot.png", f, "image/png")},
            params={"label": "empty"},
        )
    assert r.status_code == 200
    sources = r.json()["page_docs"][page_id].get("sources") or {}
    assert len(sources) == 1
    sid = next(iter(sources))
    assert sources[sid]["label"] == "empty"
    r_patch = client.patch(
        f"/api/project/pages/{page_id}/sources/{sid}",
        json={"label": "renamed"},
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["page_docs"][page_id]["sources"][sid]["label"] == "renamed"

    # Second original appends
    png2 = tmp_path / "shot2.png"
    cv2.imwrite(str(png2), np.ones((32, 32, 3), dtype=np.uint8) * 40)
    with png2.open("rb") as f:
        r2 = client.post(
            f"/api/project/pages/{page_id}/sources",
            files={"file": ("shot2.png", f, "image/png")},
        )
    assert r2.status_code == 200
    assert len(r2.json()["page_docs"][page_id]["sources"]) == 2

    # Create visual on first source then delete source → cascade
    with png.open("rb") as f:
        up = client.post(
            f"/api/project/pages/{page_id}/assets",
            files={"file": ("crop.png", f, "image/png")},
        )
    assert up.status_code == 200
    created = client.post(
        f"/api/project/pages/{page_id}/visuals",
        json={
            "template": up.json()["relpath"],
            "label": "from-src",
            "source_id": sid,
            "content_roi": [0.1, 0.5, 0.1, 0.5],
        },
    )
    assert created.status_code == 200
    assert any(
        v.get("source_id") == sid
        for v in created.json()["page_docs"][page_id]["visuals"].values()
    )
    deleted = client.delete(f"/api/project/pages/{page_id}/sources/{sid}")
    assert deleted.status_code == 200
    page = deleted.json()["page_docs"][page_id]
    assert sid not in (page.get("sources") or {})
    assert not any(
        v.get("source_id") == sid for v in (page.get("visuals") or {}).values()
    )

    # Back-compat clear-all
    r_clear = client.delete(f"/api/project/pages/{page_id}/source")
    assert r_clear.status_code == 200
    assert not r_clear.json()["page_docs"][page_id].get("sources")


def test_visuals_crud_and_shared_select(tmp_path: Path) -> None:
    import cv2
    import numpy as np

    bridge.stop()
    bridge._project = None
    bridge._engine = None
    client = TestClient(app)
    root = new_blank_project(tmp_path / "visproj", name="Vis")
    assert client.post("/api/project/open", json={"path": str(root)}).status_code == 200
    dto = client.post("/api/project/add-page", json={"name": "Home"}).json()
    page_id = list(dto["page_docs"].keys())[-1]

    png = tmp_path / "mark.png"
    cv2.imwrite(str(png), np.zeros((16, 16, 3), dtype=np.uint8))
    with png.open("rb") as f:
        up = client.post(
            f"/api/project/pages/{page_id}/assets",
            files={"file": ("mark.png", f, "image/png")},
        )
    assert up.status_code == 200
    relpath = up.json()["relpath"]

    created = client.post(
        f"/api/project/pages/{page_id}/visuals",
        json={"template": relpath, "label": "shared", "search_roi": [0, 0, 10, 10]},
    )
    assert created.status_code == 200
    visuals = created.json()["page_docs"][page_id]["visuals"]
    assert len(visuals) == 1
    vid = next(iter(visuals))

    patched = client.patch(
        f"/api/project/pages/{page_id}/visuals/{vid}",
        json={"label": "shared-v2"},
    )
    assert patched.status_code == 200
    assert patched.json()["page_docs"][page_id]["visuals"][vid]["label"] == "shared-v2"

    client.post(f"/api/project/pages/{page_id}/features", json={"label": "A"})
    f2 = client.post(
        f"/api/project/pages/{page_id}/features",
        json={"label": "B"},
    ).json()
    feats = f2["page_docs"][page_id]["features"]
    ids = [fid for fid, f in feats.items() if f["label"] in ("A", "B")]
    assert len(ids) == 2
    a_id, b_id = ids[0], ids[1]

    s1 = client.put(
        f"/api/project/pages/{page_id}/features/{a_id}/visual",
        json={"visual_id": vid},
    )
    s2 = client.put(
        f"/api/project/pages/{page_id}/features/{b_id}/visual",
        json={"visual_id": vid},
    )
    assert s1.status_code == 200 and s2.status_code == 200
    page = s2.json()["page_docs"][page_id]
    assert page["features"][a_id]["visual_id"] == vid
    assert page["features"][b_id]["visual_id"] == vid

    deleted = client.delete(f"/api/project/pages/{page_id}/visuals/{vid}")
    assert deleted.status_code == 200
    page = deleted.json()["page_docs"][page_id]
    assert vid not in page["visuals"]
    assert page["features"][a_id].get("visual_id") in (None, "")
    assert page["features"][b_id].get("visual_id") in (None, "")


def test_remove_recent_http(tmp_path: Path, monkeypatch) -> None:
    from studio_api import settings as ui_settings

    monkeypatch.setattr(ui_settings, "config_dir", lambda: tmp_path / ".screenflow")
    monkeypatch.setattr(
        ui_settings, "legacy_settings_path", lambda: tmp_path / "missing.json"
    )
    a = tmp_path / "ra"
    b = tmp_path / "rb"
    a.mkdir()
    b.mkdir()
    ui_settings.touch_recent(a, "A")
    ui_settings.touch_recent(b, "B")
    client = TestClient(app)
    r = client.post("/api/settings/remove-recent", json={"path": str(a)})
    assert r.status_code == 200
    names = [e["name"] for e in r.json()["recent"]]
    assert names == ["B"]


def test_editor_state_and_shutdown_guard() -> None:
    lifecycle.reset_for_tests()
    bridge.stop()
    client = TestClient(app)

    assert client.get("/api/app/editor-state").json()["dirty"] is False
    assert client.put("/api/app/editor-state", json={"dirty": True}).json()["dirty"] is True
    blocked = client.post("/api/app/shutdown", json={"force": False})
    assert blocked.status_code == 409

    ok = client.post("/api/app/shutdown", json={"force": True})
    assert ok.status_code == 200
    assert ok.json()["ok"] is True
    again = client.post("/api/app/shutdown", json={"force": True})
    assert again.status_code == 200
    assert again.json()["status"] == "already"
    lifecycle.reset_for_tests()

