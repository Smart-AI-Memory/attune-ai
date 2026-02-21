"""Utility CLI commands.

Commands for dashboard, setup, validation, and version info.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace

logger = logging.getLogger(__name__)


def cmd_dashboard_start(args: Namespace) -> int:
    """Start the agent coordination dashboard."""
    try:
        from attune.dashboard import run_standalone_dashboard

        # Get host and port from args
        host = args.host
        port = args.port

        print("\n🚀 Starting Agent Coordination Dashboard...")
        print(f"📊 Dashboard will be available at: http://{host}:{port}\n")
        print("💡 Make sure Redis is populated with test data:")
        print("   python scripts/populate_redis_direct.py\n")
        print("Press Ctrl+C to stop\n")

        # Start dashboard
        run_standalone_dashboard(host=host, port=port)
        return 0

    except KeyboardInterrupt:
        print("\n\n🛑 Dashboard stopped")
        return 0
    except ImportError as e:
        print(f"❌ Dashboard not available: {e}")
        print("   Install dashboard dependencies: pip install redis")
        return 1
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands should catch all errors and report gracefully
        logger.exception(f"Dashboard error: {e}")
        print(f"❌ Error starting dashboard: {e}")
        return 1


def cmd_setup(args: Namespace) -> int:
    """Install Attune slash commands for Claude Code."""
    import shutil

    # Determine source directory (package data)
    try:
        # For Python 3.9+
        try:
            from importlib.resources import files

            source_dir = files("attune") / "commands"
        except (ImportError, TypeError):
            # Fallback for older Python
            source_dir = None
    except ImportError:
        source_dir = None

    # If package resources don't work, try to find commands relative to this file
    if source_dir is None or not hasattr(source_dir, "iterdir"):
        # Look for commands directory relative to the package
        package_dir = Path(__file__).parent.parent
        potential_paths = [
            package_dir / "commands",
            package_dir.parent / ".claude" / "commands",
            Path.cwd() / ".claude" / "commands",
        ]

        source_dir = None
        for p in potential_paths:
            if p.exists() and p.is_dir():
                source_dir = p
                break

    if source_dir is None:
        print("❌ Could not find Attune command files.")
        print("\n   If you installed from git, run from the repository root:")
        print("   cd /path/to/attune-ai && attune setup")
        return 1

    # Target directory
    target_dir = Path.home() / ".claude" / "commands"

    print("\n🔧 Attune Setup\n")
    print("-" * 60)
    print(f"  Source:      {source_dir}")
    print(f"  Target:      {target_dir}")

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n  ✅ Created {target_dir}")

    # Copy command files (hub commands)
    copied = 0

    def _copy_md_files(src: Path, dst: Path) -> int:
        """Copy .md files from src to dst, return count."""
        count = 0
        if hasattr(src, "iterdir"):
            for item in src.iterdir():
                if hasattr(item, "is_file") and item.is_file() and str(item.name).endswith(".md"):
                    dst_file = dst / item.name
                    shutil.copy2(item, dst_file)
                    print(f"  ✅ Installed: {item.name}")
                    count += 1
                elif hasattr(item, "read_text") and str(item.name).endswith(".md"):
                    dst_file = dst / item.name
                    dst_file.write_text(item.read_text())
                    print(f"  ✅ Installed: {item.name}")
                    count += 1
        return count

    # Install hub commands
    print("\n  Hub Commands:")
    copied += _copy_md_files(source_dir, target_dir)

    # Install subagent definitions from agents/ subdirectory
    agents_copied = 0
    agents_src = None
    if hasattr(source_dir, "__truediv__"):
        # Path-like object
        candidate = source_dir / "agents"
        if isinstance(candidate, Path):
            # Real Path — trust .exists()
            if candidate.exists():
                agents_src = candidate
        elif hasattr(candidate, "iterdir"):
            # importlib resource — no .exists(), but iterable
            agents_src = candidate
    if agents_src is not None:
        agents_dst = target_dir / "agents"
        agents_dst.mkdir(parents=True, exist_ok=True)
        print("\n  Subagent Definitions:")
        agents_copied = _copy_md_files(agents_src, agents_dst)
        if agents_copied > 0:
            print(f"  ✅ Installed {agents_copied} subagent(s)")

    # Install config files (never overwrite existing)
    print("\n  Configuration Files:")
    project_claude_dir = Path.cwd() / ".claude"
    config_files = ["settings.json", "mcp.json"]
    configs_copied = 0
    for config_name in config_files:
        src_config = project_claude_dir / config_name
        dst_config = Path.home() / ".claude" / config_name
        if src_config.exists():
            if dst_config.exists():
                print(f"  ⏭️  Skipped: {config_name} (already exists)")
            else:
                shutil.copy2(src_config, dst_config)
                print(f"  ✅ Installed: {config_name}")
                configs_copied += 1

    print("-" * 60)

    if copied == 0:
        print("\n⚠️  No command files found to install.")
        print("   Make sure you're running from the attune-ai directory.")
        return 1

    total = copied + agents_copied + configs_copied
    print(
        f"\n✅ Installed {total} file(s) ({copied} commands, {agents_copied} subagents, {configs_copied} configs)"
    )
    print("\n📝 You can now use in Claude Code:")
    print("   /dev              - Developer tools (debug, commit, PR)")
    print("   /testing          - Run tests, coverage, test generation")
    print("   /workflows        - Security audit, bug prediction, perf")
    print("   /plan             - Planning, TDD, architecture review")
    print("   /docs             - Documentation generation")
    print("   /release          - Release preparation and publishing")
    print("   /agent            - Custom agent management")

    return 0


def _has_env_key(name: str) -> bool:
    """Check if an environment variable is set and non-empty.

    Returns only a boolean to avoid exposing sensitive values to callers.
    """
    import os

    val = os.environ.get(name, "")
    return len(val) > 0


def cmd_validate(args: Namespace) -> int:
    """Validate configuration."""
    print("\n🔍 Validating configuration...\n")

    errors = []
    warnings = []

    # Check config file
    config_paths = [
        Path("attune.config.json"),
        Path("attune.config.yml"),
        Path("attune.config.yaml"),
    ]

    config_found = False
    for config_path in config_paths:
        if config_path.exists():
            config_found = True
            print(f"  ✅ Config file: {config_path}")
            break

    if not config_found:
        warnings.append("No attune.config file found (using defaults)")

    # Check for API keys (helper returns bool to avoid logging sensitive values)
    api_keys = {
        "ANTHROPIC_API_KEY": "Anthropic (Claude)",
    }

    keys_found = 0
    for key, name in api_keys.items():
        if _has_env_key(key):
            print(f"  ✅ {name} API key set")
            keys_found += 1

    if keys_found == 0:
        errors.append(
            "No API keys found. Set ANTHROPIC_API_KEY\n"
            "   Run: python -m attune.models.auth_cli setup"
        )

    # Check workflows
    try:
        from attune.workflows import discover_workflows

        workflows = discover_workflows()
        print(f"  ✅ {len(workflows)} workflows available")
    except ImportError as e:
        warnings.append(f"Could not load workflows: {e}")

    # Summary
    print("\n" + "-" * 60)

    if errors:
        print("\n❌ Validation failed:")
        for error in errors:
            print(f"   - {error}")
        return 1

    if warnings:
        print("\n⚠️  Warnings:")
        for warning in warnings:
            print(f"   - {warning}")

    print("\n✅ Configuration is valid")
    return 0


def cmd_version(args: Namespace) -> int:
    """Show version information."""
    from attune.cli_minimal import get_version

    version = get_version()
    print(f"attune-ai {version}")

    if args.verbose:
        print(f"\nPython: {sys.version}")
        print(f"Platform: {sys.platform}")

        # Show installed extras
        try:
            from importlib.metadata import requires

            reqs = requires("attune-ai") or []
            print(f"\nDependencies: {len(reqs)}")
        except Exception:  # noqa: BLE001
            pass

    return 0


def cmd_features(args: Namespace) -> int:
    """Show available memory and telemetry features."""
    from attune.memory.features import MemoryFeatures
    from attune.telemetry.features import TelemetryFeatures

    print("\n" + "=" * 70)
    print("ATTUNE AI - FEATURE AVAILABILITY")
    print("=" * 70)

    # Memory features
    print("\n📦 MEMORY FEATURES\n")
    print(f"{'Feature':<30} {'Status':<15} {'Details'}")
    print("-" * 70)

    memory_features = MemoryFeatures.list_all_features()
    for _name, info in sorted(memory_features.items()):
        is_available = info.status.value == "available"
        status_symbol = "✅" if is_available else "⚠️"
        status_text = info.status.value.replace("_", " ").title()
        print(f"{status_symbol} {info.name:<28} {status_text:<15} {info.message}")

        if info.install_command and not is_available:
            print(f"   {'':>28} Install: {info.install_command}")

    # Telemetry features
    print("\n\n📊 TELEMETRY FEATURES\n")
    print(f"{'Feature':<30} {'Status':<15} {'Details'}")
    print("-" * 70)

    telemetry_features = TelemetryFeatures.list_all_features()
    for _name, info in sorted(telemetry_features.items()):
        is_available = info.status.value == "available"
        status_symbol = "✅" if is_available else "⚠️"
        status_text = info.status.value.replace("_", " ").title()
        print(f"{status_symbol} {info.name:<28} {status_text:<15} {info.message}")

        if info.install_command and not is_available:
            print(f"   {'':>28} Install: {info.install_command}")

    # Installation instructions summary
    print("\n" + "=" * 70)
    redis_available = MemoryFeatures.is_redis_available()

    if not redis_available:
        print("\n💡 To enable Redis-enhanced features:")
        print("   1. Install Redis package:")
        print("      pip install 'attune-ai[memory]'")
        print("\n   2. Install and start Redis server:")
        print("      • macOS: brew install redis && brew services start redis")
        print("      • Linux: sudo apt install redis-server")
        print("      • Docker: docker run -d -p 6379:6379 redis:alpine")
        print("\n   See: https://redis.io/docs/install/")
    else:
        redis_running = MemoryFeatures.is_redis_running()
        if redis_running:
            print("\n✅ Redis is installed and running - all features available!")
        else:
            print("\n⚠️  Redis package installed but server not running")
            print("   Start Redis server to enable enhanced features")

    print("\n" + "=" * 70 + "\n")
    return 0
