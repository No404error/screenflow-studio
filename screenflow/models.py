from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

DEFAULT_STATE = "DEFAULT"


class EngineStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPED = auto()


@dataclass
class ActionStep:
    op: str
    target: str | float | None = None
    reason: str | None = None
    # hold_key duration (seconds); unused by other ops
    hold: float | None = None
    # script step: passed as second arg to run(ctx, params)
    params: dict[str, Any] | None = None


@dataclass
class MacroDef:
    """Reusable step pack. scope=project for now; library reserved later."""

    id: str
    name: str
    steps: list[ActionStep] = field(default_factory=list)
    scope: str = "project"


@dataclass
class ScoreSpec:
    """How a state-tree candidate gets its confidence on the current frame."""

    # template | constant | invert
    kind: str = "template"
    key: str | None = None
    roi: list[float] | None = None
    constant: float = 0.0


@dataclass
class DecideParams:
    """threshold / near / margin / on_close — merge runtime → page → layer."""

    threshold: float | None = None
    near: float | None = None
    margin: float | None = None
    # When best−second < margin among near-band: "priority" (default) | "abstain"
    # None = inherit from outer merge layer / runtime default.
    on_close: str | None = None


def normalize_post_mode(mode: str | None) -> str:
    """
    Canonical post-listen modes:
      once | until_page | until_case | frames
    Legacy alias: until_miss → until_case
    """
    m = (mode or "once").strip().lower()
    if m == "until_miss":
        return "until_case"
    if m in ("once", "until_page", "until_case", "frames"):
        return m
    return "once"


@dataclass
class PostListen:
    """Post-processor listen config on a main leaf."""

    # once | until_page | until_case | frames  (legacy until_miss → until_case)
    # New follow-ups default to until_page (empty tree allowed).
    mode: str = "until_page"
    frames: int | None = None
    # Seconds to wait after main actions before the first post capture
    settle: float = 0.0
    # If True, UNKNOWN page ends sticky listen; if False, skip that frame
    end_on_unknown: bool = False
    # Root siblings of the listen tree (phase 1: usually one layer)
    tree: list[StateNode] = field(default_factory=list)
    params: DecideParams = field(default_factory=DecideParams)


@dataclass
class StateNode:
    """
    Node in the page state tree (or post listen tree).
    Intermediate nodes only branch; leaves may hold actions / post.
    """

    id: str
    name: str = ""
    priority: int = 0
    is_else: bool = False
    score: ScoreSpec | None = None
    children: list[StateNode] = field(default_factory=list)
    actions: list[ActionStep] = field(default_factory=list)
    post: PostListen | None = None
    # Optional overrides for the compete round among this node's children
    layer_params: DecideParams = field(default_factory=DecideParams)
    # Phase 3: require vars["k"] == value to compete (format k=value or k for truthy)
    when_var: str | None = None

    def display_name(self) -> str:
        return (self.name or self.id).strip() or self.id

    def is_leaf(self) -> bool:
        return not self.children


# Forward ref for PostListen.tree — dataclass already uses StateNode above.
# Ensure PostListen is fully defined after StateNode (reorder if needed).
# Python 3.10+ with from __future__ annotations is fine.


@dataclass
class VisualDef:
    """
    匹配方案 (Match setup / Visual): where to search + what template to match.
    Page-level first-class object; features select via visual_id.
    `asset` is the template path (JSON may also use key `template`).
    """

    id: str
    label: str = ""
    asset: str = ""  # template: project-relative image path
    search_roi: list[float] | None = None  # [y0,y1,x0,x1] 0–1 screen; None = full frame
    # Crop rect on page source (Studio overlay only; not used by matcher)
    content_roi: list[float] | None = None

    @property
    def template(self) -> str:
        return str(self.asset or "").strip()

    def is_complete(self) -> bool:
        return bool(self.template)


# Back-compat aliases
FeatureVisual = VisualDef
FeatureLink = VisualDef


