"""HTTP smoke tests for Web Studio API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from screenflow.project import new_blank_project
from studio_api.app import app
from studio_api.engine_bridge import bridge


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
