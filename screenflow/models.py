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

    # template | constant
    kind: str = "template"
    key: str | None = None
    source: str = "detect"  # detect | click
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
class PageDef:
    page_id: str
    detect_relpath: str
    name: str = ""
    # Root of state tree (siblings = first layer)
    state_tree: list[StateNode] = field(default_factory=list)
    detect_extras: dict[str, str] = field(default_factory=dict)
    click_map: dict[str, str] = field(default_factory=dict)
    pair_with: str | None = None
    detect_priority: int = 0
    decide_params: DecideParams = field(default_factory=DecideParams)
    # Phase 2: page-level default post
    default_post: PostListen | None = None

    def display_name(self) -> str:
        return self.name.strip() or self.page_id


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
    detect_files: dict[str, str]
    click_files: dict[str, str]
    macros: dict[str, MacroDef] = field(default_factory=dict)
    page_pairs: list[tuple[str, str]] = field(default_factory=list)
    detect_priority: dict[str, int] = field(default_factory=dict)
    # Phase 3 variables store (engine-owned at runtime; schema optional)
    var_defaults: dict[str, Any] = field(default_factory=dict)


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