@dataclass
class FeatureDef:
    """
    画面特征 — pure logical symbol (id/label).
    Selects at most one page-level Visual via visual_id.
    """

    id: str
    label: str = ""
    notes: str = ""
    # Selected match setup id (PageDef.visuals). None = not selected.
    visual_id: str | None = None

    def display_name(self) -> str:
        return (self.label or self.id).strip() or self.id

    def is_linked(self) -> bool:
        return bool(str(self.visual_id or "").strip())

    def has_visual(self) -> bool:
        return self.is_linked()


@dataclass
class PageDef:
    page_id: str
    name: str = ""
    # Root of state tree (siblings = first layer)
    state_tree: list[StateNode] = field(default_factory=list)
    # 画面特征 id → definition (flow references these ids)
    features: dict[str, FeatureDef] = field(default_factory=dict)
    # Match setups (visuals) — independent of features; may be idle or shared
    visuals: dict[str, VisualDef] = field(default_factory=dict)
    # Which feature is used to recognize this page (普通画面特征)
    recognize_with: str | None = None
    # Full-window canvas for match-setup editing (not used at runtime)
    source: str | None = None
    pair_with: str | None = None
    detect_priority: int = 0
    decide_params: DecideParams = field(default_factory=DecideParams)
    default_post: PostListen | None = None

    def display_name(self) -> str:
        return self.name.strip() or self.page_id

    def get_feature(self, feature_id: str | None) -> FeatureDef | None:
        if not feature_id:
            return None
        return self.features.get(str(feature_id))

    def get_visual(self, visual_id: str | None) -> VisualDef | None:
        if not visual_id:
            return None
        return self.visuals.get(str(visual_id))

    def feature_visual(self, feature_id: str | None) -> VisualDef | None:
        feat = self.get_feature(feature_id)
        if feat is None or not feat.visual_id:
            return None
        return self.get_visual(feat.visual_id)

    def linked_asset(self, feature_id: str | None) -> str | None:
        vis = self.feature_visual(feature_id)
        if vis is None:
            return None
        return str(vis.asset).strip() or None

    def feature_search_roi(self, feature_id: str | None) -> list[float] | None:
        vis = self.feature_visual(feature_id)
        if vis is None:
            return None
        return list(vis.search_roi) if vis.search_roi else None

    def recognize_asset(self) -> str | None:
        return self.linked_asset(self.recognize_with)

    def recognize_roi(self) -> list[float] | None:
        return self.feature_search_roi(self.recognize_with)


@dataclass
class RuntimeConfig:
    match_threshold: float = 0.72
    poll_interval: float = 0.5
    action_delay: float = 0.45
    action_cooldown: float = 0.35
    # State compete (also aliased as near/margin in DecideParams merge)
    state_conf_margin: float = 0.03
    state_near: float = 0.03
    page_pair_margin: float = 0.03
    page_detect_near: float = 0.35
    ref_width: int = 1920
    ref_height: int = 1080
    verbose_log: bool = False
    # Phase 3
    allow_redecide_during_action: bool = False
    log_language: str = "en"  # en | zh
    hotkeys: dict[str, str] = field(
        default_factory=lambda: {"start": "f9", "pause": "f10", "stop": "f11"}
    )


@dataclass
class Project:
    name: str
    root: Path
    runtime: RuntimeConfig
    pages: dict[str, PageDef]
    feature_files: dict[str, str] = field(default_factory=dict)
    macros: dict[str, MacroDef] = field(default_factory=dict)
    page_pairs: list[tuple[str, str]] = field(default_factory=list)
    detect_priority: dict[str, int] = field(default_factory=dict)
    # Phase 3 variables store (engine-owned at runtime; schema optional)
    var_defaults: dict[str, Any] = field(default_factory=dict)
    # UI metadata for vars: name → {type, description}; engine ignores this
    var_schema: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class MatchResult:
    page_id: str
    confidence: float
    center: tuple[int, int] | None
    scores: dict[str, float] | None = None


@dataclass
class DecideResult:
    """Outcome of state-tree (or post-tree) decision."""

    leaf: StateNode | None
    path: list[str] = field(default_factory=list)  # display names
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def leaf_id(self) -> str | None:
        return self.leaf.id if self.leaf else None

    def short_path(self, *, sep: str = " › ") -> str:
        return sep.join(self.path) if self.path else ""
