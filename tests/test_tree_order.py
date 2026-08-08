"""Sibling order drives priority; ELSE sinks to bottom."""

from screenflow.models import ActionStep, ScoreSpec, StateNode
from screenflow.tree_order import (
    normalize_sibling_order,
    normalize_tree,
    order_tree_from_priority,
    sort_siblings_by_priority,
)


def test_normalize_top_has_higher_priority():
    a = StateNode(id="a", name="a", score=ScoreSpec(key="a"))
    b = StateNode(id="b", name="b", score=ScoreSpec(key="b"))
    els = StateNode(id="e", name="e", is_else=True)
    sibs = [a, els, b]
    normalize_sibling_order(sibs)
    assert [n.id for n in sibs] == ["a", "b", "e"]
    assert a.priority > b.priority
    assert els.priority == 0


def test_sort_by_priority_then_normalize():
    a = StateNode(id="a", priority=1, score=ScoreSpec(key="a"))
    b = StateNode(id="b", priority=50, score=ScoreSpec(key="b"))
    sibs = [a, b]
    sort_siblings_by_priority(sibs)
    assert sibs[0].id == "b"
    assert sibs[0].priority > sibs[1].priority


def test_order_tree_from_priority_nested():
    leaf = StateNode(id="leaf", priority=1, score=ScoreSpec(key="l"))
    high = StateNode(id="high", priority=9, score=ScoreSpec(key="h"))
    branch = StateNode(id="br", priority=5, children=[leaf, high])
    roots = [branch]
    order_tree_from_priority(roots)
    assert roots[0].children[0].id == "high"
    assert roots[0].children[0].priority > roots[0].children[1].priority


def test_normalize_tree_clears_branch_actions():
    child = StateNode(id="c", score=ScoreSpec(key="c"))
    parent = StateNode(
        id="p",
        actions=[ActionStep(op="wait", target=0.1)],
        children=[child],
    )
    normalize_tree([parent])
    assert parent.actions == []
