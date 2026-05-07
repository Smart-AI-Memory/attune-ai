"""CLI entrypoint for ``attune ops``."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the `ops` subparser on the main attune CLI parser."""
    parser = subparsers.add_parser(
        "ops",
        help="Launch the operations dashboard (workflows, telemetry, memory)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port (default: 8765)",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project to inspect (default: cwd)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't auto-open the browser on startup",
    )
    parser.add_argument(
        "--allow-run",
        action="store_true",
        help="Enable workflow execution from the dashboard (default: read-only)",
    )


def cmd_ops(args: argparse.Namespace) -> int:
    """Run the dashboard server (blocking)."""
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        print(
            "attune ops requires extra dependencies.\n"
            "Install them with:  pip install 'attune-ai[ops]'",
            file=sys.stderr,
        )
        return 2

    from attune.ops.config import build_config
    from attune.ops.server import create_app

    config = build_config(
        project_root=args.project_root,
        host=args.host,
        port=args.port,
        allow_run=args.allow_run,
    )
    app = create_app(config)

    url = f"http://{config.host}:{config.port}"
    print(f"attune ops → {url}")
    print(f"  project: {config.project_root}")
    print(f"  attune-home: {config.attune_home}")
    print(f"  allow-run: {'on' if config.allow_run else 'off (read-only)'}")

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            # INTENTIONAL: best-effort browser launch; don't block the server.
            pass

    import uvicorn

    uvicorn.run(app, host=config.host, port=config.port, log_level="info")
    return 0


def main() -> int:
    """Standalone entry: ``python -m attune.ops``."""
    parser = argparse.ArgumentParser(prog="attune-ops")
    sub = parser.add_subparsers(dest="command")
    add_subparser(sub)
    args = parser.parse_args(["ops", *sys.argv[1:]])
    return cmd_ops(args)


if __name__ == "__main__":
    raise SystemExit(main())
