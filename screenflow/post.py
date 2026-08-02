from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

import numpy as np

from screenflow.decide import decide_tree
from screenflow.models import DecideResult, PostListen, Project, StateNode
from screenflow.project import merge_decide_params

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
    Ends on page change, once completion, until_miss+ELSE, or frames expiry.
    UNKNOWN: end only if listen.end_on_unknown; otherwise skip this frame.
    """
    out = PostOutcome(ran=True)
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
    params = merge_decide_params(
        project.runtime, listen.params
    )
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

    mode = sticky.mode
    if mode == "once":
        out.ended = True
    elif mode == "until_miss":
        if used_else:
            out.ended = True
            out.detail["reason"] = "else_ends_until_miss"
    elif mode == "frames":
        if sticky.frames_left is not None:
            sticky.frames_left -= 1
            if sticky.frames_left <= 0:
                out.ended = True
                out.detail["reason"] = "frames_exhausted"
    return out
