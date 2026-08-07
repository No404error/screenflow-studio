from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Iterable

from screenflow.assets import (
    ensure_page_asset_dirs,
    page_dir,
    page_json_path,
    scoped_asset_key,
    sync_page_asset_maps,
)

PROJECT_FORMAT_VERSION = 3
from screenflow.models import (
    ActionStep,
    DecideParams,
    MacroDef,
    PageDef,
    PostListen,
    Project,
    RuntimeConfig,
    ScoreSpec,
    StateNode,
    DEFAULT_STATE,
    normalize_post_mode,
)


class ProjectLoadError(ValueError):
    """Invalid or unsupported project.json."""


def slugify_id(name: str, existing: Iterable[str], *, fallback: str = "page") -> str:
    """Build a stable ascii id from a display name; uniquify against existing ids."""
    base = re.sub(r"[^A-Za-z0-9]+", "_", name.strip()).strip("_").lower()
    if not base:
        base = fallback
    taken = set(existing)
    candidate = base
    n = 2
    while candidate in taken:
        candidate = f"{base}_{n}"
        n += 1
    return candidate


def _steps_from_json(items: list[dict[str, Any]] | None) -> list[ActionStep]:
    if not items:
        return []
    steps: list[ActionStep] = []
    for raw in items:
        hold = raw.get("hold")
        steps.append(
            ActionStep(
                op=str(raw["op"]),
                target=raw.get("target"),
                reason=raw.get("reason"),
                hold=float(hold) if hold is not None else None,
            )
        )
    return steps


def _steps_to_json(steps: list[ActionStep]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in steps:
        item: dict[str, Any] = {"op": s.op}
        if s.target is not None:
            item["target"] = s.target
        if s.reason is not None:
            item["reason"] = s.reason
        if s.hold is not None:
            item["hold"] = s.hold
        out.append(item)
    return out


def _normalize_on_close(raw: object | None) -> str | None:
    if raw is None:
        return None
    val = str(raw).strip().lower()
    if val in ("priority", "abstain"):
        return val
    return None


def _params_from_json(raw: dict[str, Any] | None) -> DecideParams:
    if not raw:
        return DecideParams()
    return DecideParams(
        threshold=float(raw["threshold"]) if raw.get("threshold") is not None else None,
        near=float(raw["near"]) if raw.get("near") is not None else None,
        margin=float(raw["margin"]) if raw.get("margin") is not None else None,
        on_close=_normalize_on_close(raw.get("on_close")),
    )


def _params_to_json(p: DecideParams) -> dict[str, Any] | None:
    out: dict[str, Any] = {}
    if p.threshold is not None:
        out["threshold"] = p.threshold
    if p.near is not None:
        out["near"] = p.near
    if p.margin is not None:
        out["margin"] = p.margin
    if p.on_close in ("priority", "abstain"):
        out["on_close"] = p.on_close
    return out or None


def _score_from_json(raw: dict[str, Any] | None) -> ScoreSpec | None:
    if not raw:
        return None
    kind = str(raw.get("kind") or "template")
    return ScoreSpec(
        kind=kind,
        key=str(raw["key"]) if raw.get("key") is not None else None,
        source=str(raw.get("source") or "detect"),
        roi=list(raw["roi"]) if raw.get("roi") else None,
        constant=float(raw.get("constant", 0.0)),
    )


def _score_to_json(score: ScoreSpec | None) -> dict[str, Any] | None:
    if score is None:
        return None
    kind = (score.kind or "template").lower()
    if kind == "constant":
        return {"kind": "constant", "constant": score.constant}
    if kind not in ("template", "invert"):
        kind = "template"
    item: dict[str, Any] = {
        "kind": kind,
        "key": score.key,
        "source": score.source,
    }
    if score.roi:
        item["roi"] = score.roi
    return item


def _post_from_json(raw: dict[str, Any] | None) -> PostListen | None:
    if not raw:
        return None
    return PostListen(
        mode=normalize_post_mode(str(raw.get("mode") or "once")),
        frames=int(raw["frames"]) if raw.get("frames") is not None else None,
        settle=float(raw.get("settle") or 0.0),
        end_on_unknown=bool(raw.get("end_on_unknown", False)),
        tree=[_node_from_json(n) for n in (raw.get("tree") or [])],
        params=_params_from_json(raw.get("params")),
    )


def _post_to_json(post: PostListen | None) -> dict[str, Any] | None:
    if post is None:
        return None
    out: dict[str, Any] = {
        "mode": normalize_post_mode(post.mode),
        "tree": [_node_to_json(n) for n in post.tree],
    }
    if post.frames is not None:
        out["frames"] = post.frames
    if post.settle and post.settle > 0:
        out["settle"] = post.settle
    if post.end_on_unknown:
        out["end_on_unknown"] = True
    params = _params_to_json(post.params)
    if params:
        out["params"] = params
    return out


def _node_from_json(raw: dict[str, Any]) -> StateNode:
    nid = str(raw.get("id") or raw.get("name") or "node")
    children = [_node_from_json(c) for c in (raw.get("children") or [])]
    return StateNode(
        id=nid,
        name=str(raw.get("name") or nid),
        priority=int(raw.get("priority", 0)),
        is_else=bool(raw.get("else") or raw.get("is_else")),
        score=_score_from_json(raw.get("score")),
        children=children,
        actions=_steps_from_json(raw.get("actions")),
        post=_post_from_json(raw.get("post")),
        layer_params=_params_from_json(raw.get("layer_params") or raw.get("params")),
        when_var=str(raw["when_var"]) if raw.get("when_var") else None,
    )


def normalize_sole_unscored_else(nodes: list[StateNode]) -> None:
    """Mark sole unscored sibling as ELSE (legacy DEFAULT). Recurse children/post."""
    if len(nodes) == 1 and not nodes[0].is_else and nodes[0].score is None:
        nodes[0].is_else = True
    for n in nodes:
        if n.children:
            normalize_sole_unscored_else(n.children)
        if n.post and n.post.tree:
            normalize_sole_unscored_else(n.post.tree)


def _node_to_json(node: StateNode) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": node.id,
        "name": node.display_name(),
        "priority": node.priority,
    }
    if node.is_else:
        item["else"] = True
    score = _score_to_json(node.score)
    if score:
        item["score"] = score
    if node.children:
        item["children"] = [_node_to_json(c) for c in node.children]
    if node.actions:
        item["actions"] = _steps_to_json(node.actions)
    post = _post_to_json(node.post)
    if post:
        item["post"] = post
    lp = _params_to_json(node.layer_params)
    if lp:
        item["layer_params"] = lp
    if node.when_var:
        item["when_var"] = node.when_var
    return item


