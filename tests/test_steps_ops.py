"""StepsEditor preserves set_var / script / hold_key ops (no silent remap)."""

from screenflow.models import ActionStep
from screenflow.project import _steps_from_json, _steps_to_json
from studio.steps_editor import ADVANCED_OPS, COMMON_OPS, OPS


def test_ops_split_common_and_advanced():
    assert "hold_key" in COMMON_OPS
    assert "hold_space" not in OPS
    assert "set_var" in ADVANCED_OPS
    assert "clear_var" in ADVANCED_OPS
    assert "script" in ADVANCED_OPS
    assert OPS == COMMON_OPS + ADVANCED_OPS


def test_action_step_roundtrip_ops():
    steps = [
        ActionStep("set_var", "mode=farm"),
        ActionStep("clear_var", "mode"),
        ActionStep("script", "scripts/x.py"),
        ActionStep("hold_key", "space", hold=1.8),
    ]
    copied = [
        ActionStep(op=s.op, target=s.target, reason=s.reason, hold=s.hold)
        for s in steps
    ]
    assert [s.op for s in copied] == ["set_var", "clear_var", "script", "hold_key"]
    assert copied[-1].hold == 1.8
    assert all(s.op in OPS for s in copied)


def test_hold_key_json_roundtrip():
    raw = [{"op": "hold_key", "target": "space", "hold": 1.8, "reason": "End1"}]
    steps = _steps_from_json(raw)
    assert steps[0].op == "hold_key"
    assert steps[0].target == "space"
    assert steps[0].hold == 1.8
    out = _steps_to_json(steps)
    assert out == raw
