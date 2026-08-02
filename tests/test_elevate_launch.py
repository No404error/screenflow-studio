"""Dev vs frozen runner launch resolution."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from studio.elevate import ENGINE_RUNNER_FLAG, runner_launch_parts, runner_script


def test_runner_launch_parts_dev(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    exe, args, cwd = runner_launch_parts(
        project=project, host="127.0.0.1", port=9
    )
    assert Path(exe).name.lower() in {"python.exe", "pythonw.exe"}
    assert Path(args[0]) == runner_script()
    assert args[1:] == [
        "--project",
        str(project.resolve()),
        "--host",
        "127.0.0.1",
        "--port",
        "9",
    ]
    assert Path(cwd) == runner_script().parent


def test_runner_launch_parts_frozen(tmp_path: Path):
    studio = tmp_path / "ScreenFlow.exe"
    studio.write_bytes(b"")
    project = tmp_path / "proj"
    project.mkdir()
    with mock.patch("studio.elevate.sys") as fake_sys:
        fake_sys.frozen = True
        fake_sys.executable = str(studio)
        exe, args, cwd = runner_launch_parts(
            project=project, host="127.0.0.1", port=42
        )
    assert Path(exe) == studio
    assert args == [
        ENGINE_RUNNER_FLAG,
        "--project",
        str(project.resolve()),
        "--host",
        "127.0.0.1",
        "--port",
        "42",
    ]
    assert cwd == str(tmp_path)
