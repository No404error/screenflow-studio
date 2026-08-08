"""Sibling / tree display order helpers (ELSE last; priority from order)."""

from __future__ import annotations

from screenflow.models import StateNode


def normalize_sibling_order(siblings: list[StateNode]) -> None:
    """ELSE lines sink to bottom; priority = top-high among non-ELSE (…, 30, 20, 10)."""
    else_nodes = [n for n in siblings if n.is_else]
    others = [n for n in siblings if not n.is_else]
    siblings[:] = others + else_nodes
    n = len(others)
    for i, node in enumerate(others):
        node.priority = (n - i) * 10
    for node in else_nodes:
        node.priority = 0


def sort_siblings_by_priority(siblings: list[StateNode]) -> None:
    """After an explicit priority edit: sort by number, then rewrite from order."""
    else_nodes = [n for n in siblings if n.is_else]
    others = [n for n in siblings if not n.is_else]
    others.sort(key=lambda n: (n.priority, n.id), reverse=True)
    siblings[:] = others + else_nodes
    normalize_sibling_order(siblings)


def normalize_tree(roots: list[StateNode]) -> None:
    normalize_sibling_order(roots)
    for node in roots:
        if node.children:
            node.actions = []
            node.post = None
            normalize_tree(node.children)


def order_tree_from_priority(roots: list[StateNode]) -> None:
    """On load: display order follows stored priority, then rewrite clean priorities."""

    def walk(sibs: list[StateNode]) -> None:
        else_nodes = [n for n in sibs if n.is_else]
        others = [n for n in sibs if not n.is_else]
        others.sort(key=lambda n: (n.priority, n.id), reverse=True)
        sibs[:] = others + else_nodes
        for node in sibs:
            if node.children:
                walk(node.children)
        normalize_sibling_order(sibs)

    walk(roots)
    normalize_tree(roots)
