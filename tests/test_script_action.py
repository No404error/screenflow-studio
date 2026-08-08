"""ActionRunner._run_script success and abort_pack paths."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from screenflow.actions import ActionRunner
from screenflow.models import ActionStep, Project, RuntimeConfig


def _runner(tmp_path: Path, script_body: str) -> ActionRunner:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "job.py").write_text(script_body, encoding="utf-8")
    project = Project(
        name="t",
        root=tmp_path,
        runtime=RuntimeConfig(),
        pages={},
        detect_files={},
        click_files={},
    )
    return ActionRunner(
        project,
        matcher=MagicMock(),
        input_ctrl=MagicMock(),
        log=SimpleNamespace(
            info=MagicMock(),
            detail=MagicMock(),
            verbose=False,
            macro_label=lambda *_a, **_k: "m",
        ),
        is_running=lambda: True,
    )


def test_run_script_success(tmp_path):
    runner = _runner(
        tmp_path,
        "def run(ctx, params):\n    ctx['vars']['ok'] = True\n",
    )
    vars_: dict = {}
    assert runner._run_script("scripts/job.py", page_id="p", vars=vars_) is True
    assert vars_.get("ok") is True


def test_run_script_abort_pack(tmp_path):
    runner = _runner(tmp_path, "def run(ctx, params):\n    return 'abort_pack'\n")
    assert runner._run_script("scripts/job.py", page_id="p", vars={}) is False


def test_run_steps_script_abort_stops_pack(tmp_path):
    runner = _runner(tmp_path, "def run(ctx, params):\n    return 'abort_pack'\n")
    ok = runner.run_steps(
        [ActionStep("script", "scripts/job.py"), ActionStep("wait", 0.0)],
        MagicMock(),
        {},
        page_id="p",
        vars={},
    )
    assert ok is False


def test_run_script_receives_params(tmp_path):
    runner = _runner(
        tmp_path,
        "def run(ctx, params):\n    ctx['vars']['n'] = params.get('n')\n",
    )
    vars_: dict = {}
    assert (
        runner._run_script(
            "scripts/job.py",
            page_id="p",
            vars=vars_,
            params={"n": 7},
        )
        is True
    )
    assert vars_.get("n") == 7


def test_script_params_json_roundtrip():
    from screenflow.project import _steps_from_json, _steps_to_json

    steps = [ActionStep("script", "scripts/x.py", params={"a": 1, "b": "x"})]
    raw = _steps_to_json(steps)
    assert raw[0]["params"] == {"a": 1, "b": "x"}
    back = _steps_from_json(raw)
    assert back[0].params == {"a": 1, "b": "x"}


def test_unknown_macro_expand_aborts_pack(tmp_path):
    runner = _runner(tmp_path, "def run(ctx, params):\n    pass\n")
    ok = runner.run_steps(
        [ActionStep("macro", "missing_macro")],
        MagicMock(),
        {},
        page_id="p",
        vars={},
    )
    assert ok is False
