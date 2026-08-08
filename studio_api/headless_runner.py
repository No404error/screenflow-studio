"""Qt-free runner client for Web Studio API (elevate / subprocess)."""

from __future__ import annotations

import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable

from screenflow.runner_ipc import iter_messages, send_msg, serve_once
from screenflow.runner_protocol import (
    cmd_pause,
    cmd_ping,
    cmd_set_runtime,
    cmd_start,
    cmd_stop,
)
from screenflow.elevate import launch_runner
from screenflow.process_util import pid_running, terminate_pid

LogFn = Callable[[str], None]
StatusFn = Callable[[dict[str, Any]], None]


class HeadlessRunnerClient:
    def __init__(
        self,
        *,
        on_log: LogFn | None = None,
        on_status: StatusFn | None = None,
    ) -> None:
        self._on_log = on_log
        self._on_status = on_status
        self._proc: subprocess.Popen | None = None
        self._runner_pid: int | None = None
        self._sock: socket.socket | None = None
        self._listener: socket.socket | None = None
        self._write_lock = threading.Lock()
        self._alive = False
        self._ready = False
        self._reader: threading.Thread | None = None

    @property
    def is_alive(self) -> bool:
        return self._alive and self._sock is not None

    @property
    def is_ready(self) -> bool:
        return self._ready

    def start_session(
        self,
        project_root: Path,
        *,
        elevate: bool = True,
        ready_timeout: float = 60.0,
    ) -> None:
        self.stop_session(send_stop=False)
        listener, port = serve_once()
        self._listener = listener
        listener.settimeout(ready_timeout)
        try:
            self._proc = launch_runner(
                project=project_root,
                host="127.0.0.1",
                port=port,
                elevate=elevate,
            )
        except OSError as exc:
            listener.close()
            self._listener = None
            raise RuntimeError(str(exc)) from exc

        try:
            conn, _ = listener.accept()
        except (TimeoutError, socket.timeout, OSError) as exc:
            listener.close()
            self._listener = None
            self._kill_proc()
            raise RuntimeError(
                "Timed out waiting for engine runner (UAC cancelled or launch failed)."
            ) from exc
        finally:
            try:
                listener.close()
            except OSError:
                pass
            self._listener = None

        self._sock = conn
        self._alive = True
        self._ready = False
        self._reader = threading.Thread(
            target=self._read_loop, name="web-runner-read", daemon=True
        )
        self._reader.start()

        deadline = time.time() + ready_timeout
        while time.time() < deadline:
            if self._ready:
                return
            if not self._alive:
                raise RuntimeError("Engine runner disconnected before ready.")
            time.sleep(0.05)
        self.stop_session(send_stop=True)
        raise RuntimeError("Engine runner did not become ready in time.")

    def _read_loop(self) -> None:
        sock = self._sock
        if sock is None:
            return
        try:
            for msg in iter_messages(sock):
                typ = msg.get("type")
                if typ == "ready":
                    pid = msg.get("pid")
                    if isinstance(pid, int) and pid > 0:
                        self._runner_pid = pid
                    self._ready = True
                elif typ == "log":
                    if self._on_log:
                        self._on_log(str(msg.get("text") or ""))
                elif typ == "status":
                    payload = {k: v for k, v in msg.items() if k != "type"}
                    if self._on_status:
                        self._on_status(payload)
                elif typ in ("error", "exited"):
                    break
        except OSError:
            pass
        finally:
            self._alive = False
            self._ready = False

    def _send(self, obj: dict[str, Any]) -> None:
        sock = self._sock
        if not sock or not self._alive:
            return
        with self._write_lock:
            try:
                send_msg(sock, obj)
            except OSError:
                self._alive = False

    def send_start(self) -> None:
        self._send(cmd_start())

    def send_pause(self) -> None:
        self._send(cmd_pause())

    def send_stop(self) -> None:
        self._send(cmd_stop())

    def send_set_runtime(self, fields: dict[str, Any]) -> None:
        self._send(cmd_set_runtime(fields))

    def _kill_proc(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is not None:
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            except Exception:
                pass
            return
        pid = self._runner_pid
        if pid is None:
            return
        deadline = time.time() + 2.0
        while pid_running(pid) and time.time() < deadline:
            time.sleep(0.05)
        if pid_running(pid):
            terminate_pid(pid)
        self._runner_pid = None

    def stop_session(self, *, send_stop: bool = True) -> None:
        if send_stop and self._alive:
            self.send_stop()
            deadline = time.time() + 3.0
            while self._alive and time.time() < deadline:
                time.sleep(0.05)
        sock = self._sock
        self._sock = None
        self._alive = False
        self._ready = False
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        self._kill_proc()
