"""Engine session for Web Studio: inline FlowEngine or elevated Runner."""

from __future__ import annotations

import os
import threading
from collections import deque
from typing import Any, Callable

from screenflow.engine import FlowEngine
from screenflow.models import EngineStatus, Project
from screenflow.project import load_project, rebuild_resource_index, save_project
from screenflow.validate import Issue, validate_for_start
from studio_api import settings as ui_settings
from studio_api.headless_runner import HeadlessRunnerClient

LogFn = Callable[[str], None]


class EngineBridge:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._engine: FlowEngine | None = None
        self._runner: HeadlessRunnerClient | None = None
        self._project: Project | None = None
        self._logs: deque[str] = deque(maxlen=500)
        self._status: dict[str, Any] = {"mode": "idle"}
        self._listeners: list[Callable[[dict[str, Any]], None]] = []
        self._mode = self._default_mode()

    def _default_mode(self) -> str:
        # Windows → elevate; non-Windows → inline (see studio_api.settings).
        return ui_settings.get_runner_mode()

    @property
    def project(self) -> Project | None:
        return self._project

    @property
    def runner_mode(self) -> str:
        return self._mode

    def set_runner_mode(self, mode: str) -> None:
        m = (mode or "").strip().lower()
        if m not in (ui_settings.RUNNER_ELEVATE, ui_settings.RUNNER_INLINE):
            raise ValueError("runner_mode must be elevate or inline")
        self._mode = m
        ui_settings.update_ui_settings(runner_mode=m)

    def set_project(self, project: Project | None) -> None:
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
            "runner_mode": self._mode,
        }

    def is_active(self) -> bool:
        if self._runner and self._runner.is_alive:
            mode = (self._status.get("mode") or "").lower()
            return mode in ("running", "paused", "waiting_admin")
        eng = self._engine
        if eng is None:
            return False
        return eng.status in (EngineStatus.RUNNING, EngineStatus.PAUSED)

    def validate(self, t) -> list[Issue]:
        if self._project is None:
            return [Issue("error", "No project open")]
        return validate_for_start(self._project, t)

    def start(self, *, persist: bool = True, mode: str | None = None) -> None:
        if self._project is None:
            raise RuntimeError("No project open")
        if mode:
            self.set_runner_mode(mode)
        rebuild_resource_index(self._project)
        if persist:
            save_project(self._project)
            self._project = load_project(self._project.root)

        with self._lock:
            self.stop_unlocked()
            if self._mode == ui_settings.RUNNER_ELEVATE:
                self._status = {"mode": "waiting_admin"}
                self._broadcast({"type": "status", "payload": self._status})
                runner = HeadlessRunnerClient(
                    on_log=self._on_log,
                    on_status=self._on_status,
                )
                self._runner = runner
                try:
                    runner.start_session(self._project.root, elevate=True)
                except Exception:
                    self._runner = None
                    self._status = {"mode": "idle", "vars": {}}
                    self._broadcast({"type": "status", "payload": self._status})
                    raise
                runner.send_start()
            else:
                eng = FlowEngine(
                    self._project,
                    log=self._on_log,
                    status=self._on_status,
                )
                self._engine = eng
                eng.start()

    def pause(self) -> None:
        if self._runner and self._runner.is_alive:
            self._runner.send_pause()
        elif self._engine:
            self._engine.pause()

    def resume(self) -> None:
        if self._runner and self._runner.is_alive:
            self._runner.send_start()
        elif self._engine:
            self._engine.start()

    def stop(self) -> None:
        with self._lock:
            self.stop_unlocked()

    def stop_unlocked(self) -> None:
        if self._runner is not None:
            try:
                self._runner.stop_session(send_stop=True)
            except Exception:
                pass
            self._runner = None
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                pass
            self._engine = None
        self._status = {"mode": "idle", "vars": {}}
        self._broadcast({"type": "status", "payload": self._status})

    def sync_runtime(self) -> None:
        if not self._project:
            return
        rt = self._project.runtime
        fields = {
            "match_threshold": rt.match_threshold,
            "poll_interval": rt.poll_interval,
            "action_delay": rt.action_delay,
            "action_cooldown": rt.action_cooldown,
            "state_conf_margin": rt.state_conf_margin,
            "state_near": rt.state_near,
            "page_pair_margin": rt.page_pair_margin,
            "page_detect_near": rt.page_detect_near,
            "ref_width": rt.ref_width,
            "ref_height": rt.ref_height,
            "verbose_log": rt.verbose_log,
            "allow_redecide_during_action": rt.allow_redecide_during_action,
            "log_language": rt.log_language,
        }
        if self._runner and self._runner.is_alive:
            self._runner.send_set_runtime(fields)
        if self._engine:
            self._engine.runtime = rt
            self._engine.sync_runtime()


bridge = EngineBridge()
