"""Migrate a ScreenFlow project from monolithic project.json (v2) to v3 split pages."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def migrate(root: Path) -> None:
    root = root.resolve()
    meta = root / "project.json"
    data = json.loads(meta.read_text(encoding="utf-8"))
    raw_pages = data.get("pages") or []
    if not raw_pages:
        print("No pages to migrate")
    if raw_pages and all(isinstance(x, str) for x in raw_pages):
        print("Already v3 (pages are ids)")
        return
    if not raw_pages or not isinstance(raw_pages[0], dict):
        raise SystemExit(f"Unexpected pages format in {meta}")

    pages_root = root / "pages"
    pages_root.mkdir(parents=True, exist_ok=True)
    page_ids: list[str] = []
    pairs: list[list[str]] = []
    seen: set[frozenset[str]] = set()

    for raw in raw_pages:
        page_id = str(raw["id"])
        page_ids.append(page_id)
        dest = pages_root / page_id
        dest.mkdir(parents=True, exist_ok=True)
        # Move images from templates/pages/{id} if present
        old = root / "templates" / "pages" / page_id
        if old.is_dir():
            for kind in ("detect", "click"):
                src_kind = old / kind
                dst_kind = dest / kind
                if src_kind.is_dir():
                    dst_kind.mkdir(parents=True, exist_ok=True)
                    for f in src_kind.iterdir():
                        if f.is_file():
                            target = dst_kind / f.name
                            if not target.exists():
                                shutil.copy2(f, target)
        page_path = dest / "page.json"
        # Drop pair_with into page.json; also collect pairs for root
        if raw.get("pair_with"):
            a, b = page_id, str(raw["pair_with"])
            key = frozenset({a, b})
            if len(key) == 2 and key not in seen:
                seen.add(key)
                pairs.append(sorted(key))
        # Rewrite legacy templates/pages/{id}/… → pages/{id}/…
        legacy_prefix = f"templates/pages/{page_id}/"
        new_prefix = f"pages/{page_id}/"

        def _rewrite(val: object) -> object:
            if isinstance(val, str) and val.replace("\\", "/").startswith(legacy_prefix):
                return new_prefix + val.replace("\\", "/")[len(legacy_prefix) :]
            if isinstance(val, dict):
                return {k: _rewrite(v) for k, v in val.items()}
            if isinstance(val, list):
                return [_rewrite(v) for v in val]
            return val

        page_data = _rewrite(raw)
        page_path.write_text(
            json.dumps(page_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"  wrote {page_path}")

    data["version"] = 3
    data["pages"] = page_ids
    data["page_pairs"] = pairs
    # backup old monolith
    bak = root / "project.json.v2.bak"
    if not bak.exists():
        shutil.copy2(meta, bak)
    meta.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Updated {meta} (backup {bak})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.migrate_project_v3 <project_dir>")
        raise SystemExit(2)
    migrate(Path(sys.argv[1]))
