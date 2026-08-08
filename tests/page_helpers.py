"""Helpers for constructing PageDef under the visuals + visual_id schema."""

from __future__ import annotations

from screenflow.models import FeatureDef, PageDef, StateNode, VisualDef


def make_page(
    page_id: str,
    *,
    detect: str | None = None,
    name: str = "",
    state_tree: list[StateNode] | None = None,
    features: dict[str, str] | None = None,
    feature_rois: dict[str, list[float]] | None = None,
    detect_roi: list[float] | None = None,
    recognize_with: str | None = None,
    **kwargs,
) -> PageDef:
    """
    Build a PageDef.
    `detect` / `features` (id→relpath) / rois mirror the old test style and are
    converted into VisualDef + feature.visual_id.
    """
    feat_map: dict[str, FeatureDef] = {}
    visuals: dict[str, VisualDef] = {}
    rois = feature_rois or {}

    if features:
        for fid, rel in features.items():
            roi = rois.get(fid)
            visuals[fid] = VisualDef(
                id=fid,
                label=fid,
                asset=rel,
                search_roi=list(roi) if roi else None,
            )
            feat_map[fid] = FeatureDef(id=fid, label=fid, visual_id=fid)

    rw = recognize_with
    if detect:
        stem = detect.rsplit("/", 1)[-1].rsplit(".", 1)[0] or "main"
        matched = None
        for fid, vis in visuals.items():
            if vis.asset == detect:
                matched = fid
                break
        if matched is None:
            fid = stem if stem not in feat_map else f"{stem}__page"
            roi = detect_roi or rois.get(stem)
            visuals[fid] = VisualDef(
                id=fid,
                label=stem,
                asset=detect,
                search_roi=list(roi) if roi else None,
            )
            feat_map[fid] = FeatureDef(id=fid, label=stem, visual_id=fid)
            matched = fid
        elif detect_roi and not visuals[matched].search_roi:
            visuals[matched].search_roi = list(detect_roi)
        if rw is None:
            rw = matched

    return PageDef(
        page_id=page_id,
        name=name or page_id,
        state_tree=list(state_tree or []),
        features=feat_map,
        visuals=visuals,
        recognize_with=rw,
        **kwargs,
    )
