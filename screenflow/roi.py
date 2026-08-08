"""Normalized search ROI helpers. Convention: [y0, y1, x0, x1] in 0–1 of screen."""

from __future__ import annotations

from typing import Sequence


def normalize_roi(
    roi: Sequence[float] | None,
) -> tuple[float, float, float, float] | None:
    if roi is None or len(roi) != 4:
        return None
    y0, y1, x0, x1 = (float(roi[0]), float(roi[1]), float(roi[2]), float(roi[3]))
    y0 = min(max(y0, 0.0), 1.0)
    y1 = min(max(y1, 0.0), 1.0)
    x0 = min(max(x0, 0.0), 1.0)
    x1 = min(max(x1, 0.0), 1.0)
    if y1 <= y0 or x1 <= x0:
        return None
    return (y0, y1, x0, x1)


def roi_from_pixel_rect(
    x0: int, y0: int, x1: int, y1: int, *, width: int, height: int
) -> list[float] | None:
    """Build [y0, y1, x0, x1] from inclusive-exclusive pixel box on a full capture."""
    if width <= 0 or height <= 0:
        return None
    if x1 <= x0 or y1 <= y0:
        return None
    norm = normalize_roi([y0 / height, y1 / height, x0 / width, x1 / width])
    return list(norm) if norm else None


def effective_roi(
    override: Sequence[float] | None,
    asset: Sequence[float] | None,
) -> tuple[float, float, float, float] | None:
    """Prefer usage-site override, else asset ROI, else full frame (None)."""
    return normalize_roi(override) or normalize_roi(asset)


def expand_roi_for_search(
    roi: Sequence[float],
    *,
    pad_frac: float = 0.25,
    min_pad: float = 0.02,
) -> tuple[float, float, float, float]:
    """
    Grow a crop ROI into a search window.

    Templates are cropped to the selection box. If the search region is the
    same size, matchTemplate cannot slide and small UI jitter tanks confidence
    (e.g. 0.99 → ~0.67). Padding restores alignment slack while still
    avoiding full-screen scans.
    """
    n = normalize_roi(roi)
    if n is None:
        return (0.0, 1.0, 0.0, 1.0)
    y0, y1, x0, x1 = n
    hy = max((y1 - y0) * float(pad_frac), float(min_pad))
    hx = max((x1 - x0) * float(pad_frac), float(min_pad))
    out = normalize_roi([y0 - hy, y1 + hy, x0 - hx, x1 + hx])
    return out if out is not None else (0.0, 1.0, 0.0, 1.0)
