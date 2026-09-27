"""Run one project script in a short-lived child process."""

from __future__ import annotations

import contextlib
import importlib.util
import json
import sys
from pathlib import Path


def main(request_path: str, response_path: str) -> int:
    response: dict[str, object]
    try:
        request = json.loads(Path(request_path).read_text(encoding="utf-8"))
        project_root = Path(request["project_root"]).resolve()
        script = Path(request["script"]).resolve()
        if not script.is_relative_to(project_root) or not script.is_file():
            raise ValueError("script path escapes project")
        spec = importlib.util.spec_from_file_location("sf_user_script", script)
        if spec is None or spec.loader is None:
            raise ValueError("cannot load script")
        module = importlib.util.module_from_spec(spec)
        messages: list[str] = []
        variables = dict(request.get("vars") or {})
        with contextlib.redirect_stdout(sys.stderr):
            spec.loader.exec_module(module)
            run = getattr(module, "run", None)
            if not callable(run):
                raise ValueError("script missing run(ctx, params)")
            result = run(
                {
                    "project_root": str(project_root),
                    "page_id": request.get("page_id"),
                    "vars": variables,
                    "log": lambda msg: messages.append(str(msg)),
                },
                request.get("params") or {},
            )
        response = {
            "ok": True,
            "abort": result == "abort_pack",
            "vars": variables,
            "logs": messages,
        }
    except Exception as exc:
        response = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    Path(response_path).write_text(json.dumps(response), encoding="utf-8")
    return 0 if response["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
