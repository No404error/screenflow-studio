"""Compatibility shim — prefer screenflow.decide."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

import numpy as np

from screenflow.decide import decide_page_state
from screenflow.models import PageDef

if TYPE_CHECKING:
    from screenflow.engine import FlowEngine
    from screenflow.matcher import ScreenMatcher


def resolve_state(
    page_def: PageDef,
    screen: np.ndarray,
    matcher: "ScreenMatcher",
    engine: "FlowEngine",
) -> tuple[str | None, dict[str, Any]]:
    result = decide_page_state(
        engine.project, page_def, screen, matcher, vars=engine.vars
    )
    return result.leaf_id, result.detail
