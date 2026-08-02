# -*- coding: utf-8 -*-
"""Elevated (or plain) engine runner — controlled by Studio over localhost TCP."""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path

# Detach any console allocated by python.exe (pythonw has none).
if os.name == "nt":
    try:
        import ctypes

        ctypes.windll.kernel32.FreeConsole()
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from screenflow.engine import FlowEngine  # noqa: E402
from screenflow.models import RuntimeConfig  # noqa: E402
from screenflow.project import load_project  # noqa: E402
from screenflow.runner_ipc import connect_client, send_msg  # noqa: E402
from screenflow.runner_protocol import (  # noqa: E402
    event_error,
    event_exited,
    event_log,
    event_pong,
    event_ready,
    event_status,
    is_command,
)


def _apply_runtime_fields(rt: RuntimeConfig, fields: dict) -> None:
    for key, val in fields.items():
        if hasattr(rt, key):
            setattr(rt, key, val)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ScreenFlow engine runner")
    parser.add_argument("--project", required=True, help="Project folder path")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args(argv)

    root = Path(args.project).resolve()
    exit_code = 0
    sock = None
    engine: FlowEngine | None = None
    stop_event = threading.Event()

    try:
        sock = connect_client(args.host, args.port, timeout=30.0)
    except OSError as exc:
        print(f"runner: connect failed: {exc}", file=sys.stderr)
        return 2

    write_lock = threading.Lock()

    def emit(obj: dict) -> None:
        with write_lock:
            try:
                send_msg(sock, obj)
            except OSError:
                stop_event.set()

    try:
        project = load_project(root)
    except Exception as exc:
        emit(event_error(f"Failed to load project: {exc}"))
        emit(event_exited(1))
        sock.close()
        return 1

    def on_log(msg: str) -> None:
        emit(event_log(msg))

    def on_status(payload: dict) -> None:
        emit(event_status(payload))

    try:
        engine = FlowEngine(project, log=on_log, status=on_status)
    except Exception as exc:
        emit(event_error(f"Failed to init engine: {exc}"))
        emit(event_exited(1))
        sock.close()
        return 1
    emit(event_ready(os.getpid()))

    try:
        from screenflow.runner_ipc import iter_messages

        for msg in iter_messages(sock):
            if stop_event.is_set():
                break
            if not is_command(msg):
                continue
            cmd = msg.get("cmd")
            if cmd == "ping":
                emit(event_pong())
            elif cmd == "start":
                try:
                    engine.start()
                except Exception as exc:
                    emit(event_error(str(exc)))
            elif cmd == "pause":
                engine.pause()
            elif cmd == "stop":
                engine.stop()
                break
            elif cmd == "set_runtime":
                fields = msg.get("runtime")
                if isinstance(fields, dict):
                    _apply_runtime_fields(engine.runtime, fields)
                    project.runtime = engine.runtime
                    engine.sync_runtime()
                    emit(event_log("Runtime settings applied"))
    except Exception as exc:
        emit(event_error(str(exc)))
        exit_code = 1
    finally:
        if engine is not None:
            try:
                engine.stop()
            except Exception:
                pass
            # Give the loop thread a moment to notice STOPPED
            time.sleep(0.05)
        try:
            emit(event_exited(exit_code))
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
