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


def _consume_frame(sticky: StickyPost, out: PostOutcome) -> None:
    """Decrement frames budget; end when exhausted."""
    if sticky.frames_left is None:
        return
    sticky.frames_left -= 1
    if sticky.frames_left <= 0:
        out.ended = True
        out.detail["reason"] = "frames_exhausted"


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
      until_case — when the listen leaf is ELSE (legacy until_miss)
      frames — after N observation attempts (hit, miss, or unknown-skip)
    UNKNOWN: end only if listen.end_on_unknown; otherwise skip this frame (still counts for frames).
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
        if mode == "frames":
            _consume_frame(sticky, out)
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
        if mode == "frames":
            path_parts = []
            if sticky.path_prefix:
                path_parts.append(sticky.path_prefix)
            path_parts.append("post")
            out.short_path = " › ".join(path_parts)
            out.skipped = True
            out.ran = False
            out.detail["reason"] = "empty_tree"
            _consume_frame(sticky, out)
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
    out.detail = dict(result.detail)
    # End until_case on the leaf being ELSE (not last-layer compete flag).
    used_else = bool(result.leaf is not None and result.leaf.is_else)
    out.used_else = used_else
    path_parts = []
    if sticky.path_prefix:
        path_parts.append(sticky.path_prefix)
    path_parts.append("post")
    if result.path:
        path_parts.extend(result.path)
    out.short_path = " › ".join(path_parts)

    if result.leaf is None:
        if mode in ("until_page", "frames"):
            out.skipped = True
            out.ran = False
            out.detail["reason"] = "no_match_skip"
            if mode == "frames":
                _consume_frame(sticky, out)
            return out
        out.ended = True
        out.detail["reason"] = "no_match"
        return out

    out.leaf = result.leaf
    # until_page + ELSE: wait for page change; do not re-fire ELSE actions every poll.
    if mode == "until_page" and result.leaf.is_else:
        out.skipped = True
        out.ran = False
        out.detail["reason"] = "until_page_else_wait"
        return out

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
        # Continue on same page; end only via page_changed above.
        pass
    elif mode == "frames":
        _consume_frame(sticky, out)
    return out
