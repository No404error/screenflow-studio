"""Launch the engine runner, requesting admin on Windows when needed."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Same binary, second process (packaged ScreenFlow.exe --engine-runner …).
ENGINE_RUNNER_FLAG = "--engine-runner"


def is_admin() -> bool:
    if os.name == "nt":
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return True


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def runner_script() -> Path:
    return Path(__file__).resolve().parent.parent / "run_runner.py"


def runner_interpreter() -> str:
    """
    Interpreter used to spawn the Runner in development.

    On Windows prefer pythonw.exe (Windows subsystem) — python.exe always
    allocates a console; ShellExecute SW_HIDE does not reliably suppress it.
    """
    exe = Path(sys.executable)
    if os.name == "nt" and exe.name.lower() == "python.exe":
        candidate = exe.with_name("pythonw.exe")
        if candidate.is_file():
            return str(candidate)
    return str(exe)


# Back-compat alias for older imports / tests.
runner_executable = runner_interpreter


def runner_launch_parts(
    *,
    project: Path,
    host: str,
    port: int,
) -> tuple[str, list[str], str]:
    """
    Resolve how to start the Runner.

    Returns (executable, argv_after_exe, cwd).

    Packaged: relaunch ScreenFlow.exe with --engine-runner.
    Dev: pythonw + run_runner.py.
    """
    tail = [
        "--project",
        str(project.resolve()),
        "--host",
        host,
        "--port",
        str(port),
    ]
    if is_frozen():
        exe = Path(sys.executable).resolve()
        if not exe.is_file():
            raise FileNotFoundError(f"Frozen executable missing: {exe}")
        return str(exe), [ENGINE_RUNNER_FLAG, *tail], str(exe.parent)

    script = runner_script()
    if not script.is_file():
        raise FileNotFoundError(f"Runner script missing: {script}")
    return runner_interpreter(), [str(script), *tail], str(script.parent)


def launch_runner(
    *,
    project: Path,
    host: str,
    port: int,
    elevate: bool = True,
) -> subprocess.Popen | None:
    """
    Start the engine runner connecting back to host:port.

    Dev: pythonw + run_runner.py.
    Packaged: same ScreenFlow.exe with --engine-runner (UAC when needed).

    On Windows with elevate=True and not already admin, uses ShellExecuteW
    "runas" (UAC). Returns None when elevation was requested via ShellExecute
    (child handle not retained); returns Popen when started as a normal child.
    """
    executable, args_list, cwd = runner_launch_parts(
        project=project, host=host, port=port
    )

    need_uac = elevate and os.name == "nt" and not is_admin()
    if need_uac:
        import ctypes

        params = subprocess.list2cmdline(args_list)
        rc = int(
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                executable,
                params,
                cwd,
                0,  # SW_HIDE
            )
        )
        if rc <= 32:
            raise OSError(f"UAC launch failed (ShellExecute={rc})")
        return None

    kwargs: dict = {
        "cwd": cwd,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    return subprocess.Popen([executable, *args_list], **kwargs)
