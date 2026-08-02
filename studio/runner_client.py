"""Studio-side controller for the external engine runner process."""

from __future__ import annotations

import os
import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal

from screenflow.runner_ipc import iter_messages, send_msg, serve_once
from screenflow.runner_protocol import (
    cmd_pause,
    cmd_ping,
    cmd_set_runtime,
    cmd_start,
    cmd_stop,
)
from studio.elevate import launch_runner


LogFn = Callable[[str], None]
StatusFn = Callable[[dict[str, Any]], None]


def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        # QUERY_LIMITED often works even across elevation for existence checks.
        process_query_limited = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(process_query_limited, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _terminate_pid(pid: int) -> None:
    """Best-effort; unelevated Studio may be denied killing an elevated Runner."""
    if pid <= 0:
        return
    if os.name == "nt":
        import ctypes

        process_terminate = 0x0001
        handle = ctypes.windll.kernel32.OpenProcess(process_terminate, False, pid)
        if not handle:
            return
        try:
            ctypes.windll.kernel32.TerminateProcess(handle, 1)
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
        return
    try:
        os.kill(pid, 15)
    except OSError:
        pass


class RunnerClient(QObject):
    """
    Listen on localhost, launch runner, forward log/status via Qt signals.
    """

    log_message = Signal(str)
    status_payload = Signal(object)
    failed = Signal(str)
    ready = Signal()
    exited = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
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
        """Bind, launch runner, block until ready or raise."""
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
            target=self._read_loop, name="runner-client-read", daemon=True
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
                    self.ready.emit()
                elif typ == "log":
                    self.log_message.emit(str(msg.get("text") or ""))
                elif typ == "status":
                    payload = {k: v for k, v in msg.items() if k != "type"}
                    self.status_payload.emit(payload)
                elif typ == "error":
                    self.failed.emit(str(msg.get("text") or "Runner error"))
                elif typ == "exited":
                    code = int(msg.get("code") or 0)
                    self.exited.emit(code)
                    break
                elif typ == "pong":
                    pass
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

    def send_ping(self) -> None:
        self._send(cmd_ping())

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
        # UAC / ShellExecute path: no Popen handle — use PID from ready event.
        pid = self._runner_pid
        if pid is None:
            return
        deadline = time.time() + 2.0
        while _pid_running(pid) and time.time() < deadline:
            time.sleep(0.05)
        if _pid_running(pid):
            _terminate_pid(pid)
            deadline = time.time() + 1.0
            while _pid_running(pid) and time.time() < deadline:
                time.sleep(0.05)
        self._runner_pid = None

    def stop_session(self, *, send_stop: bool = True) -> None:
        if send_stop and self._alive:
            self.send_stop()
            # Wait briefly for clean exit
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
        # Closing the socket also makes the Runner leave its read loop / finally.
        self._kill_proc()
        if self._listener is not None:
            try:
                self._listener.close()
            except OSError:
                pass
            self._listener = None