def _legacy_flat_to_tree(
    states_raw: list[dict[str, Any]],
    actions: dict[str, list[ActionStep]],
) -> list[StateNode]:
    """Convert legacy flat states + actions map into a single-layer tree."""
    nodes: list[StateNode] = []
    if not states_raw:
        # DEFAULT leaf only
        return [
            StateNode(
                id=DEFAULT_STATE,
                name=DEFAULT_STATE,
                actions=list(actions.get(DEFAULT_STATE) or []),
            )
        ]
    for st in states_raw:
        name = str(st["name"])
        kind = str(st.get("kind", "STATIC")).upper()
        if kind == "DYNAMIC" or st.get("when_field") is not None or st.get("when"):
            raise ProjectLoadError(
                f"Legacy DYNAMIC / when_field state {name!r} is no longer supported. "
                "Migrate to a state tree with scores / ELSE line and post-listen "
                "(remove probe_steps / probe_checks)."
            )
        dkey = st.get("detect_key") or name.lower()
        score = ScoreSpec(kind="template", key=str(dkey), source="detect", roi=st.get("roi"))
        nodes.append(
            StateNode(
                id=name,
                name=name,
                priority=int(st.get("priority", 0)),
                is_else=bool(st.get("else") or st.get("is_else")),
                score=score,
                actions=list(actions.get(name) or []),
            )
        )
    return nodes


def _reject_probe(raw_page: dict[str, Any], page_id: str) -> None:
    if raw_page.get("probe_steps") or raw_page.get("probe_checks"):
        raise ProjectLoadError(
            f"Page {page_id!r}: probe_steps/probe_checks were removed. "
            "Use main-leaf actions + post-listen instead."
        )


