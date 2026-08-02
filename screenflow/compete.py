from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from screenflow.models import DecideParams

T = TypeVar("T")


@dataclass
class ScoredCandidate(Generic[T]):
    item: T
    score: float
    priority: int
    is_else: bool = False
    label: str = ""


@dataclass
class CompeteDetail:
    scores: dict[str, float]
    eliminated: list[str]
    winner_label: str | None
    used_else: bool = False


def compete(
    candidates: list[ScoredCandidate[T]],
    params: DecideParams,
) -> tuple[ScoredCandidate[T] | None, CompeteDetail]:
    """
    Shared compete: threshold → near band → relative margin → priority.
    ELSE candidates do not score; if nobody passes, pick the single ELSE if present.
    """
    detail = CompeteDetail(scores={}, eliminated=[], winner_label=None)
    threshold = float(params.threshold if params.threshold is not None else 0.72)
    near = float(params.near if params.near is not None else 0.03)
    margin = float(params.margin if params.margin is not None else 0.03)

    else_cand = [c for c in candidates if c.is_else]
    scored = [c for c in candidates if not c.is_else]

    for c in scored:
        detail.scores[c.label or str(c.priority)] = c.score

    passed = [c for c in scored if c.score >= threshold]
    if not passed:
        if len(else_cand) == 1:
            w = else_cand[0]
            detail.winner_label = w.label
            detail.used_else = True
            return w, detail
        return None, detail

    top = max(c.score for c in passed)
    near_band = [c for c in passed if top - c.score <= near]
    # Relative margin: winner must beat second-best among near_band by margin
    near_band.sort(key=lambda c: (c.score, c.priority), reverse=True)
    if len(near_band) >= 2:
        best, second = near_band[0], near_band[1]
        if best.score - second.score < margin:
            on_close = (params.on_close or "priority").strip().lower()
            if on_close == "abstain":
                # Too close to call: no scored winner; ELSE if present, else None.
                detail.eliminated.append(
                    f"close:abstain({best.score - second.score:.3f}<{margin})"
                )
                if len(else_cand) == 1:
                    w = else_cand[0]
                    detail.winner_label = w.label
                    detail.used_else = True
                    return w, detail
                return None, detail
            # Default: keep those within margin of best for priority break
            tight = [c for c in near_band if best.score - c.score < margin]
            for c in near_band:
                if c not in tight:
                    detail.eliminated.append(
                        f"{c.label}:margin({best.score - c.score:.3f}<{margin})"
                    )
            near_band = tight

    winner = max(near_band, key=lambda c: (c.priority, c.score))
    for c in near_band:
        if c is not winner:
            detail.eliminated.append(f"{c.label}:priority_or_score")
    detail.winner_label = winner.label
    return winner, detail


def compete_page_pair(
    best_id: str,
    best_conf: float,
    sibling_id: str,
    sibling_conf: float,
    pri: dict[str, int],
    params: DecideParams,
    threshold: float,
) -> str | None:
    """
    Page-pair disambiguation using the same margin/priority idea.
    Returns winning page id, or None for UNKNOWN.
    """
    margin = float(params.margin if params.margin is not None else 0.03)
    if best_conf - sibling_conf >= margin:
        return best_id
    bp = pri.get(best_id, 0)
    sp = pri.get(sibling_id, 0)
    if bp > sp:
        return best_id
    if sp > bp and sibling_conf >= threshold:
        return sibling_id
    return None
