from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np

from screenflow.assets import scoped_asset_key
from screenflow.input import InputController
from screenflow.logfmt import EngineLog
from screenflow.matcher import ScreenMatcher
from screenflow.models import ActionStep, Project


class ActionRunner:
    """Expand macros and run action step packs."""

    def __init__(
        self,
        project: Project,
        matcher: ScreenMatcher,
        input_ctrl: InputController,
        log: EngineLog,
        is_running: Callable[[], bool],
    ) -> None:
        self.project = project
        self.matcher = matcher
        self.input = input_ctrl
        self.log = log
        self._is_running = is_running

    def expand_steps(
        self, steps: list[ActionStep], *, _depth: int = 0
    ) -> list[ActionStep]:
        if _depth > 8:
            self.log.info("Action: macro nesting too deep — stop expanding")
            return []
        out: list[ActionStep] = []
        for step in steps:
            if step.op != "macro":
                out.append(step)
                continue
            mid = str(step.target or "")
            macro = self.project.macros.get(mid)
            if macro is None:
                self.log.info(
                    f"Action: unknown macro {self.log.macro_label(self.project, mid)}"
                )
                continue
            label = self.log.macro_label(self.project, mid)
            self.log.detail(f"  expand macro {label} ({len(macro.steps)} steps)")
            out.extend(self.expand_steps(macro.steps, _depth=_depth + 1))
        return out

    def _step_label(self, step: ActionStep) -> str:
        if step.op == "macro":
            return f"macro {self.log.macro_label(self.project, str(step.target or ''))}"
        if step.op == "click":
            return f"click {step.target!r}"
        if step.op == "key":
            return f"key {step.target!r}"
        if step.op == "hold_key":
            return f"hold_key {step.target!r} {step.hold!r}s"
        if step.op == "wait":
            return f"wait {step.target!r}"
        if step.op in ("set_var", "clear_var"):
            return f"{step.op} {step.target!r}"
        return f"{step.op} {step.target!r}"

    def run_steps(
        self,
        steps: list[ActionStep],
        screen: np.ndarray,
        ctx: dict[str, Any],
        *,
        page_id: str | None = None,
        vars: dict[str, Any] | None = None,
    ) -> bool:
        """Run an action pack. Returns False if aborted."""
        flat = self.expand_steps(steps)
        if not flat:
            self.log.info("Action: empty pack → next loop")
            return True

        if self.log.verbose and len(flat) != len(steps):
            self.log.detail(
                "  flat steps: " + ", ".join(self._step_label(s) for s in flat)
            )

        frame = ctx.get("after", screen)
        for i, step in enumerate(flat):
            if not self._is_running():
                self.log.info("Action: paused/stopped — abort pack")
                return False

            self.log.info(f"Action [{i + 1}/{len(flat)}] {self._step_label(step)}")
            if step.reason:
                self.log.detail(f"  note: {step.reason}")

            if step.op == "click":
                assert isinstance(step.target, str)
                click_key = (
                    scoped_asset_key(page_id, step.target)
                    if page_id
                    else step.target
                )
                pos = self.matcher.find_click_target(frame, click_key)
                if pos is None and click_key != step.target:
                    pos = self.matcher.find_click_target(frame, step.target)
                if pos is None:
                    self.log.detail("  click miss — recapture")
                    frame = self.matcher.capture_screen()
                    pos = self.matcher.find_click_target(frame, click_key)
                    if pos is None and click_key != step.target:
                        pos = self.matcher.find_click_target(frame, step.target)
                if pos is None:
                    self.log.info(f"Action: click target not found: {step.target}")
                    return False
                self.log.detail(f"  at {pos}")
                self.input.click(*pos, force=True)
                frame = self.matcher.capture_screen()
            elif step.op == "key":
                assert isinstance(step.target, str)
                self.input.tap_key(step.target)
            elif step.op == "hold_key":
                key = str(step.target or "space")
                seconds = float(step.hold if step.hold is not None else 1.0)
                self.input.hold_key(key, seconds)
            elif step.op == "wait":
                time.sleep(float(step.target or 0))
            elif step.op == "set_var" and vars is not None:
                # target: "name=value" or reason holds value
                raw = str(step.target or "")
                if "=" in raw:
                    k, v = raw.split("=", 1)
                    vars[k.strip()] = _parse_var(v.strip())
                else:
                    vars[raw] = True
                self.log.detail(f"  vars[{raw}]")
            elif step.op == "clear_var" and vars is not None:
                vars.pop(str(step.target or ""), None)
            elif step.op == "script":
                ok = self._run_script(str(step.target or ""), page_id=page_id, vars=vars)
                if not ok:
                    return False
            else:
                if step.op not in ("set_var", "clear_var"):
                    self.log.info(f"Action: unknown op {step.op}")

            # Minimal redecide: abort pack if page changed mid-pack
            if (
                self.project.runtime.allow_redecide_during_action
                and page_id
                and i + 1 < len(flat)
            ):
                frame = self.matcher.capture_screen()
                pr = self.matcher.detect_page(frame)
                if (
                    pr.page_id != "UNKNOWN"
                    and pr.page_id != page_id
                ):
                    self.log.info(
                        f"Action: page changed to {pr.page_id!r} — abort pack"
                    )
                    return False

        self.log.info("Action: pack finished → next loop")
        return True


    def _run_script(
        self,
        rel: str,
        *,
        page_id: str | None,
        vars: dict[str, Any] | None,
    ) -> bool:
        """Phase 3: load project script and call run(ctx, params)."""
        path = (self.project.root / rel).resolve()
        if not str(path).startswith(str(self.project.root.resolve())):
            self.log.info("Action: script path escapes project")
            return False
        if not path.is_file():
            self.log.info(f"Action: script not found {rel}")
            return False
        import importlib.util

        spec = importlib.util.spec_from_file_location("sf_user_script", path)
        if spec is None or spec.loader is None:
            return False
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            run = getattr(mod, "run", None)
            if not callable(run):
                self.log.info("Action: script missing run(ctx, params)")
                return False
            ctx = {
                "project_root": str(self.project.root),
                "page_id": page_id,
                "vars": vars if vars is not None else {},
                "log": self.log.info,
            }
            result = run(ctx, {})
            if result == "abort_pack":
                return False
            return True
        except Exception as exc:
            self.log.info(f"Action: script error {exc}")
            return False


def _parse_var(text: str) -> Any:
    low = text.lower()
    if low in ("true", "yes", "1"):
        return True
    if low in ("false", "no", "0"):
        return False
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text