def merge_decide_params(
    runtime: RuntimeConfig,
    *layers: DecideParams | None,
    for_page_detect: bool = False,
) -> DecideParams:
    """Merge runtime defaults with page/layer overrides."""
    if for_page_detect:
        base = DecideParams(
            threshold=runtime.match_threshold,
            near=runtime.page_detect_near,
            margin=runtime.page_pair_margin,
            on_close="priority",
        )
    else:
        base = DecideParams(
            threshold=runtime.match_threshold,
            near=runtime.state_near,
            margin=runtime.state_conf_margin,
            on_close="priority",
        )
    for layer in layers:
        if not layer:
            continue
        if layer.threshold is not None:
            base.threshold = layer.threshold
        if layer.near is not None:
            base.near = layer.near
        if layer.margin is not None:
            base.margin = layer.margin
        if layer.on_close in ("priority", "abstain"):
            base.on_close = layer.on_close
    return base


def iter_tree(nodes: list[StateNode]):
    for n in nodes:
        yield n
        yield from iter_tree(n.children)


def find_node(nodes: list[StateNode], node_id: str) -> StateNode | None:
    for n in iter_tree(nodes):
        if n.id == node_id:
            return n
    return None


def rebuild_resource_index(project: Project) -> None:
    """Rebuild detect/click maps and pairs from page definitions (after edits)."""
    detect_files: dict[str, str] = {}
    click_files: dict[str, str] = {}
    detect_priority: dict[str, int] = {}
    page_pairs: list[tuple[str, str]] = []

    for page_id, page in project.pages.items():
        ensure_page_asset_dirs(project, page_id)
        sync_page_asset_maps(project, page)
        detect_priority[page_id] = page.detect_priority
        for k, rel in page.detect_extras.items():
            detect_files[scoped_asset_key(page_id, k)] = rel
            detect_files.setdefault(k, rel)
        for k, rel in page.click_map.items():
            click_files[scoped_asset_key(page_id, k)] = rel
            click_files.setdefault(k, rel)
        if page.pair_with:
            a, b = page_id, page.pair_with
            pair = (a, b) if a < b else (b, a)
            if pair not in page_pairs:
                page_pairs.append(pair)

    project.detect_files = detect_files
    project.click_files = click_files
    project.detect_priority = detect_priority
    project.page_pairs = page_pairs


def list_page_pairs(project: Project) -> list[tuple[str, str]]:
    """Unique unordered pairs (a < b by id) currently defined on pages."""
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for page_id, page in project.pages.items():
        other = page.pair_with
        if not other or other not in project.pages:
            continue
        pair = (page_id, other) if page_id < other else (other, page_id)
        if pair not in seen:
            seen.add(pair)
            out.append(pair)
    out.sort()
    return out


def _clear_partner_link(project: Project, page_id: str) -> None:
    page = project.pages.get(page_id)
    if page is None:
        return
    old = page.pair_with
    page.pair_with = None
    if old and old in project.pages and project.pages[old].pair_with == page_id:
        project.pages[old].pair_with = None


def set_page_pair(project: Project, page_a: str, page_b: str | None) -> None:
    """
    Pair page_a with page_b (one-to-one), or clear when page_b is None.
    Always keeps both sides consistent; a page belongs to at most one pair.
    """
    if page_a not in project.pages:
        return
    if page_b == page_a:
        page_b = None
    if page_b is not None and page_b not in project.pages:
        return

    _clear_partner_link(project, page_a)
    if page_b is None:
        rebuild_resource_index(project)
        return

    _clear_partner_link(project, page_b)
    project.pages[page_a].pair_with = page_b
    project.pages[page_b].pair_with = page_a
    rebuild_resource_index(project)


def clear_pairs_involving(project: Project, page_id: str) -> None:
    """Remove any mutex pair that includes page_id (e.g. before deleting the page)."""
    _clear_partner_link(project, page_id)
    rebuild_resource_index(project)


def _runtime_from_json(rt_raw: dict[str, Any]) -> RuntimeConfig:
    return RuntimeConfig(
        match_threshold=float(rt_raw.get("match_threshold", 0.72)),
        poll_interval=float(rt_raw.get("poll_interval", 0.5)),
        action_delay=float(rt_raw.get("action_delay", 0.45)),
        action_cooldown=float(rt_raw.get("action_cooldown", 0.35)),
        state_conf_margin=float(
            rt_raw.get("state_conf_margin", rt_raw.get("state_margin", 0.03))
        ),
        state_near=float(rt_raw.get("state_near", 0.03)),
        page_pair_margin=float(rt_raw.get("page_pair_margin", 0.03)),
        page_detect_near=float(rt_raw.get("page_detect_near", 0.35)),
        ref_width=int(rt_raw.get("ref_width", 1920)),
        ref_height=int(rt_raw.get("ref_height", 1080)),
        verbose_log=bool(rt_raw.get("verbose_log", False)),
        allow_redecide_during_action=bool(
            rt_raw.get("allow_redecide_during_action", False)
        ),
        log_language=str(rt_raw.get("log_language") or "en"),
        hotkeys=dict(
            rt_raw.get("hotkeys") or {"start": "f9", "pause": "f10", "stop": "f11"}
        ),
    )


