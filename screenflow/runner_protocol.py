"""Line-delimited JSON protocol between Studio and elevated Runner."""

from __future__ import annotations

import json
from typing import Any

# Studio → Runner
CMDS = frozenset({"start", "pause", "stop", "ping", "set_runtime"})

# Runner → Studio
EVENT_TYPES = frozenset({"ready", "log", "status", "error", "exited", "pong"})


def encode_message(obj: dict[str, Any]) -> bytes:
    """Serialize one message as a single UTF-8 line ending with \\n."""
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def decode_line(line: str | bytes) -> dict[str, Any] | None:
    """
    Parse one protocol line. Returns None for empty/invalid JSON or non-dict.
    Does not validate cmd/type membership (callers may use helpers).
    """
    if isinstance(line, bytes):
        try:
            line = line.decode("utf-8")
        except UnicodeDecodeError:
            return None
    text = line.strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def is_command(msg: dict[str, Any]) -> bool:
    cmd = msg.get("cmd")
    return isinstance(cmd, str) and cmd in CMDS


def is_event(msg: dict[str, Any]) -> bool:
    typ = msg.get("type")
    return isinstance(typ, str) and typ in EVENT_TYPES


def cmd_start() -> dict[str, Any]:
    return {"cmd": "start"}


def cmd_pause() -> dict[str, Any]:
    return {"cmd": "pause"}


def cmd_stop() -> dict[str, Any]:
    return {"cmd": "stop"}


def cmd_ping() -> dict[str, Any]:
    return {"cmd": "ping"}


def cmd_set_runtime(fields: dict[str, Any]) -> dict[str, Any]:
    return {"cmd": "set_runtime", "runtime": dict(fields)}


def event_ready(pid: int | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"type": "ready"}
    if pid is not None:
        out["pid"] = int(pid)
    return out


def event_log(text: str) -> dict[str, Any]:
    return {"type": "log", "text": str(text)}


def event_status(payload: dict[str, Any]) -> dict[str, Any]:
    out = {"type": "status"}
    out.update(payload)
    return out


def event_error(text: str) -> dict[str, Any]:
    return {"type": "error", "text": str(text)}


def event_exited(code: int = 0) -> dict[str, Any]:
    return {"type": "exited", "code": int(code)}


def event_pong() -> dict[str, Any]:
    return {"type": "pong"}
