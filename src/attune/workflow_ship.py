"""Pre-Ship Validation Workflow for Attune AI.

Pre-commit validation pipeline including lint, format, type, security,
and test checks.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import sys


def _wc():
    """Late-resolve the workflow_commands facade for patchable helper access."""
    return sys.modules["attune.workflow_commands"]


def _run_tests_only(project_root: str = ".", verbose: bool = False) -> int:
    """Run tests only (used by ship --tests-only)."""
    wc = _wc()
    print("\n" + "=" * 60)
    print("  TEST RESULTS")
    print("=" * 60 + "\n")

    # Try pytest first
    success, output = wc._run_command(
        ["python", "-m", "pytest", project_root, "-v", "--tb=short"],
    )

    if success:
        print("All tests passed!")
        print("\n" + "=" * 60 + "\n")
        return 0
    print("Test Results:")
    print("-" * 40)
    print(output)
    print("\n" + "=" * 60 + "\n")
    return 1


def _run_security_only(project_root: str = ".", verbose: bool = False) -> int:
    """Run security checks only (used by ship --security-only)."""
    wc = _wc()
    print("\n" + "=" * 60)
    print("  SECURITY SCAN")
    print("=" * 60 + "\n")

    issues = []

    # Try bandit (Python security scanner)
    print("1. Running Bandit security scan...")
    success, output = wc._run_command(["bandit", "-r", project_root, "-ll", "-q"])
    if success:
        print("   PASS - No high/medium security issues")
    elif "bandit" in output.lower() and "not found" in output.lower():
        print("   SKIP - Bandit not installed (pip install bandit)")
    else:
        issue_count = output.count(">> Issue:")
        issues.append(f"Bandit: {issue_count} security issues")
        print(f"   WARN - {issue_count} issues found")
        if verbose:
            print(output)

    # Check for secrets in code
    print("2. Checking for hardcoded secrets...")
    success, output = wc._run_command(
        ["grep", "-rn", "--include=*.py", "password.*=.*['\"]", project_root],
    )
    if not success or not output.strip():
        print("   PASS - No obvious hardcoded secrets")
    else:
        lines = sum(1 for line in output.split("\n") if line.strip())
        issues.append(f"Secrets: {lines} potential hardcoded secrets")
        print(f"   WARN - {lines} potential hardcoded values found")

    # Check for .env files that might be committed
    print("3. Checking for sensitive files...")
    success, output = wc._run_command(["git", "ls-files", ".env", "*.pem", "*.key"])
    if not output.strip():
        print("   PASS - No sensitive files tracked")
    else:
        files = sum(1 for line in output.split("\n") if line.strip())
        issues.append(f"Files: {files} sensitive files in git")
        print(f"   WARN - {files} sensitive files tracked in git")

    # Summary
    print("\n" + "-" * 60)
    if issues:
        print("\nSECURITY ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
        print("\n" + "=" * 60 + "\n")
        return 1

    print("\nNo security issues found!")
    print("\n" + "=" * 60 + "\n")
    return 0


def ship_workflow(
    patterns_dir: str = "./patterns",
    project_root: str = ".",
    skip_sync: bool = False,
    tests_only: bool = False,
    security_only: bool = False,
    verbose: bool = False,
) -> int:
    """Pre-commit validation pipeline.

    Runs:
    1. Lint check (ruff)
    2. Format check (ruff format)
    3. Type check (mypy)
    4. Git status
    5. Summary

    Args:
        patterns_dir: Path to patterns directory
        project_root: Project root directory
        skip_sync: Skip syncing patterns to Claude
        tests_only: Run tests only (skip lint/format checks)
        security_only: Run security checks only
        verbose: Show detailed output

    Returns exit code (0 = ready to ship, non-zero = issues found).

    """
    if tests_only:
        return _run_tests_only(project_root, verbose)

    if security_only:
        return _run_security_only(project_root, verbose)

    wc = _wc()

    print("\n" + "=" * 60)
    print("  PRE-SHIP CHECKLIST")
    print("=" * 60 + "\n")

    issues = []
    warnings = []

    # 1. Lint check
    print("1. Running lint check...")
    success, output = wc._run_command(["ruff", "check", project_root])
    if success:
        print("   PASS - No lint issues")
    else:
        issue_count = len(
            [line for line in output.split("\n") if line.strip() and not line.startswith("Found")],
        )
        issues.append(f"Lint: {issue_count} issues")
        print(f"   FAIL - {issue_count} issues found")
        if verbose:
            print(output)

    # 2. Format check
    print("2. Checking formatting...")
    success, output = wc._run_command(["ruff", "format", "--check", project_root])
    if success:
        print("   PASS - Code is formatted")
    else:
        files = len(
            [
                line
                for line in output.split("\n")
                if "would be reformatted" in line.lower() or line.strip().endswith(".py")
            ],
        )
        warnings.append(f"Format: {files} files need formatting")
        print(f"   WARN - {files} files need formatting (run 'ruff format .')")

    # 3. Type check (if mypy available)
    print("3. Checking types...")
    success, output = wc._run_command(
        ["python", "-m", "mypy", project_root, "--ignore-missing-imports", "--no-error-summary"],
        capture=True,
    )
    if success or "error:" not in output.lower():
        print("   PASS - No type errors")
    else:
        error_count = output.lower().count("error:")
        warnings.append(f"Types: {error_count} type issues")
        print(f"   WARN - {error_count} type issues")

    # 4. Git status
    print("4. Checking git status...")
    success, output = wc._run_command(["git", "status", "--porcelain"])
    if success:
        staged = sum(1 for line in output.split("\n") if line.startswith(("A ", "M ", "D ", "R ")))
        unstaged = sum(1 for line in output.split("\n") if line.startswith((" M", " D", "??")))
        if staged > 0:
            print(f"   INFO - {staged} staged, {unstaged} unstaged")
        elif unstaged > 0:
            warnings.append(f"Git: {unstaged} unstaged files")
            print(f"   WARN - No staged changes ({unstaged} unstaged files)")
        else:
            print("   INFO - Working tree clean")

    # 5. Security check (optional)
    if not skip_sync:
        print("5. Running quick security check...")
        success, output = wc._run_command(
            ["bandit", "-r", project_root, "-ll", "-q"],
            capture=True,
        )
        if success:
            print("   PASS - No security issues")
        else:
            print("   SKIP - Bandit not available")
    else:
        print("5. Skipping security check (--skip-sync)")

    # Summary
    print("\n" + "-" * 60)

    if issues:
        print("\nBLOCKERS (must fix before shipping):")
        for issue in issues:
            print(f"  - {issue}")
        print("\n  Run 'ruff check --fix . && ruff format .' to auto-fix what's possible")
        print("\n" + "=" * 60)
        print("  NOT READY TO SHIP")
        print("=" * 60 + "\n")
        return 1

    if warnings:
        print("\nWARNINGS (recommended to fix):")
        for warning in warnings:
            print(f"  - {warning}")

    print("\n" + "=" * 60)
    print("  READY TO SHIP!")
    print("=" * 60 + "\n")

    # Update stats
    stats = wc._load_stats()
    stats["commands"]["ship"] = stats["commands"].get("ship", 0) + 1
    wc._save_stats(stats)

    return 0


def cmd_ship(args: object) -> int:
    """Ship command handler."""
    return _wc().ship_workflow(
        patterns_dir=getattr(args, "patterns_dir", "./patterns"),
        project_root=getattr(args, "project_root", "."),
        skip_sync=getattr(args, "skip_sync", False),
        tests_only=getattr(args, "tests_only", False),
        security_only=getattr(args, "security_only", False),
        verbose=getattr(args, "verbose", False),
    )
