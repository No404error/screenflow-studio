"""Inline engine session for Web Studio (default runner mode)."""

from __future__ import annotations

import threading
from collections import deque
from typing import Any, Callable

from screenflow.engine import FlowEngine
from screenflow.models import EngineStatus, Project
from screenflow.project import load_project, rebuild_resource_index, save_project
from screenflow.validate import Issue, validate_for_start


class EngineBridge:
    """Owns an optional FlowEngine and fans out log/status to subscribers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._engine: FlowEngine | None = None
        self._project: Project | None = None
        self._logs: deque[str] = deque(maxlen=500)
        self._status: dict[str, Any] = {"mode": "idle"}
        self._listeners: list[Callable[[dict[str, Any]], None]] = []

    @property
    def project(self) -> Project | None:
        return self._project

    def set_project(self, project: Project) -> None:
        with self._lock:
            self.stop_unlocked()
            self._project = project

    def subscribe(self, cb: Callable[[dict[str, Any]], None]) -> Callable[[], None]:
        self._listeners.append(cb)

        def _unsub() -> None:
            if cb in self._listeners:
                self._listeners.remove(cb)

        return _unsub

    def _broadcast(self, event: dict[str, Any]) -> None:
        for cb in list(self._listeners):
            try:
                cb(event)
            except Exception:
                pass

    def _on_log(self, msg: str) -> None:
        self._logs.append(msg)
        self._broadcast({"type": "log", "message": msg})

    def _on_status(self, payload: dict[str, Any]) -> None:
        self._status = dict(payload)
        self._broadcast({"type": "status", "payload": self._status})

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": dict(self._status),
            "logs": list(self._logs),
            "running": self.is_active(),
        }

    def is_active(self) -> bool:
        eng = self._engine
        if eng is None:
            return False
        return eng.status in (EngineStatus.RUNNING, EngineStatus.PAUSED)

    def validate(self, t) -> list[Issue]:
        if self._project is None:
            return [Issue("error", "No project open")]
        return validate_for_start(self._project, t)

    def start(self, *, persist: bool = True) -> None:
        if self._project is None:
            raise RuntimeError("No project open")
        rebuild_resource_index(self._project)
        if persist:
            save_project(self._project)
            # Reload from disk so matcher sees latest assets
            self._project = load_project(self._project.root)
        with self._lock:
            self.stop_unlocked()
            eng = FlowEngine(
                self._project,
                log=self._on_log,
                status=self._on_status,
            )
            self._engine = eng
            eng.start()

    def pause(self) -> None:
        if self._engine:
            self._engine.pause()

    def resume(self) -> None:
        if self._engine:
            self._engine.start()

    def stop(self) -> None:
        with self._lock:
            self.stop_unlocked()

    def stop_unlocked(self) -> None:
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                pass
            self._engine = None
        self._status = {"mode": "idle", "vars": {}}
        self._broadcast({"type": "status", "payload": self._status})

    def sync_runtime(self) -> None:
        if self._engine and self._project:
            self._engine.runtime = self._project.runtime
            self._engine.sync_runtime()


bridge = EngineBridge()
