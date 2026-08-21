"""Memory Control Panel display and CLI entry point.

Console display functions and CLI main() entry point for the Memory Control Panel.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

import structlog

from .storage_backend import default_storage_dir

if TYPE_CHECKING:
    from .control_panel import MemoryControlPanel


def print_status(panel: MemoryControlPanel):
    """Print status in a formatted way."""
    status = panel.status()

    print("\n" + "=" * 50)
    print("EMPATHY MEMORY STATUS")
    print("=" * 50)

    # Redis
    redis = status["redis"]
    redis_icon = "✓" if redis["status"] == "running" else "✗"
    print(f"\n{redis_icon} Redis: {redis['status'].upper()}")
    print(f"  Host: {redis['host']}:{redis['port']}")
    if redis["method"] != "unknown":
        print(f"  Method: {redis['method']}")

    # Long-term
    lt = status["long_term"]
    lt_icon = "✓" if lt["status"] == "available" else "○"
    print(f"\n{lt_icon} Long-term Storage: {lt['status'].upper()}")
    print(f"  Path: {lt['storage_dir']}")
    print(f"  Patterns: {lt['pattern_count']}")

    print()


def print_stats(panel: MemoryControlPanel):
    """Print statistics in a formatted way."""
    stats = panel.get_statistics()

    print("\n" + "=" * 50)
    print("EMPATHY MEMORY STATISTICS")
    print("=" * 50)

    print("\nShort-term Memory (Redis):")
    print(f"  Available: {stats.redis_available}")
    if stats.redis_available:
        print(f"  Total keys: {stats.redis_keys_total}")
        print(f"  Working keys: {stats.redis_keys_working}")
        print(f"  Staged patterns: {stats.redis_keys_staged}")
        print(f"  Memory used: {stats.redis_memory_used}")

    print("\nLong-term Memory (Patterns):")
    print(f"  Available: {stats.long_term_available}")
    print(f"  Total patterns: {stats.patterns_total}")
    print(f"  └─ PUBLIC: {stats.patterns_public}")
    print(f"  └─ INTERNAL: {stats.patterns_internal}")
    print(f"  └─ SENSITIVE: {stats.patterns_sensitive}")
    print(f"  Encrypted: {stats.patterns_encrypted}")

    # Performance stats
    print("\nPerformance:")
    if stats.redis_ping_ms > 0:
        print(f"  Redis latency: {stats.redis_ping_ms:.2f}ms")
    if stats.storage_bytes > 0:
        size_kb = stats.storage_bytes / 1024
        print(f"  Storage size: {size_kb:.1f} KB")
    print(f"  Stats collected in: {stats.collection_time_ms:.2f}ms")

    print()


def print_health(panel: MemoryControlPanel):
    """Print health check in a formatted way."""
    health = panel.health_check()

    print("\n" + "=" * 50)
    print("EMPATHY MEMORY HEALTH CHECK")
    print("=" * 50)

    status_icons = {"pass": "✓", "warn": "⚠", "fail": "✗", "info": "ℹ"}
    overall_icon = (
        "✓" if health["overall"] == "healthy" else "⚠" if health["overall"] == "degraded" else "✗"
    )

    print(f"\n{overall_icon} Overall: {health['overall'].upper()}")

    print("\nChecks:")
    for check in health["checks"]:
        icon = status_icons.get(check["status"], "?")
        print(f"  {icon} {check['name']}: {check['message']}")

    if health["recommendations"]:
        print("\nRecommendations:")
        for rec in health["recommendations"]:
            print(f"  • {rec}")

    print()


def _configure_logging(verbose: bool = False):
    """Configure logging for CLI mode."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )


