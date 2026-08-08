"""python -m studio_api — start Web Studio API (+ optional built UI)."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="ScreenFlow Web Studio API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument(
        "--serve-ui",
        action="store_true",
        help="Serve web/dist static files at /",
    )
    args = parser.parse_args()

    if args.serve_ui:
        from studio_api.app import mount_ui

        mount_ui()
    else:
        from studio_api.app import add_api_root_hint

        add_api_root_hint()

    uvicorn.run(
        "studio_api.app:app",
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
