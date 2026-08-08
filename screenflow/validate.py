from __future__ import annotations

from dataclasses import dataclass

from screenflow.assets import list_page_assets, resolve_asset_path, sync_page_asset_maps
from screenflow.models import (
    ActionStep,
    PostListen,
    Project,
    StateNode,
    normalize_post_mode,
)
from screenflow.project import iter_tree


@dataclass
class Issue:
    level: str  # error | warning
    text: str


def _check_else_count(nodes: list[StateNode], where: str, t) -> list[Issue]:
    issues: list[Issue] = []
    else_n = sum(1 for n in nodes if n.is_else)
    if else_n > 1:
        issues.append(Issue("error", t("val_else_dup", where=where)))
    for n in nodes:
        if n.children:
            issues.extend(
                _check_else_count(
                    n.children, f"{where}/{n.display_name()}", t
                )
            )
    return issues


def _check_scoreless(nodes: list[StateNode], where: str, t) -> list[Issue]:
    """Non-ELSE nodes competing need a score (sole unscored should already be ELSE)."""
    issues: list[Issue] = []
    for n in nodes:
        if not n.is_else and n.score is None:
            issues.append(
                Issue(
                    "error",
                    t(
                        "val_scoreless",
                        where=where,
                        node=n.display_name(),
                    ),
                )
            )
        if n.children:
            issues.extend(
                _check_scoreless(
                    n.children, f"{where}/{n.display_name()}", t
                )
            )
    return issues


def _check_post_listen(
    post: PostListen | None,
    where: str,
    t,
    *,
    project: Project | None = None,
    page_id: str | None = None,
) -> list[Issue]:
    if post is None:
        return []
    issues: list[Issue] = []
    raw_mode = (post.mode or "").strip().lower()
    if raw_mode and raw_mode not in (
        "once",
        "until_page",
        "until_case",
        "frames",
        "until_miss",
    ):
        issues.append(
            Issue("error", t("val_post_mode", where=where, mode=str(post.mode)))
        )
    mode = normalize_post_mode(post.mode)
    # until_page may use an empty tree (wait for page change only).
    if not post.tree and mode != "until_page":
        issues.append(Issue("error", t("val_post_empty", where=where)))
    if mode == "until_case" and post.tree:
        if not any(n.is_else for n in post.tree):
            issues.append(
                Issue("warning", t("val_post_until_case_else", where=where))
            )
    if mode == "frames":
        if post.frames is None or int(post.frames) < 1:
            issues.append(Issue("error", t("val_frames_missing", where=where)))
    if post.settle < 0:
        issues.append(Issue("error", t("val_post_settle", where=where)))
    issues.extend(
        _check_tree_rules(
            post.tree,
            f"{where}/post",
            t,
            project=project,
            page_id=page_id,
        )
    )
    return issues


def _check_score_assets(
    nodes: list[StateNode],
    *,
    project: Project,
    page_id: str,
    where: str,
    t,
) -> list[Issue]:
    """Score image keys must exist in the page's chosen library."""
    detect_names = {a.name for a in list_page_assets(project, page_id, "detect")}
    click_names = {a.name for a in list_page_assets(project, page_id, "click")}
    issues: list[Issue] = []
    for n in iter_tree(nodes):
        if n.is_else or n.score is None:
            continue
        if (n.score.kind or "template") == "constant":
            continue
        key = (n.score.key or "").strip()
        src = n.score.source or "detect"
        lib = detect_names if src == "detect" else click_names
        lib_label = t("st_src_detect") if src == "detect" else t("st_src_click")
        path = f"{where}/{n.display_name()}"
        if not key:
            issues.append(
                Issue(
                    "error",
                    t("val_score_key_empty", where=path, node=n.display_name()),
                )
            )
        elif key not in lib:
            issues.append(
                Issue(
                    "error",
                    t(
                        "val_score_missing",
                        where=path,
                        node=n.display_name(),
                        image=key,
                        lib=lib_label,
                    ),
                )
            )
    return issues


def _check_tree_rules(
    nodes: list[StateNode],
    where: str,
    t,
    *,
    project: Project | None = None,
    page_id: str | None = None,
) -> list[Issue]:
    issues = _check_else_count(nodes, where, t)
    issues.extend(_check_scoreless(nodes, where, t))
    if project is not None and page_id is not None:
        issues.extend(
            _check_score_assets(
                nodes, project=project, page_id=page_id, where=where, t=t
            )
        )
    for n in iter_tree(nodes):
        if not n.is_leaf():
            if n.actions:
                issues.append(
                    Issue(
                        "error",
                        t("val_branch_actions", node=n.display_name(), where=where),
                    )
                )
            if n.post is not None:
                issues.append(
                    Issue(
                        "error",
                        t("val_branch_post", node=n.display_name(), where=where),
                    )
                )
        if n.post is not None:
            issues.extend(
                _check_post_listen(
                    n.post,
                    f"{where}/{n.display_name()}",
                    t,
                    project=project,
                    page_id=page_id,
                )
            )
    return issues