def _build_parser(version: str) -> argparse.ArgumentParser:
    """Build the argument parser for the memory control panel CLI.

    Args:
        version: Package version string for --version flag

    Returns:
        Configured ArgumentParser

    """
    parser = argparse.ArgumentParser(
        description="Empathy Memory Control Panel - Manage Redis and pattern storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status              Show memory system status
  %(prog)s start               Start Redis if not running
  %(prog)s stop                Stop Redis (if we started it)
  %(prog)s stats               Show detailed statistics
  %(prog)s health              Run health check
  %(prog)s patterns            List stored patterns
  %(prog)s export patterns.json  Export patterns to file
  %(prog)s api --api-port 8765 Start REST API server only
  %(prog)s serve               Start Redis + API server (recommended)

Quick Start:
  1. pip install attune-ai
  2. attune-memory serve
  3. Open http://localhost:8765/api/status in browser
        """,
    )

    parser.add_argument(
        "command",
        choices=[
            "status",
            "start",
            "stop",
            "stats",
            "health",
            "patterns",
            "export",
            "api",
            "serve",
        ],
        help="Command to execute",
        nargs="?",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"attune-memory {version}",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Redis host (or API host for 'api' command)",
    )
    parser.add_argument("--port", type=int, default=6379, help="Redis port")
    parser.add_argument(
        "--api-port",
        type=int,
        default=8765,
        help="API server port (for 'api' command)",
    )
    parser.add_argument(
        "--storage",
        default=default_storage_dir(),
        help="Long-term storage directory",
    )
    parser.add_argument(
        "--classification",
        "-c",
        help="Filter by classification (PUBLIC/INTERNAL/SENSITIVE)",
    )
    parser.add_argument("--output", "-o", help="Output file for export")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show debug output")

    # Security options (for api/serve commands)
    parser.add_argument(
        "--api-key",
        help="API key for authentication (or set EMPATHY_MEMORY_API_KEY env var)",
    )
    parser.add_argument("--no-rate-limit", action="store_true", help="Disable rate limiting")
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=100,
        help="Max requests per minute per IP (default: 100)",
    )
    parser.add_argument("--ssl-cert", help="Path to SSL certificate file for HTTPS")
    parser.add_argument("--ssl-key", help="Path to SSL key file for HTTPS")
    parser.add_argument(
        "--cors-origins",
        help="Comma-separated list of allowed CORS origins (default: localhost)",
    )
    return parser


def _parse_cors_origins(args: argparse.Namespace) -> list[str] | None:
    """Parse CORS origins from CLI args.

    Args:
        args: Parsed CLI arguments

    Returns:
        List of origin strings or None

    """
    if args.cors_origins:
        return [o.strip() for o in args.cors_origins.split(",")]
    return None


def _dispatch_data_commands(
    command: str,
    args: argparse.Namespace,
    panel: MemoryControlPanel,
    _cp: Any,
) -> bool:
    """Handle status, start, stop, stats, health, patterns, and export commands.

    Args:
        command: The CLI command string
        args: Parsed CLI arguments
        panel: MemoryControlPanel instance
        _cp: The control_panel module (for display functions)

    Returns:
        True if command was handled, False otherwise

    """
    if command == "status":
        if args.json:
            print(json.dumps(panel.status(), indent=2))
        else:
            _cp.print_status(panel)
        return True

    if command == "start":
        status = panel.start_redis(verbose=not args.json)
        if args.json:
            print(json.dumps({"available": status.available, "method": status.method.value}))
        elif status.available:
            print(f"\n✓ Redis started via {status.method.value}")
        else:
            print(f"\n✗ Failed to start Redis: {status.message}")
            sys.exit(1)
        return True

    if command == "stop":
        if panel.stop_redis():
            print("✓ Redis stopped")
        else:
            print("⚠ Could not stop Redis (may not have been started by us)")
        return True

    if command == "stats":
        if args.json:
            print(json.dumps(asdict(panel.get_statistics()), indent=2))
        else:
            _cp.print_stats(panel)
        return True

    if command == "health":
        if args.json:
            print(json.dumps(panel.health_check(), indent=2))
        else:
            _cp.print_health(panel)
        return True

    if command == "patterns":
        patterns = panel.list_patterns(classification=args.classification)
        if args.json:
            print(json.dumps(patterns, indent=2))
        else:
            print(f"\nPatterns ({len(patterns)} found):")
            for p in patterns:
                print(
                    f"  [{p.get('classification', '?')}] {p.get('pattern_id', '?')} ({p.get('pattern_type', '?')})",
                )
        return True

    if command == "export":
        output = args.output or "patterns_export.json"
        count = panel.export_patterns(output, classification=args.classification)
        print(f"✓ Exported {count} patterns to {output}")
        return True

    return False


def _dispatch_server_commands(
    command: str,
    args: argparse.Namespace,
    panel: MemoryControlPanel,
    run_api_server: Any,
) -> bool:
    """Handle api and serve commands.

    Args:
        command: The CLI command string
        args: Parsed CLI arguments
        panel: MemoryControlPanel instance
        run_api_server: The API server runner function

    Returns:
        True if command was handled, False otherwise

    """
    if command == "api":
        cors_origins = _parse_cors_origins(args)
        run_api_server(
            panel,
            host=args.host,
            port=args.api_port,
            api_key=args.api_key,
            enable_rate_limit=not args.no_rate_limit,
            rate_limit_requests=args.rate_limit,
            ssl_certfile=args.ssl_cert,
            ssl_keyfile=args.ssl_key,
            allowed_origins=cors_origins,
        )
        return True

    if command == "serve":
        print("\n" + "=" * 50)
        print("EMPATHY MEMORY - STARTING SERVICES")
        print("=" * 50)

        print("\n[1/2] Starting Redis...")
        redis_status = panel.start_redis(verbose=False)
        if redis_status.available:
            print(f"  ✓ Redis running via {redis_status.method.value}")
        else:
            print(f"  ⚠ Redis not available: {redis_status.message}")
            print("      (Continuing with mock memory)")

        cors_origins = _parse_cors_origins(args)

        print("\n[2/2] Starting API server...")
        run_api_server(
            panel,
            host=args.host,
            port=args.api_port,
            api_key=args.api_key,
            enable_rate_limit=not args.no_rate_limit,
            rate_limit_requests=args.rate_limit,
            ssl_certfile=args.ssl_cert,
            ssl_keyfile=args.ssl_key,
            allowed_origins=cors_origins,
        )
        return True

    return False


def main():
    """CLI entry point."""
    from . import control_panel as _cp
    from .control_panel_api import run_api_server

    ControlPanelConfig = _cp.ControlPanelConfig
    MemoryControlPanel = _cp.MemoryControlPanel

    parser = _build_parser(_cp.__version__)
    args = parser.parse_args()

    _configure_logging(verbose=args.verbose)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    config = ControlPanelConfig(
        redis_host=args.host,
        redis_port=args.port,
        storage_dir=args.storage,
    )
    panel = MemoryControlPanel(config)

    if _dispatch_data_commands(args.command, args, panel, _cp):
        return

    _dispatch_server_commands(args.command, args, panel, run_api_server)


if __name__ == "__main__":
    main()