def _page_from_json(raw: dict[str, Any], *, page_id: str | None = None) -> PageDef:
    pid = str(page_id or raw["id"])
    _reject_probe(raw, pid)
    detect_rel = str(raw.get("detect") or f"pages/{pid}/detect/main.png")
    extras = {str(k): str(v) for k, v in (raw.get("detect_extras") or {}).items()}
    clicks = {str(k): str(v) for k, v in (raw.get("click") or {}).items()}

    if raw.get("state_tree") is not None:
        tree = [_node_from_json(n) for n in raw["state_tree"]]
    else:
        actions = {
            str(k): _steps_from_json(v) for k, v in (raw.get("actions") or {}).items()
        }
        tree = _legacy_flat_to_tree(list(raw.get("states") or []), actions)

    normalize_sole_unscored_else(tree)
    default_post = _post_from_json(raw.get("default_post"))
    if default_post and default_post.tree:
        normalize_sole_unscored_else(default_post.tree)

    return PageDef(
        page_id=pid,
        detect_relpath=detect_rel,
        name=str(raw.get("name") or pid),
        state_tree=tree,
        detect_extras=extras,
        click_map=clicks,
        pair_with=str(raw["pair_with"]) if raw.get("pair_with") else None,
        detect_priority=int(raw.get("detect_priority", 0)),
        decide_params=_params_from_json(raw.get("decide_params")),
        default_post=default_post,
    )


def page_to_dict(page: PageDef) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": page.page_id,
        "name": page.display_name(),
        "detect": page.detect_relpath,
        "detect_priority": page.detect_priority,
        "pair_with": page.pair_with,
        "detect_extras": page.detect_extras,
        "click": page.click_map,
        "state_tree": [_node_to_json(n) for n in page.state_tree],
    }
    dp = _params_to_json(page.decide_params)
    if dp:
        item["decide_params"] = dp
    dpost = _post_to_json(page.default_post)
    if dpost:
        item["default_post"] = dpost
    return item


def _macros_from_json(raw_macros: Any) -> dict[str, MacroDef]:
    macros: dict[str, MacroDef] = {}
    if isinstance(raw_macros, dict):
        for mid, steps in raw_macros.items():
            mid_s = str(mid)
            macros[mid_s] = MacroDef(
                id=mid_s,
                name=mid_s,
                steps=_steps_from_json(steps),
                scope="project",
            )
        return macros
    for raw in raw_macros or []:
        mid = str(raw["id"])
        macros[mid] = MacroDef(
            id=mid,
            name=str(raw.get("name") or mid),
            steps=_steps_from_json(raw.get("steps")),
            scope=str(raw.get("scope") or "project"),
        )
    return macros


def load_project(project_dir: str | Path) -> Project:
    root = Path(project_dir).resolve()
    meta_path = root / "project.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"project.json not found in {root}")

    data = json.loads(meta_path.read_text(encoding="utf-8"))
    runtime = _runtime_from_json(data.get("runtime") or {})
    macros = _macros_from_json(data.get("macros") or [])

    pages: dict[str, PageDef] = {}
    raw_pages = data.get("pages") or []

    # v3: pages is a list of page ids; each page lives in pages/{id}/page.json
    page_ids: list[str] = []
    if not raw_pages:
        page_ids = []
    elif all(isinstance(x, str) for x in raw_pages):
        page_ids = [str(x) for x in raw_pages]
    elif isinstance(raw_pages[0], dict) and "state_tree" not in raw_pages[0]:
        page_ids = [str(entry["id"]) for entry in raw_pages]
    else:
        raise ProjectLoadError(
            "Unsupported project.json: expected version 3 with pages as id list "
            "and pages/{id}/page.json files. Migrate the project folder."
        )

    for page_id in page_ids:
        pj = root / "pages" / page_id / "page.json"
        if not pj.is_file():
            raise ProjectLoadError(f"Missing page file: {pj}")
        raw = json.loads(pj.read_text(encoding="utf-8"))
        pages[page_id] = _page_from_json(raw, page_id=page_id)

    # Apply root-level page_pairs if present
    for pair in data.get("page_pairs") or []:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        a, b = str(pair[0]), str(pair[1])
        if a in pages and b in pages:
            pages[a].pair_with = b
            pages[b].pair_with = a

    for page_id, page in pages.items():
        other_id = page.pair_with
        if not other_id or other_id not in pages:
            page.pair_with = None
            continue
        pages[other_id].pair_with = page_id

    project = Project(
        name=str(data.get("name") or root.name),
        root=root,
        runtime=runtime,
        pages=pages,
        detect_files={},
        click_files={},
        macros=macros,
        var_defaults=dict(data.get("vars") or {}),
    )
    for page in project.pages.values():
        sync_page_asset_maps(project, page)
    rebuild_resource_index(project)
    return project


