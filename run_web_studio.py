# -*- coding: utf-8 -*-
"""Launch ScreenFlow Web Studio (API + Vite dev, or API + built UI)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ScreenFlow Web Studio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Also start Vite dev server (npm run dev) and open it",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open a browser",
    )
    parser.add_argument(
        "--no-tray",
        action="store_true",
        help="Do not show the system tray icon",
    )
    args = parser.parse_args(argv)

    dist = ROOT / "web" / "dist"
    serve_ui = dist.is_dir() and not args.dev

    if serve_ui:
        from studio_api.app import mount_ui

        mount_ui()
    else:
        from studio_api.app import add_api_root_hint

        add_api_root_hint()

    studio_url = (
        "http://127.0.0.1:5173" if args.dev else f"http://{args.host}:{args.port}"
    )
    from studio_api import lifecycle

    lifecycle.configure(studio_url=studio_url)

    vite_proc: subprocess.Popen | None = None
    if args.dev:
        print(
            f"API  http://{args.host}:{args.port}\n"
            f"UI   http://127.0.0.1:5173/  ← open this in the browser",
            flush=True,
        )
        web = ROOT / "web"
        npm = shutil_which("npm")
        if not npm:
            print("npm not found; start Vite manually in web/", file=sys.stderr)
        else:
            vite_proc = subprocess.Popen(
                [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
                cwd=str(web),
                env={**os.environ},
            )
            time.sleep(1.5)
            if not args.no_open:
                webbrowser.open("http://127.0.0.1:5173")
    elif not args.no_open:
        webbrowser.open(f"http://{args.host}:{args.port}")

    import uvicorn

    # Windowed exe: stdout/stderr may be None; uvicorn ColourizedFormatter needs isatty().
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    use_tray = not args.no_tray and sys.platform == "win32"
    if use_tray:
        try:
            from studio_api.tray_host import start_tray

            start_tray()
        except Exception as exc:
            print(f"tray unavailable: {exc}", file=sys.stderr)

    config = uvicorn.Config(
        "studio_api.app:app",
        host=args.host,
        port=args.port,
        reload=False,
        use_colors=False,
    )
    server = uvicorn.Server(config)
    lifecycle.set_server(server)

    try:
        server.run()
    finally:
        if use_tray:
            try:
                from studio_api.tray_host import stop_tray

                stop_tray()
            except Exception:
                pass
        if vite_proc and vite_proc.poll() is None:
            vite_proc.terminate()
    return 0


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
