from screenflow.compete import ScoredCandidate, compete, compete_page_pair
from screenflow.models import DecideParams


def test_compete_highest_score():
    params = DecideParams(threshold=0.5, near=0.05, margin=0.02)
    cands = [
        ScoredCandidate("a", 0.9, 1, label="a"),
        ScoredCandidate("b", 0.7, 10, label="b"),
    ]
    w, d = compete(cands, params)
    assert w and w.item == "a"


def test_compete_else_when_none_pass():
    params = DecideParams(threshold=0.9, near=0.05, margin=0.02)
    cands = [
        ScoredCandidate("a", 0.2, 1, label="a"),
        ScoredCandidate("e", 0.0, 0, is_else=True, label="else"),
    ]
    w, d = compete(cands, params)
    assert w and w.is_else and d.used_else


def test_compete_priority_in_margin():
    params = DecideParams(threshold=0.5, near=0.2, margin=0.15)
    cands = [
        ScoredCandidate("lowpri", 0.91, 1, label="lowpri"),
        ScoredCandidate("hipri", 0.90, 50, label="hipri"),
    ]
    w, d = compete(cands, params)
    assert w and w.item == "hipri"


def test_compete_abstain_when_close():
    params = DecideParams(
        threshold=0.5, near=0.2, margin=0.05, on_close="abstain"
    )
    cands = [
        ScoredCandidate("ready", 0.80, 30, label="ready"),
        ScoredCandidate("using", 0.78, 20, label="using"),
    ]
    w, d = compete(cands, params)
    assert w is None
    assert any("abstain" in x for x in d.eliminated)


def test_compete_abstain_falls_back_to_else():
    params = DecideParams(
        threshold=0.5, near=0.2, margin=0.05, on_close="abstain"
    )
    cands = [
        ScoredCandidate("ready", 0.80, 30, label="ready"),
        ScoredCandidate("using", 0.78, 20, label="using"),
        ScoredCandidate("e", 0.0, 0, is_else=True, label="else"),
    ]
    w, d = compete(cands, params)
    assert w is not None and w.is_else and d.used_else


def test_compete_abstain_clear_lead_still_wins():
    params = DecideParams(
        threshold=0.5, near=0.2, margin=0.05, on_close="abstain"
    )
    cands = [
        ScoredCandidate("ready", 0.90, 30, label="ready"),
        ScoredCandidate("using", 0.70, 20, label="using"),
    ]
    w, d = compete(cands, params)
    assert w and w.item == "ready"


def test_page_pair_shared():
    params = DecideParams(threshold=0.72, margin=0.03)
    win = compete_page_pair("a", 0.95, "b", 0.94, {"a": 0, "b": 100}, params, 0.72)
    assert win == "b"
