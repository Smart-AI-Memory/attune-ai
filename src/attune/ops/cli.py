"""CLI entrypoint for ``attune ops``."""

from __future__ import annotations

import argparse
import os
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
        default=int(os.environ.get("PORT") or 8765),
        help="Port (default: $PORT env var if set, else 8765)",
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
        "--read-only",
        action="store_true",
        help="Disable workflow execution from the dashboard (default: runs enabled)",
    )
    parser.add_argument(
        "--specs-root",
        type=Path,
        action="append",
        default=None,
        metavar="DIR",
        help=(
            "Directory containing spec subdirectories (each with"
            " decisions.md/tasks.md/etc.). Repeatable for federated"
            " listing across multiple project roots. Default:"
            " <project-root>/docs/specs/"
        ),
    )
    parser.add_argument(
        "--trusted-host",
        action="append",
        default=None,
        metavar="HOST",
        help=(
            "Repeatable. Hostname (optionally with :port) accepted in"
            " the Host: header. Use when reaching the dashboard via a"
            " tunnel, reverse proxy, or non-default hostname."
            " Example: --trusted-host my-tunnel.example.com"
        ),
    )
    parser.add_argument(
        "--runs-retention-days",
        type=int,
        default=30,
        metavar="DAYS",
        help=(
            "Delete persisted run files older than this many days at"
            " startup. Set to 0 to disable pruning. Persisted runs"
            " live under <attune-home>/ops/runs/. Default: 30."
        ),
    )
    # Specs page "Ready to close?" candidates surface — opt-in default-off.
    # Mutually exclusive on/off flags so the user can re-disable from the
    # CLI; both default to None so we can distinguish "no flag" (use
    # persisted state) from "explicit value" (overwrite persisted).
    # See docs/specs/ops-specs-completion-candidates/.
    candidates_group = parser.add_mutually_exclusive_group()
    candidates_group.add_argument(
        "--specs-candidates",
        dest="specs_candidates",
        action="store_const",
        const=True,
        default=None,
        help=(
            "Surface completion candidates on the Specs page. Requires"
            " 'gh auth login' for PR + open-issue verification. Setting"
            " persists across launches via <attune-home>/ops/config.json."
        ),
    )
    candidates_group.add_argument(
        "--no-specs-candidates",
        dest="specs_candidates",
        action="store_const",
        const=False,
        default=None,
        help="Hide the completion-candidates section and clear the persisted toggle.",
    )

    # Backwards-compat: --allow-run was the opt-IN flag before runs became
    # the default. Accept it silently as a no-op so existing scripts and
    # shell history keep working without prompting users to update.
    parser.add_argument(
        "--allow-run",
        action="store_true",
        help=argparse.SUPPRESS,
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

    from attune.ops.config import attune_home, build_config
    from attune.ops.ops_config_store import resolve_specs_candidates_enabled
    from attune.ops.server import create_app

    # Runs are enabled by default; --read-only opts out. The legacy
    # --allow-run flag is accepted as a no-op (already the default).
    allow_run = not args.read_only

    # Combine CLI flag with persisted setting. Resolver writes back when
    # the CLI flag is explicit; "no flag" returns whatever was persisted
    # (default False). This must happen BEFORE build_config so we have
    # the final value to pass in.
    specs_candidates_enabled = resolve_specs_candidates_enabled(
        args.specs_candidates, attune_home()
    )

    # Warn loudly when the user binds to all interfaces without an
    # explicit trusted-host. The middleware will still reject any
    # non-loopback Host header, but the user probably wanted to
    # reach the dashboard from elsewhere and would otherwise get a
    # confusing 400.
    if args.host == "0.0.0.0" and not args.trusted_host:  # nosec B104
        print(
            "WARNING: Binding to 0.0.0.0 without --trusted-host means any"
            " external hostname will be rejected by the security middleware."
            "\n         Add --trusted-host <external-hostname> for each"
            " hostname you intend to reach the dashboard at.",
            file=sys.stderr,
        )

    config = build_config(
        project_root=args.project_root,
        host=args.host,
        port=args.port,
        allow_run=allow_run,
        specs_roots=tuple(args.specs_root) if args.specs_root else None,
        trusted_hosts=tuple(args.trusted_host) if args.trusted_host else None,
        runs_retention_days=args.runs_retention_days,
        specs_candidates_enabled=specs_candidates_enabled,
    )
    app = create_app(config)

    url = f"http://{config.host}:{config.port}"
    print(f"attune ops → {url}")
    print(f"  project: {config.project_root}")
    print(f"  attune-home: {config.attune_home}")
    print(f"  allow-run: {'on' if config.allow_run else 'off (read-only)'}")
    print(f"  specs-candidates: {'on' if config.specs_candidates_enabled else 'off'}")

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
