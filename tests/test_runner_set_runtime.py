"""set_runtime command updates runner engine poll interval."""

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
from screenflow.runner_protocol import cmd_set_runtime, cmd_start, cmd_stop

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_runner.py"


def test_set_runtime_acks_in_log():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        det = root / "pages" / "p" / "detect"
        det.mkdir(parents=True)
        cv2.imwrite(str(det / "main.png"), np.zeros((8, 8, 3), dtype=np.uint8))
        save_project(
            Project(
                name="rt",
                root=root,
                runtime=RuntimeConfig(poll_interval=0.5),
                pages={
                    "p": PageDef(
                        page_id="p",
                        detect_relpath="pages/p/detect/main.png",
                        state_tree=[StateNode(id="e", name="O", is_else=True)],
                    )
                },
                detect_files={},
                click_files={},
            )
        )
        listener, port = serve_once()
        listener.settimeout(20.0)
        proc = subprocess.Popen(
            [sys.executable, str(RUNNER), "--project", str(root), "--port", str(port)],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            conn, _ = listener.accept()
            listener.close()
            logs: list[str] = []
            ready = threading.Event()

            def reader() -> None:
                for msg in iter_messages(conn):
                    if msg.get("type") == "ready":
                        ready.set()
                    if msg.get("type") == "log":
                        logs.append(str(msg.get("text") or ""))
                    if msg.get("type") == "exited":
                        break

            t = threading.Thread(target=reader, daemon=True)
            t.start()
            assert ready.wait(15)
            send_msg(conn, cmd_start())
            send_msg(
                conn,
                cmd_set_runtime({"poll_interval": 0.2, "verbose_log": True}),
            )
            deadline = time.time() + 5
            while time.time() < deadline and not any("Runtime" in x for x in logs):
                time.sleep(0.05)
            send_msg(conn, cmd_stop())
            t.join(10)
            proc.wait(timeout=10)
            assert any("Runtime" in x for x in logs)
        finally:
            if proc.poll() is None:
                proc.kill()