def project_to_dict(project: Project) -> dict[str, Any]:
    """Root project.json only (no embedded page trees)."""
    rt = project.runtime
    pairs: list[list[str]] = []
    seen: set[frozenset[str]] = set()
    for page in project.pages.values():
        if not page.pair_with:
            continue
        key = frozenset({page.page_id, page.pair_with})
        if len(key) == 2 and key not in seen:
            seen.add(key)
            a, b = sorted(key)
            pairs.append([a, b])

    macros_out = [
        {
            "id": m.id,
            "name": m.name,
            "scope": m.scope,
            "steps": _steps_to_json(m.steps),
        }
        for m in project.macros.values()
    ]

    out: dict[str, Any] = {
        "name": project.name,
        "version": PROJECT_FORMAT_VERSION,
        "runtime": {
            "match_threshold": rt.match_threshold,
            "poll_interval": rt.poll_interval,
            "action_delay": rt.action_delay,
            "action_cooldown": rt.action_cooldown,
            "state_conf_margin": rt.state_conf_margin,
            "state_near": rt.state_near,
            "page_pair_margin": rt.page_pair_margin,
            "page_detect_near": rt.page_detect_near,
            "ref_width": rt.ref_width,
            "ref_height": rt.ref_height,
            "verbose_log": rt.verbose_log,
            "allow_redecide_during_action": rt.allow_redecide_during_action,
            "log_language": rt.log_language,
            "hotkeys": rt.hotkeys,
        },
        "macros": macros_out,
        "pages": list(project.pages.keys()),
        "page_pairs": pairs,
    }
    if project.var_defaults:
        out["vars"] = project.var_defaults
    return out


def save_project(project: Project) -> Path:
    rebuild_resource_index(project)
    (project.root / "pages").mkdir(parents=True, exist_ok=True)
    for page in project.pages.values():
        ensure_page_asset_dirs(project, page.page_id)
        sync_page_asset_maps(project, page)
        pj = page_json_path(project, page.page_id)
        pj.parent.mkdir(parents=True, exist_ok=True)
        pj.write_text(
            json.dumps(page_to_dict(page), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    # Drop page folders no longer in the project
    pages_root = project.root / "pages"
    if pages_root.is_dir():
        keep = set(project.pages.keys())
        for child in list(pages_root.iterdir()):
            if child.is_dir() and child.name not in keep:
                shutil.rmtree(child, ignore_errors=True)
    path = project.root / "project.json"
    path.write_text(
        json.dumps(project_to_dict(project), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def new_blank_project(target_dir: str | Path, name: str = "Untitled Project") -> Path:
    root = Path(target_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "pages").mkdir(parents=True, exist_ok=True)
    project = Project(
        name=name,
        root=root,
        runtime=RuntimeConfig(),
        pages={},
        detect_files={},
        click_files={},
        macros={},
    )
    save_project(project)
    return root


def import_image_to_project(
    project: Project, src: str | Path, *, kind: str, logical_key: str
) -> str:
    """Legacy helper: store under pages/_shared/{kind}/ when no page context."""
    src_path = Path(src)
    if not src_path.exists():
        raise FileNotFoundError(src_path)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in logical_key)
    ext = src_path.suffix.lower() or ".png"
    rel = f"pages/_shared/{kind}/{safe}{ext}"
    dest = project.root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dest)
    return rel
