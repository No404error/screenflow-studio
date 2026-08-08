from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

MAX_RECENT = 12
DEFAULT_SPLITTER_SIZES = [280, 520, 360]
RUNNER_ELEVATE = "elevate"
RUNNER_INLINE = "inline"


def config_dir() -> Path:
    """Per-user config directory (e.g. ~/.screenflow)."""
    return Path.home() / ".screenflow"


def settings_path() -> Path:
    return config_dir() / "ui.json"


def legacy_settings_path() -> Path:
    """Old in-repo settings file (pre user-config migration)."""
    return Path(__file__).resolve().parent.parent / ".screenflow_ui.json"


def _ensure_config_dir() -> Path:
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def migrate_legacy_settings_if_needed() -> bool:
    """
    Copy repo-local .screenflow_ui.json → ~/.screenflow/ui.json once.
    Returns True if a migration write happened.
    """
    dest = settings_path()
    if dest.exists():
        return False
    src = legacy_settings_path()
    if not src.exists():
        return False
    data = _read_json_file(src)
    if not data:
        return False
    _ensure_config_dir()
    save_ui_settings(data)
    try:
        bak = src.with_suffix(src.suffix + ".migrated")
        if not bak.exists():
            shutil.copy2(src, bak)
    except Exception:
        pass
    return True


def load_ui_settings() -> dict[str, Any]:
    migrate_legacy_settings_if_needed()
    return _read_json_file(settings_path())


def save_ui_settings(data: dict[str, Any]) -> None:
    _ensure_config_dir()
    path = settings_path()
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def update_ui_settings(**kwargs: Any) -> dict[str, Any]:
    data = load_ui_settings()
    data.update(kwargs)
    save_ui_settings(data)
    return data


def get_recent() -> list[dict[str, str]]:
    raw = load_ui_settings().get("recent") or []
    out: list[dict[str, str]] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip()
        if not path:
            continue
        out.append(
            {
                "path": path,
                "name": str(item.get("name") or Path(path).name),
            }
        )
    return out


def touch_recent(path: str | Path, name: str) -> None:
    root = str(Path(path).resolve())
    entries = [e for e in get_recent() if e["path"] != root]
    entries.insert(0, {"path": root, "name": name.strip() or Path(root).name})
    update_ui_settings(recent=entries[:MAX_RECENT])


def remove_recent(path: str | Path) -> None:
    root = str(Path(path).resolve())
    entries = [e for e in get_recent() if e["path"] != root]
    update_ui_settings(recent=entries)


def clear_recent() -> None:
    update_ui_settings(recent=[])


def get_reopen_last_project() -> bool:
    val = load_ui_settings().get("reopen_last_project", True)
    return bool(val)


def default_runner_mode() -> str:
    return RUNNER_ELEVATE if os.name == "nt" else RUNNER_INLINE


def get_runner_mode() -> str:
    """
    Engine process mode: elevate (external UAC runner) or inline (in-process).
    Env SCREENFLOW_RUNNER=inline|elevate overrides ui.json.
    """
    env = (os.environ.get("SCREENFLOW_RUNNER") or "").strip().lower()
    if env in (RUNNER_ELEVATE, RUNNER_INLINE):
        return env
    val = load_ui_settings().get("runner_mode")
    if val in (RUNNER_ELEVATE, RUNNER_INLINE):
        return str(val)
    return default_runner_mode()


def set_runner_mode(mode: str) -> None:
    if mode not in (RUNNER_ELEVATE, RUNNER_INLINE):
        raise ValueError(f"invalid runner_mode: {mode}")
    update_ui_settings(runner_mode=mode)


def set_reopen_last_project(enabled: bool) -> None:
    update_ui_settings(reopen_last_project=bool(enabled))


def resolve_reopen_project_path() -> Path | None:
    """
    First recent entry that still looks like a ScreenFlow project.
    Stale missing paths are pruned from the recent list.
    """
    if not get_reopen_last_project():
        return None
    stale: list[str] = []
    chosen: Path | None = None
    for entry in get_recent():
        root = Path(entry["path"])
        if (root / "project.json").is_file():
            chosen = root
            break
        stale.append(entry["path"])
    for path in stale:
        remove_recent(path)
    return chosen


def get_main_splitter_sizes() -> list[int] | None:
    raw = load_ui_settings().get("main_splitter_sizes")
    if not isinstance(raw, list) or len(raw) != 3:
        return None
    try:
        sizes = [max(80, int(x)) for x in raw]
    except (TypeError, ValueError):
        return None
    if sum(sizes) <= 0:
        return None
    return sizes


def set_main_splitter_sizes(sizes: list[int]) -> None:
    if len(sizes) != 3:
        return
    cleaned = [max(80, int(x)) for x in sizes]
    update_ui_settings(main_splitter_sizes=cleaned)


def get_window_geometry() -> str | None:
    val = load_ui_settings().get("window_geometry")
    if isinstance(val, str) and val.strip():
        return val.strip()
    return None


def set_window_geometry(geometry_b64: str) -> None:
    if not geometry_b64:
        return
    update_ui_settings(window_geometry=geometry_b64)


def get_last_dir(kind: str) -> str:
    data = load_ui_settings()
    key = f"last_dir_{kind}"
    val = str(data.get(key) or "").strip()
    if val and Path(val).is_dir():
        return val
    return str(Path.home())


def set_last_dir(kind: str, path: str | Path) -> None:
    p = Path(path)
    if p.is_file():
        p = p.parent
    if not p.is_dir():
        return
    update_ui_settings(**{f"last_dir_{kind}": str(p.resolve())})


def safe_folder_name(name: str, *, fallback: str = "Untitled Project") -> str:
    """Filesystem-safe folder name; keeps CJK characters."""
    bad = '<>:"/\\|?*'
    cleaned = "".join("_" if (c in bad or ord(c) < 32) else c for c in name.strip())
    cleaned = cleaned.rstrip(" .")
    return cleaned or fallback
