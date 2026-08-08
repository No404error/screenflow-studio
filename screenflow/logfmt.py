from __future__ import annotations

import time
from typing import Any, Callable

from screenflow.models import MatchResult, Project

LogEmit = Callable[[str], None]


_ZH_HINTS = (
    ("Unknown screen", "未识别页面"),
    ("no matching state", "无匹配状态"),
    ("waiting for another page", "等待命中其他页面"),
    ("no follow-up case — keep waiting", "后续情况未命中 — 继续等待"),
    ("Action:", "动作:"),
    ("RUNNING", "运行中"),
    ("PAUSED", "已暂停"),
    ("STOPPED", "已停止"),
    ("Error:", "错误:"),
)


class EngineLog:
    """Engine logs: brief by default; optional verbose; optional zh gloss."""

    def __init__(
        self,
        emit: LogEmit | None = None,
        *,
        verbose: bool = False,
        language: str = "en",
    ) -> None:
        self._emit = emit or (lambda msg: print(msg, flush=True))
        self.verbose = verbose
        self.language = language

    def info(self, msg: str) -> None:
        out = msg
        if self.language == "zh":
            for en, zh in _ZH_HINTS:
                out = out.replace(en, zh)
        self._emit(f"[{time.strftime('%H:%M:%S')}] {out}")

    def detail(self, msg: str) -> None:
        if self.verbose:
            self.info(msg)

    def page_label(self, project: Project, page_id: str) -> str:
        if page_id == "UNKNOWN":
            return "unknown screen"
        page = project.pages.get(page_id)
        name = page.display_name() if page else page_id
        if self.verbose and page and name != page_id:
            return f"{name} [{page_id}]"
        return name

    def macro_label(self, project: Project, macro_id: str) -> str:
        macro = project.macros.get(macro_id)
        name = (macro.name if macro else "") or macro_id
        if self.verbose and macro and name != macro_id:
            return f"{name} [{macro_id}]"
        return name

    def format_scores(self, detail: dict[str, Any]) -> str:
        parts: list[str] = []
        for k, v in detail.items():
            if k in ("after", "probe"):
                continue
            if isinstance(v, float):
                parts.append(f"{k}={v:.2f}")
            else:
                parts.append(f"{k}={v}")
        return " ".join(parts)

    def frame(
        self,
        project: Project,
        frame_id: int,
        page_result: MatchResult,
        *,
        paused: bool,
    ) -> None:
        label = self.page_label(project, page_result.page_id)
        line = f"Frame #{frame_id} → {label} ({page_result.confidence:.2f})"
        if paused:
            line += " [paused]"
        self.info(line)
        if self.verbose and page_result.scores:
            scores = " ".join(f"{k}={v:.2f}" for k, v in page_result.scores.items())
            self.detail(f"  candidates: {scores}")

    def status(self, name: str) -> None:
        self.info(f">>> {name}")
