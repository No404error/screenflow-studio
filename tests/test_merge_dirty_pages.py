"""Mirror of web/src/utils/mergeProject.ts mergeDirtyPageDocs semantics."""

from __future__ import annotations


def merge_dirty_page_docs(local: dict, server: dict) -> dict:
    dirty_keys = (
        "name",
        "detect_priority",
        "pair_with",
        "decide_params",
        "default_post",
        "state_tree",
    )
    out = {**server, "page_docs": dict(server.get("page_docs") or {})}
    for pid, local_page in (local.get("page_docs") or {}).items():
        server_page = out["page_docs"].get(pid)
        if not server_page:
            continue
        merged = dict(server_page)
        for key in dirty_keys:
            if key in local_page:
                merged[key] = local_page[key]
        out["page_docs"][pid] = merged
    if local.get("runtime"):
        out["runtime"] = {**(server.get("runtime") or {}), **local["runtime"]}
    if local.get("var_schema") is not None:
        out["var_schema"] = dict(local["var_schema"])
    if local.get("vars") is not None:
        out["vars"] = dict(local["vars"])
    if local.get("macros") is not None:
        out["macros"] = local["macros"]
    if local.get("name"):
        out["name"] = local["name"]
    return out


def test_merge_keeps_local_page_name_and_takes_server_features():
    local = {
        "name": "LocalProj",
        "page_docs": {
            "p": {
                "id": "p",
                "name": "Edited Name",
                "detect_priority": 9,
                "features": {"old": {"id": "old"}},
                "state_tree": [{"id": "c1", "name": "local"}],
            }
        },
        "runtime": {"match_threshold": 0.9},
    }
    server = {
        "name": "ServerProj",
        "page_docs": {
            "p": {
                "id": "p",
                "name": "Server Name",
                "detect_priority": 0,
                "features": {"new": {"id": "new", "visual_id": "v1"}},
                "visuals": {"v1": {"id": "v1", "asset": "a.png"}},
                "state_tree": [],
            }
        },
        "runtime": {"match_threshold": 0.72, "poll_interval": 0.5},
    }
    out = merge_dirty_page_docs(local, server)
    assert out["name"] == "LocalProj"
    assert out["page_docs"]["p"]["name"] == "Edited Name"
    assert out["page_docs"]["p"]["detect_priority"] == 9
    assert out["page_docs"]["p"]["features"] == {"new": {"id": "new", "visual_id": "v1"}}
    assert out["page_docs"]["p"]["visuals"] == {"v1": {"id": "v1", "asset": "a.png"}}
    assert out["page_docs"]["p"]["state_tree"] == [{"id": "c1", "name": "local"}]
    assert out["runtime"]["match_threshold"] == 0.9
    assert out["runtime"]["poll_interval"] == 0.5
