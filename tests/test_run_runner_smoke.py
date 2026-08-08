"""Smoke: run_runner.py over TCP — ready → start → stop → exited."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import cv2
import numpy as np

from screenflow.models import PageDef, Project, RuntimeConfig, StateNode
from screenflow.project import save_project
from screenflow.runner_ipc import iter_messages, send_msg, serve_once
from screenflow.runner_protocol import cmd_start, cmd_stop

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_runner.py"


def _minimal_project(root: Path) -> None:
    page = PageDef(
        page_id="p",
        detect_relpath="pages/p/features/main.png",
        state_tree=[
            StateNode(
                id="else",
                name="Other",
                is_else=True,
                actions=[],
            )
        ],
    )
    det = root / "pages" / "p" / "features"
    det.mkdir(parents=True)
    cv2.imwrite(str(det / "main.png"), np.zeros((8, 8, 3), dtype=np.uint8))
    proj = Project(
        name="runner-smoke",
        root=root,
        runtime=RuntimeConfig(poll_interval=0.2),
        pages={"p": page},
        feature_files={},
    )
    save_project(proj)


def test_run_runner_ready_start_stop():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _minimal_project(root)
        listener, port = serve_once()
        listener.settimeout(20.0)

        proc = subprocess.Popen(
            [
                sys.executable,
                str(RUNNER),
                "--project",
                str(root),
                "--port",
                str(port),
            ],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            conn, _addr = listener.accept()
            listener.close()
            types: list[str] = []
            got_ready = threading.Event()

            def reader() -> None:
                try:
                    for msg in iter_messages(conn):
                        typ = str(msg.get("type") or "")
                        types.append(typ)
                        if typ == "ready":
                            got_ready.set()
                        if typ == "exited":
                            break
                except OSError:
                    pass

            t = threading.Thread(target=reader, daemon=True)
            t.start()
            assert got_ready.wait(15), f"no ready; types={types} stderr={proc.stderr.read() if proc.stderr else b''}"
            send_msg(conn, cmd_start())
            time.sleep(0.3)
            send_msg(conn, cmd_stop())
            t.join(10)
            proc.wait(timeout=15)
            assert "ready" in types
            assert "exited" in types
            assert proc.returncode == 0
        finally:
            if proc.poll() is None:
                proc.kill()
            try:
                listener.close()
            except OSError:
                pass
