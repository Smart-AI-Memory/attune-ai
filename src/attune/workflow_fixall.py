"""Auto-Fix Workflow for Attune AI.

Automatically fix all fixable lint, formatting, and import issues.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import sys


def _wc():
    """Late-resolve the workflow_commands facade for patchable helper access."""
    return sys.modules["attune.workflow_commands"]


def fix_all_workflow(
    project_root: str = ".",
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Auto-fix all fixable issues.

    Runs:
    1. ruff --fix (lint fixes)
    2. ruff format (formatting)
    3. isort (import sorting)
    4. Report what changed

    Returns exit code (0 = success).
    """
    wc = _wc()
    print("\n" + "=" * 60)
    print("  AUTO-FIX ALL")
    if dry_run:
        print("  (DRY RUN - no changes will be made)")
    print("=" * 60 + "\n")

    fixed_count = 0

    # 1. Ruff lint fixes
    print("1. Fixing lint issues...")
    if dry_run:
        success, output = wc._run_command(
            ["ruff", "check", project_root, "--fix", "--diff"],
        )
    else:
        success, output = wc._run_command(["ruff", "check", project_root, "--fix"])

    if success:
        fixed = output.count("Fixed")
        fixed_count += fixed
        print(f"   Fixed {fixed} issues")
    else:
        # Some issues couldn't be auto-fixed
        unfixable = sum(1 for line in output.split("\n") if "error" in line.lower())
        print(f"   {unfixable} issues require manual fix")
        if verbose:
            print(output)

    # 2. Ruff formatting
    print("2. Formatting code...")
    if dry_run:
        success, output = wc._run_command(["ruff", "format", project_root, "--diff"])
        formatted = output.count("@@ ")
    else:
        success, output = wc._run_command(["ruff", "format", project_root])
        formatted = len(
            [
                line
                for line in output.split("\n")
                if line.strip().endswith(".py") and "reformatted" in output.lower()
            ],
        )

    print(f"   Formatted {formatted} files")

    # 3. isort (if available)
    print("3. Sorting imports...")
    if dry_run:
        success, output = wc._run_command(
            ["isort", project_root, "--check-only", "--diff"],
        )
    else:
        success, output = wc._run_command(["isort", project_root])

    if "Skipped" in output or "isort" in output:
        sorted_count = output.count("Fixing") if not dry_run else output.count("---")
        print(f"   Sorted imports in {sorted_count} files")
    else:
        print("   No import changes needed")

    # Summary
    print("\n" + "-" * 60)

    if dry_run:
        print("\nDRY RUN complete - no files were modified")
        print("Run without --dry-run to apply changes")
    else:
        print(f"\nTotal fixes applied: {fixed_count}+")
        print("Run 'empathy ship' to verify everything is ready")

    print("\n" + "=" * 60 + "\n")

    # Update stats
    stats = wc._load_stats()
    stats["commands"]["fix-all"] = stats["commands"].get("fix-all", 0) + 1
    wc._save_stats(stats)

    return 0


def cmd_fix_all(args: object) -> int:
    """Fix-all command handler."""
    return _wc().fix_all_workflow(
        project_root=getattr(args, "project_root", "."),
        dry_run=getattr(args, "dry_run", False),
        verbose=getattr(args, "verbose", False),
    )
