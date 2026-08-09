"""python -m studio_api — start Web Studio API (+ optional built UI)."""

from __future__ import annotations

import argparse
import sys

import uvicorn

from studio_api import lifecycle


def main() -> None:
    parser = argparse.ArgumentParser(description="ScreenFlow Web Studio API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument(
        "--serve-ui",
        action="store_true",
        help="Serve web/dist static files at /",
    )
    parser.add_argument(
        "--no-tray",
        action="store_true",
        help="Do not show the system tray icon",
    )
    args = parser.parse_args()

    if args.serve_ui:
        from studio_api.app import mount_ui

        mount_ui()
    else:
        from studio_api.app import add_api_root_hint

        add_api_root_hint()

    lifecycle.configure(studio_url=f"http://{args.host}:{args.port}")

    if not args.no_tray and sys.platform == "win32":
        try:
            from studio_api.tray_host import start_tray

            start_tray()
        except Exception:
            pass

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
        try:
            from studio_api.tray_host import stop_tray

            stop_tray()
        except Exception:
            pass


if __name__ == "__main__":
    main()
