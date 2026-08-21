"""Utility CLI commands.

Commands for setup, validation, and version info.

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


def _find_source_dir() -> Path | None:
    """Find the source directory for Attune command files."""
    try:
        from importlib.resources import files

        source_dir = files("attune") / "commands"
        if hasattr(source_dir, "iterdir"):
            return source_dir
    except (ImportError, TypeError):
        pass

    package_dir = Path(__file__).parent.parent
    potential_paths = [
        package_dir / "commands",
        package_dir.parent / ".claude" / "commands",
        Path.cwd() / ".claude" / "commands",
    ]
    for p in potential_paths:
        if p.exists() and p.is_dir():
            return p
    return None


def _copy_md_files(src: Path, dst: Path) -> int:
    """Copy .md files from src to dst, return count."""
    import shutil

    from attune.security.path_validation import _validate_file_path

    count = 0
    if not hasattr(src, "iterdir"):
        return 0
    for item in src.iterdir():
        if not str(item.name).endswith(".md"):
            continue
        dst_file = _validate_file_path(str(dst / item.name), allowed_dir=str(dst))
        if hasattr(item, "is_file") and item.is_file():
            shutil.copy2(item, dst_file)
        elif hasattr(item, "read_text"):
            dst_file.write_text(item.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            continue
        print(f"  ✅ Installed: {item.name}")
        count += 1
    return count


def _find_agents_src(source_dir) -> Path | None:
    """Find the agents subdirectory if it exists."""
    if not hasattr(source_dir, "__truediv__"):
        return None
    candidate = source_dir / "agents"
    if isinstance(candidate, Path) and candidate.exists():
        return candidate
    if hasattr(candidate, "iterdir"):
        return candidate
    return None


def _install_config_files() -> int:
    """Install config files, never overwriting existing ones. Return count."""
    import shutil

    project_claude_dir = Path.cwd() / ".claude"
    config_files = ["settings.json", "mcp.json"]
    configs_copied = 0
    for config_name in config_files:
        src_config = project_claude_dir / config_name
        if not src_config.exists():
            continue
        dst_config = Path.home() / ".claude" / config_name
        if dst_config.exists():
            print(f"  ⏭️  Skipped: {config_name} (already exists)")
        else:
            shutil.copy2(src_config, dst_config)
            print(f"  ✅ Installed: {config_name}")
            configs_copied += 1
    return configs_copied


def cmd_setup(args: Namespace) -> int:
    """Install Attune slash commands for Claude Code."""
    source_dir = _find_source_dir()
    if source_dir is None:
        print("❌ Could not find Attune command files.")
        print("\n   If you installed from git, run from the repository root:")
        print("   cd /path/to/attune-ai && attune setup")
        return 1

    target_dir = Path.home() / ".claude" / "commands"

    print("\n🔧 Attune Setup\n")
    print("-" * 60)
    print(f"  Source:      {source_dir}")
    print(f"  Target:      {target_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n  ✅ Created {target_dir}")

    # Install hub commands
    print("\n  Hub Commands:")
    copied = _copy_md_files(source_dir, target_dir)

    # Install subagent definitions
    agents_copied = 0
    agents_src = _find_agents_src(source_dir)
    if agents_src is not None:
        agents_dst = target_dir / "agents"
        agents_dst.mkdir(parents=True, exist_ok=True)
        print("\n  Subagent Definitions:")
        agents_copied = _copy_md_files(agents_src, agents_dst)
        if agents_copied > 0:
            print(f"  ✅ Installed {agents_copied} subagent(s)")

    # Install config files
    print("\n  Configuration Files:")
    configs_copied = _install_config_files()

    print("-" * 60)

    if copied == 0:
        print("\n⚠️  No command files found to install.")
        print("   Make sure you're running from the attune-ai directory.")
        return 1

    total = copied + agents_copied + configs_copied
    print(
        f"\n✅ Installed {total} file(s)"
        f" ({copied} commands, {agents_copied} subagents, {configs_copied} configs)",
    )
    print("\n📝 You can now use in Claude Code:")
    print("   /spec             - Spec-driven development")
    print("   /attune           - Guided discovery (asks what you need)")
    print("   /security         - Security audit")
    print("   /smart-test       - Find test gaps, generate tests")
    print("   /release          - Release preparation")
    print("   /help             - Full command reference")

    return 0


def _has_env_key(name: str) -> bool:
    """Check if an environment variable is set and non-empty.

    Returns only a boolean to avoid exposing sensitive values to callers.
    """
    import os

    val = os.environ.get(name, "")
    return bool(val)


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
        # Missing key is only an ERROR when there's no subscription-auth
        # evidence either — a Claude Code login (`~/.claude` present /
        # OAuth token set) is a fully working configuration
        # (setup-friction F2/F3: validate used to hard-fail machines
        # that subscription-first routing serves fine).
        import os as _os
        from pathlib import Path as _Path

        has_subscription_evidence = (
            bool(_os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip())
            or (_Path.home() / ".claude").exists()
        )
        if has_subscription_evidence:
            print("  ✅ Claude Code (subscription) auth evidence found")
            warnings.append(
                "No ANTHROPIC_API_KEY set — workflows will use "
                "subscription (Claude Code) auth; large-module API "
                "fallback is unavailable",
            )
        else:
            errors.append(
                "No auth found. Log in to Claude Code (run `claude` once) "
                "or set ANTHROPIC_API_KEY\n"
                "   Run: attune auth setup\n"
                "   Setup fight you? https://github.com/Smart-AI-Memory/"
                "attune-ai/discussions/1325",
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
            # INTENTIONAL: Dependency metadata is optional;
            # failure should not break the info command.
            pass

    return 0


def cmd_features(args: Namespace) -> int:
    """Show available memory and telemetry features."""
    from attune.memory.features import MemoryFeatures
    from attune.telemetry.features import TelemetryFeatures

    print("\n" + "=" * 70)
    print("ATTUNE AI - FEATURE AVAILABILITY")
    print("=" * 70)

    def _print_feature_table(title: str, features: dict) -> None:
        """Print a feature availability table."""
        print(f"\n{title}\n")
        print(f"{'Feature':<30} {'Status':<15} {'Details'}")
        print("-" * 70)
        for _name, info in sorted(features.items()):
            is_available = info.status.value == "available"
            symbol = "✅" if is_available else "⚠️"
            status_text = info.status.value.replace("_", " ").title()
            print(f"{symbol} {info.name:<28} {status_text:<15} {info.message}")
            if info.install_command and not is_available:
                print(f"   {'':>28} Install: {info.install_command}")

    _print_feature_table("📦 MEMORY FEATURES", MemoryFeatures.list_all_features())
    _print_feature_table("\n📊 TELEMETRY FEATURES", TelemetryFeatures.list_all_features())

    # Installation instructions summary
    print("\n" + "=" * 70)
    redis_available = MemoryFeatures.is_redis_available()

    if not redis_available:
        print("\n💡 To enable Redis-enhanced features:")
        print("   1. Repair the redis package (it ships as a core")
        print("      dependency, so this means a broken install):")
        print("      pip install --force-reinstall 'redis>=5.0.0,<9.0.0'")
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


def cmd_doctor(args: Namespace) -> int:
    """Run comprehensive environment health check.

    Combines validation, feature detection, and connectivity
    checks into a single diagnostic command.

    Args:
        args: Parsed CLI arguments (unused).

    Returns:
        0 if no failures, 1 if any critical check fails.

    """
    print("\n" + "=" * 60)
    print("  ATTUNE AI DOCTOR")
    print("=" * 60 + "\n")

    passed = 0
    optional = 0
    failed = 0

    def _ok(label: str, detail: str = "") -> None:
        nonlocal passed
        passed += 1
        suffix = f" ({detail})" if detail else ""
        print(f"  [OK]   {label}{suffix}")

    def _warn(label: str, detail: str = "") -> None:
        nonlocal optional
        optional += 1
        suffix = f" ({detail})" if detail else ""
        print(f"  [--]   {label}{suffix}")

    def _fail(label: str, detail: str = "") -> None:
        nonlocal failed
        failed += 1
        suffix = f" ({detail})" if detail else ""
        print(f"  [FAIL] {label}{suffix}")

    # 1. Python version
    version_str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    _ok(f"Python {version_str}")

    # 2. Package version
    try:
        from attune import __version__

        _ok(f"attune-ai {__version__}")
    except Exception:  # noqa: BLE001
        # INTENTIONAL: version check is non-critical
        _warn("attune-ai version unknown")

    # 3. API key
    if _has_env_key("ANTHROPIC_API_KEY"):
        _ok("ANTHROPIC_API_KEY set")
    else:
        _fail("ANTHROPIC_API_KEY not set")

    # 4. Optional extras
    _extras = {
        "redis": "redis",
        "jinja2": "jinja2",
        "sentence_transformers": "sentence-transformers",
    }
    for mod_name, pkg_name in _extras.items():
        try:
            __import__(mod_name)
            _ok(f"{pkg_name} installed")
        except ImportError:
            _warn(f"{pkg_name} not installed", "optional")

    # 5. Redis connectivity
    #
    # Probe THE CONFIGURED endpoint, via the canonical resolver. A bare
    # ``redis.Redis(...)`` defaults to localhost:6379 no matter what
    # REDIS_URL says, so `attune doctor` used to report reachability for
    # a server the user does not run — the H1 split-brain oracle, in the
    # one command whose entire job is telling the truth about the
    # environment.
    try:
        from attune.memory.config import resolve_redis_connection
        from attune.memory.recall_redis import connect_recall_redis

        resolved = resolve_redis_connection()
        client = connect_recall_redis(socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        _ok(f"Redis server reachable ({resolved.redacted_url})")
    except ImportError:
        _warn("Redis connectivity", "redis package not installed")
    except Exception:  # noqa: BLE001
        # INTENTIONAL: Redis is optional
        _warn("Redis server not reachable", "optional")

    # 6. Workflows
    try:
        from attune.workflows import discover_workflows

        wfs = discover_workflows()
        _ok(f"{len(wfs)} workflows registered")
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Workflow discovery is non-critical
        _fail(f"Workflow discovery failed: {e}")

    # 7. Wizards
    try:
        from attune.wizards import list_wizards

        wizards = list_wizards()
        _ok(f"{len(wizards)} wizards registered")
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Wizard discovery is non-critical
        _warn(f"Wizard discovery: {e}")

    # 8. MCP server
    try:
        from attune.mcp.server import EmpathyMCPServer

        server = EmpathyMCPServer()
        tool_count = len(server.tools)
        _ok(f"MCP server: {tool_count} tools")
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: MCP is optional
        _warn(f"MCP server: {e}")

    # Summary
    total = passed + optional + failed
    print("\n" + "-" * 60)
    print(f"  {passed}/{total} passed, {optional} optional, {failed} failures")
    print("=" * 60 + "\n")

    return 1 if failed > 0 else 0
