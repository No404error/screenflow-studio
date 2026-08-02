from __future__ import annotations

from typing import Any, TYPE_CHECKING

import numpy as np

from screenflow.assets import scoped_asset_key
from screenflow.compete import ScoredCandidate, compete
from screenflow.models import (
    DecideParams,
    DecideResult,
    PageDef,
    Project,
    RuntimeConfig,
    ScoreSpec,
    StateNode,
)
from screenflow.project import merge_decide_params

if TYPE_CHECKING:
    from screenflow.matcher import ScreenMatcher


def _var_match(vars: dict[str, Any], expr: str) -> bool:
    expr = expr.strip()
    if not expr:
        return True
    if "=" in expr:
        k, v = expr.split("=", 1)
        cur = vars.get(k.strip())
        want = v.strip()
        if want.lower() in ("true", "false"):
            return bool(cur) == (want.lower() == "true")
        return str(cur) == want
    return bool(vars.get(expr))


def score_node(
    node: StateNode,
    screen: np.ndarray,
    matcher: "ScreenMatcher",
    page_id: str,
) -> float:
    if node.is_else:
        return 0.0
    spec = node.score
    if spec is None:
        return 0.0
    if spec.kind == "constant":
        return float(spec.constant)
    if spec.kind == "invert":
        base = ScoreSpec(
            kind="template",
            key=spec.key,
            source=spec.source,
            roi=spec.roi,
        )
        conf = _template_score(base, screen, matcher, page_id)
        return max(0.0, 1.0 - conf)
    return _template_score(spec, screen, matcher, page_id)


def _template_score(
    spec: ScoreSpec,
    screen: np.ndarray,
    matcher: "ScreenMatcher",
    page_id: str,
) -> float:
    key = (spec.key or "").strip()
    if not key:
        return 0.0
    roi = tuple(spec.roi) if spec.roi and len(spec.roi) == 4 else None
    source = (spec.source or "detect").lower()
    if source == "click":
        scoped = scoped_asset_key(page_id, key)
        conf, _ = matcher.match_click(screen, scoped, roi=roi)
        if conf <= 0:
            conf, _ = matcher.match_click(screen, key, roi=roi)
        return conf
    scoped = scoped_asset_key(page_id, key)
    conf, _ = matcher.match_detect(screen, scoped, roi=roi)
    if conf <= 0:
        conf, _ = matcher.match_detect(screen, key, roi=roi)
    return conf


def decide_layer(
    siblings: list[StateNode],
    screen: np.ndarray,
    matcher: "ScreenMatcher",
    page_id: str,
    params: DecideParams,
    *,
    vars: dict[str, Any] | None = None,
) -> tuple[StateNode | None, dict[str, Any]]:
    """One compete round among siblings. vars reserved for phase 3 (read-only)."""
    # Sole unscored non-ELSE sibling → treat as ELSE (legacy DEFAULT pages).
    if (
        len(siblings) == 1
        and not siblings[0].is_else
        and siblings[0].score is None
        and not (siblings[0].when_var and not _var_match(vars or {}, siblings[0].when_var))
    ):
        node = siblings[0]
        return node, {
            "scores": {},
            "eliminated": [],
            "used_else": True,
            "winner": node.display_name(),
            "implicit_else": True,
        }

    cands: list[ScoredCandidate[StateNode]] = []
    for node in siblings:
        if node.when_var and not _var_match(vars or {}, node.when_var):
            continue
        sc = 0.0 if node.is_else else score_node(node, screen, matcher, page_id)
        cands.append(
            ScoredCandidate(
                item=node,
                score=sc,
                priority=node.priority,
                is_else=node.is_else,
                label=node.display_name(),
            )
        )
    winner, detail = compete(cands, params)
    info = {
        "scores": detail.scores,
        "eliminated": detail.eliminated,
        "used_else": detail.used_else,
        "winner": detail.winner_label,
    }
    return (winner.item if winner else None), info


def decide_tree(
    roots: list[StateNode],
    screen: np.ndarray,
    matcher: "ScreenMatcher",
    page_id: str,
    runtime: RuntimeConfig,
    page_params: DecideParams | None = None,
    *,
    parent_layer_params: DecideParams | None = None,
    vars: dict[str, Any] | None = None,
) -> DecideResult:
    """Walk state tree to a leaf; return path of display names."""
    if not roots:
        return DecideResult(leaf=None, path=[], detail={"reason": "empty_tree"})

    path: list[str] = []
    detail: dict[str, Any] = {"layers": []}
    siblings = roots
    layer_index = 0
    # First layer uses page params; deeper layers use parent node's layer_params
    current_params = merge_decide_params(
        runtime, page_params, parent_layer_params
    )

    while siblings:
        node, layer_detail = decide_layer(
            siblings, screen, matcher, page_id, current_params, vars=vars
        )
        detail["layers"].append(layer_detail)
        if node is None:
            return DecideResult(leaf=None, path=path, detail=detail)
        path.append(node.display_name())
        if node.is_leaf():
            return DecideResult(leaf=node, path=path, detail=detail)
        # Descend: child's siblings compete with this node's layer_params
        current_params = merge_decide_params(
            runtime, page_params, node.layer_params
        )
        siblings = node.children
        layer_index += 1

    return DecideResult(leaf=None, path=path, detail=detail)


def decide_page_state(
    project: Project,
    page: PageDef,
    screen: np.ndarray,
    matcher: "ScreenMatcher",
    *,
    vars: dict[str, Any] | None = None,
) -> DecideResult:
    return decide_tree(
        page.state_tree,
        screen,
        matcher,
        page.page_id,
        project.runtime,
        page.decide_params,
        vars=vars,
    )
