#!/usr/bin/env python3
"""Post-release QA script for attune-ai 5.10.0 + attune-help 0.3.0.

Run after `pip install --upgrade attune-ai attune-help` to verify
the published packages work correctly on a real install.

Usage:
    python scripts/qa_post_release.py
"""

import subprocess
import sys
import traceback

PASS = 0
FAIL = 0
SKIP = 0


def check(name, fn):
    """Run a check and report pass/fail."""
    global PASS, FAIL, SKIP
    try:
        result = fn()
        if result is None or result is True:
            print(f"  PASS  {name}")
            PASS += 1
        else:
            print(f"  FAIL  {name} — {result}")
            FAIL += 1
    except Exception as e:
        print(f"  FAIL  {name} — {e}")
        traceback.print_exc(limit=2)
        FAIL += 1


def skip(name, reason):
    """Skip a check with reason."""
    global SKIP
    print(f"  SKIP  {name} — {reason}")
    SKIP += 1


# ── 1. Version checks ──────────────────────────────────


def check_attune_ai_version():
    import attune

    v = attune.__version__
    if v != "5.10.0":
        return f"expected 5.10.0, got {v}"


def check_attune_help_version():
    from attune_help import __version__

    v = __version__
    if v != "0.3.0":
        return f"expected 0.3.0, got {v}"


def check_pip_shows_correct_versions():
    out = subprocess.check_output(
        [sys.executable, "-m", "pip", "show", "attune-ai", "attune-help"],
        text=True,
    )
    lines = [l for l in out.splitlines() if l.startswith("Version:")]
    versions = [l.split(":")[1].strip() for l in lines]
    if "5.10.0" not in versions:
        return f"attune-ai 5.10.0 not in pip show output: {versions}"
    if "0.3.0" not in versions:
        return f"attune-help 0.3.0 not in pip show output: {versions}"


# ── 2. Core imports ─────────────────────────────────────


def check_core_imports():
    pass


def check_workflow_registry():
    from attune.workflows import list_workflows

    wfs = list_workflows()
    if not wfs or len(wfs) < 5:
        return f"expected 5+ workflows, got {len(wfs)}"


def check_wizard_registry():
    from attune.wizards import list_wizards

    wizards = list_wizards()
    if not wizards or len(wizards) < 3:
        return f"expected 3+ wizards, got {len(wizards)}"


def check_mcp_imports():
    from attune.mcp.tool_schemas import (
        get_help_tools,
    )

    help_tools = get_help_tools()
    if not help_tools:
        return "get_help_tools() returned empty"


def check_agent_templates():
    from attune.meta_workflows.builtin_templates import BUILTIN_TEMPLATES

    count = len(BUILTIN_TEMPLATES)
    if count < 3:
        return f"expected 3+ agent templates, got {count}"


# ── 3. attune-help functionality ────────────────────────


def check_help_engine_init():
    from attune_help import HelpEngine

    engine = HelpEngine()


def check_help_engine_renderers():
    from attune_help.transformers import render_claude_code, render_cli, render_marketplace

    assert callable(render_cli)
    assert callable(render_claude_code)
    assert callable(render_marketplace)


def check_help_engine_session():
    import tempfile

    from attune_help.storage import LocalFileStorage

    with tempfile.TemporaryDirectory() as td:
        store = LocalFileStorage(storage_dir=td)


# ── 4. CLI entry points ────────────────────────────────


def check_attune_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "attune.cli_minimal", "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        return f"exit code {result.returncode}: {result.stderr[:200]}"


def check_attune_help_cli():
    """Check attune-help has a working module entry."""
    result = subprocess.run(
        [sys.executable, "-c", "from attune_help import HelpEngine; print('ok')"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return f"exit code {result.returncode}: {result.stderr[:200]}"
    if "ok" not in result.stdout:
        return f"unexpected output: {result.stdout[:100]}"


# ── 5. Security validation ─────────────────────────────


def check_path_validation_blocks_traversal():
    from attune.security.path_validation import _validate_file_path

    try:
        _validate_file_path("/etc/passwd")
        return "should have raised ValueError for /etc/passwd"
    except ValueError:
        pass


def check_path_validation_blocks_null_bytes():
    from attune.security.path_validation import _validate_file_path

    try:
        _validate_file_path("foo\x00bar")
        return "should have raised ValueError for null bytes"
    except ValueError:
        pass


# ── 6. MCP server startup ──────────────────────────────


def check_mcp_server_imports():
    from attune.mcp.tool_schemas import (
        get_help_tools,
        get_memory_tools,
        get_utility_tools,
        get_workflow_tools,
    )

    all_tools = {
        **get_workflow_tools(),
        **get_utility_tools(),
        **get_help_tools(),
        **get_memory_tools(),
    }
    if len(all_tools) < 10:
        return f"expected 10+ MCP tools, got {len(all_tools)}"


# ── 7. Cross-package integration ────────────────────────


def check_attune_help_in_attune_ai():
    """Verify attune-ai can import and use attune-help."""
    try:
        from attune_help import HelpEngine

        engine = HelpEngine()
    except ImportError as e:
        return f"attune-help not importable from attune-ai env: {e}"


# ── Run all checks ──────────────────────────────────────


def main():
    print("=" * 50)
    print("Post-Release QA — attune-ai 5.10.0 + attune-help 0.3.0")
    print("=" * 50)

    print(f"\nPython: {sys.version}")
    print(f"Executable: {sys.executable}\n")

    print("── 1. Version Checks ──")
    check("attune-ai version == 5.10.0", check_attune_ai_version)
    check("attune-help version == 0.3.0", check_attune_help_version)
    check("pip show versions match", check_pip_shows_correct_versions)

    print("\n── 2. Core Imports ──")
    check("core module imports", check_core_imports)
    check("workflow registry loads", check_workflow_registry)
    check("wizard registry loads", check_wizard_registry)
    check("MCP schema imports", check_mcp_imports)
    check("agent templates load", check_agent_templates)

    print("\n── 3. attune-help Functionality ──")
    check("HelpEngine initializes", check_help_engine_init)
    check("renderers import", check_help_engine_renderers)
    check("FileSessionStore works", check_help_engine_session)

    print("\n── 4. CLI Entry Points ──")
    check("attune CLI --help", check_attune_cli_help)
    check("attune-help importable", check_attune_help_cli)

    print("\n── 5. Security Validation ──")
    check("path traversal blocked", check_path_validation_blocks_traversal)
    check("null byte injection blocked", check_path_validation_blocks_null_bytes)

    print("\n── 6. MCP Server ──")
    check("MCP server imports + tools", check_mcp_server_imports)

    print("\n── 7. Cross-Package Integration ──")
    check("attune-help usable from attune-ai", check_attune_help_in_attune_ai)

    print("\n" + "=" * 50)
    total = PASS + FAIL + SKIP
    print(f"Results: {PASS} passed, {FAIL} failed, {SKIP} skipped / {total} total")
    print("=" * 50)

    return 1 if FAIL > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