def _walk_steps_refs(
    steps: list[ActionStep],
    *,
    project: Project,
    page_name: str,
    state: str,
    click_keys: set[str],
    issues: list[Issue],
    t,
    click_missing_level: str = "error",
    click_missing_key: str = "val_click_missing",
) -> None:
    for i, step in enumerate(steps, start=1):
        if step.op == "click":
            target = str(step.target or "").strip()
            if not target:
                issues.append(
                    Issue(
                        "error",
                        t(
                            "val_click_empty",
                            page=page_name,
                            state=state,
                            step=i,
                        ),
                    )
                )
            elif target not in click_keys:
                issues.append(
                    Issue(
                        click_missing_level,
                        t(
                            click_missing_key,
                            page=page_name,
                            state=state,
                            step=i,
                            target=target,
                            macro=state,
                        ),
                    )
                )
        elif step.op == "macro":
            mid = str(step.target or "").strip()
            if mid and mid not in project.macros:
                issues.append(
                    Issue(
                        "warning",
                        t(
                            "val_macro_missing",
                            page=page_name,
                            state=state,
                            step=i,
                            macro=mid,
                        ),
                    )
                )
        elif step.op == "script":
            rel = str(step.target or "").strip()
            if not rel:
                issues.append(
                    Issue(
                        "warning",
                        t(
                            "val_script_missing",
                            page=page_name,
                            state=state,
                            step=i,
                            script="(empty)",
                        ),
                    )
                )
            else:
                path = (project.root / rel).resolve()
                root = project.root.resolve()
                if not str(path).startswith(str(root)) or not path.is_file():
                    issues.append(
                        Issue(
                            "warning",
                            t(
                                "val_script_missing",
                                page=page_name,
                                state=state,
                                step=i,
                                script=rel,
                            ),
                        )
                    )


def validate_project_structure(project: Project, t) -> list[Issue]:
    issues: list[Issue] = []
    for page_id, page in project.pages.items():
        sync_page_asset_maps(project, page)
        name = page.display_name()
        issues.extend(
            _check_tree_rules(
                page.state_tree,
                name,
                t,
                project=project,
                page_id=page_id,
            )
        )
        if page.default_post:
            issues.extend(
                _check_post_listen(
                    page.default_post,
                    f"{name}/default_post",
                    t,
                    project=project,
                    page_id=page_id,
                )
            )
    return issues


def validate_for_start(project: Project, t) -> list[Issue]:
    """Blocking errors and soft warnings before Start."""
    issues: list[Issue] = []
    issues.extend(validate_project_structure(project, t))
    if not project.pages:
        issues.append(Issue("error", t("val_no_pages")))
        return issues

    for page_id, page in project.pages.items():
        sync_page_asset_maps(project, page)
        name = page.display_name()
        detect_assets = list_page_assets(project, page_id, "detect")
        detect_ok = bool(detect_assets) or resolve_asset_path(
            project, page.detect_relpath
        ).is_file()
        if not detect_ok:
            issues.append(Issue("error", t("val_no_detect", page=name)))

        click_keys = set(page.click_map.keys())

        def walk_actions(node: StateNode, path: str) -> None:
            if node.is_leaf():
                steps = node.actions
                if not steps and not node.is_else:
                    issues.append(
                        Issue(
                            "warning",
                            t(
                                "val_no_actions",
                                page=name,
                                state=path or node.display_name(),
                            ),
                        )
                    )
                _walk_steps_refs(
                    steps,
                    project=project,
                    page_name=name,
                    state=path or node.display_name(),
                    click_keys=click_keys,
                    issues=issues,
                    t=t,
                )
                if node.post:
                    for pn in iter_tree(node.post.tree):
                        if pn.is_leaf():
                            _walk_steps_refs(
                                pn.actions,
                                project=project,
                                page_name=name,
                                state=f"{path or node.display_name()}/post/{pn.display_name()}",
                                click_keys=click_keys,
                                issues=issues,
                                t=t,
                            )
            for ch in node.children:
                walk_actions(
                    ch, f"{path}/{ch.display_name()}" if path else ch.display_name()
                )

        if not page.state_tree:
            issues.append(
                Issue("warning", t("val_no_actions", page=name, state="(empty tree)"))
            )
        for root in page.state_tree:
            walk_actions(root, root.display_name())

    # Macros: click targets may live on any page; missing → warning (edit still allowed)
    all_click_keys: set[str] = set()
    for page_id, page in project.pages.items():
        sync_page_asset_maps(project, page)
        all_click_keys.update(page.click_map.keys())
        all_click_keys.update(
            a.name for a in list_page_assets(project, page_id, "click")
        )

    for mid, macro in project.macros.items():
        _walk_steps_refs(
            macro.steps,
            project=project,
            page_name="(macros)",
            state=mid,
            click_keys=all_click_keys,
            issues=issues,
            t=t,
            click_missing_level="warning",
            click_missing_key="val_macro_click_missing",
        )

    return issues
