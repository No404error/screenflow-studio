from __future__ import annotations

from dataclasses import dataclass

from screenflow.assets import feature_link_ok
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


def _collect_feature_refs(nodes: list[StateNode]) -> set[str]:
    refs: set[str] = set()
    for n in iter_tree(nodes):
        if n.score is not None and (n.score.kind or "template") != "constant":
            key = (n.score.key or "").strip()
            if key:
                refs.add(key)
        for step in n.actions or []:
            if step.op == "click":
                target = str(step.target or "").strip()
                if target:
                    refs.add(target)
        if n.post:
            refs |= _collect_feature_refs(n.post.tree)
    return refs


def _check_score_features(
    nodes: list[StateNode],
    *,
    project: Project,
    page_id: str,
    where: str,
    t,
) -> list[Issue]:
    """Score keys must be 画面特征 ids on this page; unbound → error at structure time too."""
    page = project.pages[page_id]
    feature_ids = set(page.features.keys())
    lib_label = t("asset_features")
    issues: list[Issue] = []
    for n in iter_tree(nodes):
        if n.is_else or n.score is None:
            continue
        if (n.score.kind or "template") == "constant":
            continue
        key = (n.score.key or "").strip()
        path = f"{where}/{n.display_name()}"
        if not key:
            issues.append(
                Issue(
                    "error",
                    t("val_score_key_empty", where=path, node=n.display_name()),
                )
            )
        elif key not in feature_ids:
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
        elif not feature_link_ok(project, page, key):
            issues.append(
                Issue(
                    "error",
                    t(
                        "val_feature_unbound",
                        page=page.display_name(),
                        feature=page.features[key].display_name(),
                        where=path,
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
            _check_score_features(
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
    page_id: str | None,
    feature_ids: set[str],
    issues: list[Issue],
    t,
    click_missing_level: str = "error",
    click_missing_key: str = "val_click_missing",
) -> None:
    page = project.pages.get(page_id) if page_id else None
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
            elif target not in feature_ids:
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
            elif page is not None and not feature_link_ok(project, page, target):
                issues.append(
                    Issue(
                        "error",
                        t(
                            "val_feature_unbound",
                            page=page_name,
                            feature=page.features[target].display_name(),
                            where=f"{state}/step {i}",
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
                root = project.root.resolve()
                path = (root / rel).resolve()
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
        name = page.display_name()
        if not feature_link_ok(project, page, page.recognize_with):
            issues.append(Issue("error", t("val_no_detect", page=name)))

        feature_ids = set(page.features.keys())
        refs = _collect_feature_refs(page.state_tree)
        if page.default_post:
            refs |= _collect_feature_refs(page.default_post.tree)
        if page.recognize_with:
            refs.add(page.recognize_with)

        for fid, feat in page.features.items():
            if fid in refs:
                continue
            if not feature_link_ok(project, page, fid):
                issues.append(
                    Issue(
                        "warning",
                        t(
                            "val_feature_unbound_unused",
                            page=name,
                            feature=feat.display_name(),
                        ),
                    )
                )

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
                    page_id=page_id,
                    feature_ids=feature_ids,
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
                                page_id=page_id,
                                feature_ids=feature_ids,
                                issues=issues,
                                t=t,
                            )
            for ch in node.children:
                walk_actions(
                    ch, f"{path}/{ch.display_name()}" if path else ch.display_name()
                )

        if not page.state_tree:
            issues.append(
                Issue("warning", t("val_no_actions", page=name, state=t("val_empty_tree")))
            )
        for root in page.state_tree:
            walk_actions(root, root.display_name())

    # Macros: feature ids resolve on the page where the macro runs.
    all_feature_ids: set[str] = set()
    for page in project.pages.values():
        all_feature_ids.update(page.features.keys())

    for mid, macro in project.macros.items():
        _walk_steps_refs(
            macro.steps,
            project=project,
            page_name="(macros)",
            state=mid,
            page_id=None,
            feature_ids=all_feature_ids,
            issues=issues,
            t=t,
            click_missing_level="warning",
            click_missing_key="val_macro_click_missing",
        )
        for step in macro.steps:
            if step.op != "click":
                continue
            target = str(step.target or "").strip()
            if not target:
                continue
            for page in project.pages.values():
                if target not in page.features:
                    continue
                if not feature_link_ok(project, page, target):
                    issues.append(
                        Issue(
                            "error",
                            t(
                                "val_feature_unbound",
                                page=page.display_name(),
                                feature=page.features[target].display_name(),
                                where=f"macro/{mid}",
                            ),
                        )
                    )

    return issues
