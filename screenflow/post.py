from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

import numpy as np

from screenflow.decide import decide_tree
from screenflow.models import DecideResult, PostListen, Project, StateNode, normalize_post_mode

if TYPE_CHECKING:
    from screenflow.engine import FlowEngine
    from screenflow.matcher import ScreenMatcher


@dataclass
class StickyPost:
    """Active post-listen session across frames."""

    page_id: str
    listen: PostListen
    mode: str
    frames_left: int | None = None
    path_prefix: str = ""
    # Wait settle seconds before the next capture (usually once after arming)
    pending_settle: bool = True


@dataclass
class PostOutcome:
    ran: bool = False
    ended: bool = False
    skipped: bool = False
    short_path: str = ""
    leaf: StateNode | None = None
    used_else: bool = False
    detail: dict[str, Any] = field(default_factory=dict)


def run_post_listen(
    project: Project,
    matcher: "ScreenMatcher",
    engine: "FlowEngine",
    sticky: StickyPost,
    screen: np.ndarray,
    *,
    current_page_id: str,
) -> PostOutcome:
    """
    Evaluate post listen tree on screen and run leaf actions.

    End conditions by mode:
      once — after one evaluation
      until_page — when the page changes (empty tree / ELSE / no-match keep listening)
      until_case — when the listen tree picks ELSE (legacy until_miss)
      frames — when the frame budget is exhausted
    UNKNOWN: end only if listen.end_on_unknown; otherwise skip this frame.
    """
    out = PostOutcome(ran=True)
    mode = normalize_post_mode(sticky.mode)

    if current_page_id == "UNKNOWN":
        if sticky.listen.end_on_unknown:
            out.ended = True
            out.detail["reason"] = "unknown_page"
            return out
        out.skipped = True
        out.ran = False
        out.detail["reason"] = "unknown_skip"
        return out
    if current_page_id != sticky.page_id:
        out.ended = True
        out.detail["reason"] = "page_changed"
        return out

    listen = sticky.listen
    # Empty until_page: only wait for page_changed (handled above).
    if not listen.tree:
        if mode == "until_page":
            path_parts = []
            if sticky.path_prefix:
                path_parts.append(sticky.path_prefix)
            path_parts.append("post")
            out.short_path = " › ".join(path_parts)
            out.skipped = True
            out.ran = False
            out.detail["reason"] = "until_page_wait"
            return out
        out.ended = True
        out.detail["reason"] = "empty_tree"
        return out

    result: DecideResult = decide_tree(
        listen.tree,
        screen,
        matcher,
        sticky.page_id,
        project.runtime,
        listen.params,
        vars=engine.vars,
    )
    out.detail = result.detail
    layers = result.detail.get("layers") or []
    used_else = bool(layers and layers[-1].get("used_else"))
    out.used_else = used_else
    path_parts = []
    if sticky.path_prefix:
        path_parts.append(sticky.path_prefix)
    path_parts.append("post")
    if result.path:
        path_parts.extend(result.path)
    out.short_path = " › ".join(path_parts)

    if result.leaf is None:
        # until_page: stay armed until the page actually changes
        if mode == "until_page":
            out.skipped = True
            out.ran = False
            out.detail["reason"] = "no_match_skip"
            return out
        out.ended = True
        out.detail["reason"] = "no_match"
        return out

    out.leaf = result.leaf
    # Run post actions
    engine.actions.run_steps(
        result.leaf.actions,
        screen,
        {},
        page_id=sticky.page_id,
        vars=engine.vars,
    )

    if mode == "once":
        out.ended = True
    elif mode == "until_case":
        if used_else:
            out.ended = True
            out.detail["reason"] = "else_ends_until_case"
    elif mode == "until_page":
        # Continue on same page (including ELSE); end only via page_changed above.
        pass
    elif mode == "frames":
        if sticky.frames_left is not None:
            sticky.frames_left -= 1
            if sticky.frames_left <= 0:
                out.ended = True
                out.detail["reason"] = "frames_exhausted"
    return out
