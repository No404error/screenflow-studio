"""RunnerClient session without UAC (elevate=False)."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtWidgets import QApplication

from screenflow.models import PageDef, Project, RuntimeConfig, StateNode
from screenflow.project import save_project
from studio.runner_client import RunnerClient


def _proj(root: Path) -> None:
    det = root / "pages" / "p" / "features"
    det.mkdir(parents=True)
    cv2.imwrite(str(det / "main.png"), np.zeros((8, 8, 3), dtype=np.uint8))
    page = PageDef(
        page_id="p",
        detect_relpath="pages/p/features/main.png",
        state_tree=[StateNode(id="e", name="Other", is_else=True)],
    )
    save_project(
        Project(
            name="c",
            root=root,
            runtime=RuntimeConfig(poll_interval=0.25),
            pages={"p": page},
            feature_files={},
        )
    )


def test_runner_client_start_stop():
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _proj(root)
        client = RunnerClient()
        logs: list[str] = []
        statuses: list[dict] = []
        client.log_message.connect(logs.append)
        client.status_payload.connect(lambda p: statuses.append(p))
        client.start_session(root, elevate=False, ready_timeout=30)
        assert client.is_ready
        client.send_start()
        deadline = time.time() + 5
        while time.time() < deadline and not any(
            s.get("mode") == "running" for s in statuses
        ):
            app.processEvents()
            time.sleep(0.05)
        client.send_stop()
        deadline = time.time() + 5
        while time.time() < deadline and client.is_alive:
            app.processEvents()
            time.sleep(0.05)
        client.stop_session(send_stop=False)
        assert any(s.get("mode") == "running" for s in statuses) or logs
