from __future__ import annotations

import threading
import time
from typing import Any, Callable

import numpy as np

from screenflow.actions import ActionRunner
from screenflow.decide import decide_page_state
from screenflow.input import InputController
from screenflow.logfmt import EngineLog
from screenflow.matcher import ScreenMatcher
from screenflow.models import (
    ActionStep,
    EngineStatus,
    MatchResult,
    Project,
    RuntimeConfig,
    StateNode,
    normalize_post_mode,
)
from screenflow.post import StickyPost, run_post_listen

LogFn = Callable[[str], None]
StatusFn = Callable[[dict[str, Any]], None]


class FlowEngine:
    """Page → state tree → main actions → post-processor loop."""

    def __init__(
        self,
        project: Project,
        log: LogFn | None = None,
        status: StatusFn | None = None,
    ) -> None:
        self.project = project
        self.runtime: RuntimeConfig = project.runtime
        self.elog = EngineLog(
            log,
            verbose=self.runtime.verbose_log,
            language=self.runtime.log_language,
        )
        self.matcher = ScreenMatcher(project)
        self.input = InputController(self.runtime, self.elog)
        self.actions = ActionRunner(
            project,
            self.matcher,
            self.input,
            self.elog,
            is_running=self._is_running,
        )
        self.status = EngineStatus.IDLE
        self._frame_id = 0
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._status_cb = status
        self._last_page_id: str | None = None
        self._last_state: str | None = None
        self._sticky: StickyPost | None = None
        self.vars: dict[str, Any] = dict(project.var_defaults)

    def _emit_status(
        self,
        mode: str,
        page_id: str | None = None,
        state: str | None = None,
        *,
        clear: bool = False,
    ) -> None:
        if clear:
            self._last_page_id = None
            self._last_state = None
        else:
            if page_id and page_id != "UNKNOWN":
                self._last_page_id = page_id
            elif page_id == "UNKNOWN" and mode == "running":
                self._last_page_id = None
                self._last_state = None
            if state is not None:
                self._last_state = state
        if not self._status_cb:
            return
        pid = self._last_page_id
        page = self.project.pages.get(pid) if pid else None
        page_label = page.display_name() if page else None
        self._status_cb(
            {
                "mode": mode,
                "page_id": pid,
                "page_label": page_label,
                "state": self._last_state,
            }
        )

    def log(self, msg: str) -> None:
        self.elog.info(msg)

    def _is_running(self) -> bool:
        with self._lock:
            return self.status == EngineStatus.RUNNING

    def sync_runtime(self) -> None:
        self.elog.verbose = self.runtime.verbose_log
        self.elog.language = self.runtime.log_language
        self.input.runtime = self.runtime
        self.matcher.runtime = self.runtime

    def click(self, x: int, y: int, *, force: bool = False) -> None:
        self.input.click(x, y, force=force)

    def expand_steps(
        self, steps: list[ActionStep], *, _depth: int = 0
    ) -> list[ActionStep]:
        return self.actions.expand_steps(steps, _depth=_depth)

    def run_steps(
        self,
        steps: list[ActionStep],
        screen: np.ndarray,
        ctx: dict[str, Any],
        *,
        page_id: str | None = None,
    ) -> bool:
        return self.actions.run_steps(
            steps, screen, ctx, page_id=page_id, vars=self.vars
        )

    def _arm_post(self, leaf: StateNode, page_id: str, main_path: str) -> None:
        post = leaf.post
        if post is None:
            page = self.project.pages.get(page_id)
            if page and page.default_post:
                post = page.default_post
        if post is None:
            return
        mode = normalize_post_mode(post.mode)
        # until_page may arm with an empty tree (page-change wait only).
        if not post.tree and mode != "until_page":
            return
        frames = post.frames if mode == "frames" else None
        self._sticky = StickyPost(
            page_id=page_id,
            listen=post,
            mode=mode,
            frames_left=frames,
            path_prefix=main_path,
            pending_settle=True,
        )
        self.elog.detail(
            f"  post armed mode={mode} settle={post.settle:g}s"
            + (" (empty tree)" if not post.tree else "")
        )

    def _dispatch_sticky_post(self, screen: np.ndarray) -> str | None:
        """Run active post-listen; return status path."""
        sticky = self._sticky
        assert sticky is not None
        if sticky.pending_settle:
            sticky.pending_settle = False
            delay = float(sticky.listen.settle or 0.0)
            if delay > 0:
                self.elog.detail(f"  post settle {delay:g}s")
                time.sleep(delay)
            # Recapture after main actions / settle so UI can appear
            frame = self.matcher.capture_screen()
        else:
            frame = screen
        # Light path: assume still on the armed page; full scan only if not.
        pr = self.matcher.detect_page(frame, prefer=sticky.page_id)
        if pr.page_id != sticky.page_id:
            pr = self.matcher.detect_page(frame, force_full=True)
        outcome = run_post_listen(
            self.project,
            self.matcher,
            self,
            sticky,
            frame,
            current_page_id=pr.page_id,
        )
        reason = str((outcome.detail or {}).get("reason") or "")
        if outcome.skipped:
            # Sticky post owns the loop — main state tree is not evaluated.
            if reason == "until_page_wait":
                self.elog.info(
                    f"{outcome.short_path or 'post'}: waiting for another page"
                )
            elif reason == "no_match_skip":
                self.elog.info(
                    f"{outcome.short_path or 'post'}: no follow-up case — keep waiting"
                )
            elif reason == "unknown_skip":
                self.elog.detail("  post: unrecognized page — skip frame")
            else:
                self.elog.detail(f"  post: skip ({reason or 'unknown'})")
            return self._last_state
        if outcome.short_path:
            self.elog.info(outcome.short_path)
        if self.elog.verbose and outcome.detail:
            self.elog.detail(f"  post detail: {outcome.detail}")
        if outcome.ended:
            self._sticky = None
            if reason:
                self.elog.detail(f"  post ended: {reason}")
        return outcome.short_path or self._last_state

    def dispatch(self, screen: np.ndarray, page_result: MatchResult) -> str | None:
        """Returns short path string for status, or None."""
        # Sticky post first
        if self._sticky is not None:
            return self._dispatch_sticky_post(screen)

        if page_result.page_id == "UNKNOWN":
            self.elog.info(
                f"Unknown screen ({page_result.confidence:.2f}) — wait"
            )
            return None

        page_def = self.project.pages.get(page_result.page_id)
        if page_def is None:
            self.elog.info(
                f"Page id {page_result.page_id!r} missing from project — wait"
            )
            return None

        page_label = self.elog.page_label(self.project, page_result.page_id)
        result = decide_page_state(
            self.project, page_def, screen, self.matcher, vars=self.vars
        )
        if self.elog.verbose:
            for i, layer in enumerate(result.detail.get("layers") or []):
                self.elog.detail(f"  layer {i}: {layer}")

        if result.leaf is None:
            self.elog.info(f"{page_label}: no matching state — wait")
            return None

        short = f"{page_label} › {result.short_path()}"
        self.elog.info(short)

        self.actions.run_steps(
            result.leaf.actions,
            screen,
            {},
            page_id=page_def.page_id,
            vars=self.vars,
        )
        # Arm post, then first listen frame (settle → capture) for all modes
        self._arm_post(result.leaf, page_def.page_id, short)
        if self._sticky is not None:
            path = self._dispatch_sticky_post(screen)
            if path:
                short = path
        return short

    def _loop(self) -> None:
        while True:
            with self._lock:
                if self.status == EngineStatus.STOPPED:
                    break
                running = self.status == EngineStatus.RUNNING
                paused = self.status == EngineStatus.PAUSED

            if paused:
                # Status bar keeps last page/state from pause(); no capture/log.
                time.sleep(self.runtime.poll_interval)
                continue

            t0 = time.perf_counter()
            capture_ms = match_ms = decide_ms = 0.0
            try:
                self._frame_id += 1
                t = time.perf_counter()
                screen = self.matcher.capture_screen()
                capture_ms = (time.perf_counter() - t) * 1000.0

                t = time.perf_counter()
                page_result = self.matcher.detect_page(screen)
                match_ms = (time.perf_counter() - t) * 1000.0

                self.elog.frame(
                    self.project,
                    self._frame_id,
                    page_result,
                    paused=False,
                )
                state_name: str | None = None
                if running and self._is_running():
                    t = time.perf_counter()
                    state_name = self.dispatch(screen, page_result)
                    decide_ms = (time.perf_counter() - t) * 1000.0
                # Re-read status: pause/stop during this frame must not emit stale "running".
                with self._lock:
                    cur = self.status
                if cur == EngineStatus.PAUSED:
                    self._emit_status(
                        "paused",
                        page_id=page_result.page_id,
                        state=state_name or self._last_state,
                    )
                elif cur == EngineStatus.RUNNING:
                    self._emit_status(
                        "running",
                        page_id=page_result.page_id,
                        state=state_name if state_name is not None else self._last_state,
                    )
            except Exception as exc:
                self.elog.info(f"Error: {exc} (continue)")
                self.elog.detail(f"  {type(exc).__name__}: {exc!r}")

            # Adaptive poll: only sleep the remainder of poll_interval.
            elapsed = time.perf_counter() - t0
            remain = float(self.runtime.poll_interval) - elapsed
            sleep_ms = 0.0
            if remain > 0:
                time.sleep(remain)
                sleep_ms = remain * 1000.0
            if self.elog.verbose:
                self.elog.detail(
                    "  timing "
                    f"capture={capture_ms:.0f} match={match_ms:.0f} "
                    f"decide={decide_ms:.0f} sleep={sleep_ms:.0f} ms"
                )

    def start(self) -> None:
        with self._lock:
            resuming = self.status == EngineStatus.PAUSED
            need_thread = self._thread is None or not self._thread.is_alive()
            self.status = EngineStatus.RUNNING
        if not resuming:
            self.sync_runtime()
            self.vars = dict(self.project.var_defaults)
            self._sticky = None
            self.matcher.clear_page_sticky()
        self.elog.status("RUNNING")
        if not resuming:
            self.elog.detail(
                f"  verbose={self.elog.verbose} threshold={self.runtime.match_threshold}"
            )
        self._emit_status("running")
        if need_thread:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def pause(self) -> None:
        with self._lock:
            if self.status == EngineStatus.STOPPED:
                return
            self.status = EngineStatus.PAUSED
        self.elog.status("PAUSED")
        self._emit_status("paused")

    def stop(self) -> None:
        with self._lock:
            if self.status == EngineStatus.STOPPED:
                return
            self.status = EngineStatus.STOPPED
        self._sticky = None
        self.matcher.clear_page_sticky()
        self.elog.status("STOPPED")
        self._emit_status("stopped", clear=True)
