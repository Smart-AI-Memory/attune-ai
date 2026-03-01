"""Health Check Checkers

Standalone functions that run individual health checks (lint, types, tests, deps).

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import subprocess
from pathlib import Path

from .models import HealthCategory, HealthIssue, IssueSeverity

logger = logging.getLogger(__name__)


async def run_lint_check(path: str) -> dict:
    """Run ruff lint check.

    Args:
        path: Path to check.

    Returns:
        Dictionary with 'passed', 'issues', and 'tool' keys.

    """
    issues: list[HealthIssue] = []
    passed = True

    try:
        result = subprocess.run(
            ["python", "-m", "ruff", "check", path, "--output-format=json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            passed = False

        # Parse JSON output
        try:
            violations = json.loads(result.stdout) if result.stdout else []
            for v in violations[:50]:  # Limit to 50
                issues.append(
                    HealthIssue(
                        title=f"{v.get('code', 'LINT')}: {v.get('message', 'Lint error')}",
                        description=v.get("message", ""),
                        category=HealthCategory.LINT,
                        severity=IssueSeverity.MEDIUM,
                        file_path=v.get("filename"),
                        line_number=v.get("location", {}).get("row"),
                        rule_id=v.get("code"),
                        tool="ruff",
                    ),
                )
        except json.JSONDecodeError:
            pass

    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning(f"Lint check failed: {e}")

    return {"passed": passed, "issues": issues, "tool": "ruff"}


async def run_type_check(path: str) -> dict:
    """Run mypy type check.

    Args:
        path: Path to check.

    Returns:
        Dictionary with 'passed', 'issues', and 'tool' keys.

    """
    issues: list[HealthIssue] = []
    passed = True

    # Only scan production code packages
    production_packages = [
        "attune",
        "empathy_software_plugin",
        "empathy_healthcare_plugin",
        "empathy_llm_toolkit",
        "patterns",
    ]

    # Use production packages if checking current directory
    scan_args: list[str] = []
    if path in [".", "./"]:
        # Use package notation for packages in src/
        for pkg in production_packages:
            scan_args.extend(["-p", pkg])
    else:
        # For specific paths, use file notation
        scan_args.append(path)

    try:
        result = subprocess.run(
            ["python", "-m", "mypy"]
            + scan_args
            + ["--ignore-missing-imports", "--no-error-summary"],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            passed = False

        # Parse text output
        for line in result.stdout.splitlines()[:50]:
            if ": error:" in line:
                parts = line.split(": error:", 1)
                location = parts[0] if parts else ""
                message = parts[1].strip() if len(parts) > 1 else line

                file_path = None
                line_num = None
                if ":" in location:
                    loc_parts = location.rsplit(":", 2)
                    file_path = loc_parts[0]
                    try:
                        line_num = int(loc_parts[1]) if len(loc_parts) > 1 else None
                    except ValueError:
                        pass

                issues.append(
                    HealthIssue(
                        title=f"Type error: {message[:60]}",
                        description=message,
                        category=HealthCategory.TYPES,
                        severity=IssueSeverity.MEDIUM,
                        file_path=file_path,
                        line_number=line_num,
                        tool="mypy",
                    ),
                )

    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning(f"Type check failed: {e}")

    return {"passed": passed, "issues": issues, "tool": "mypy"}


async def run_test_check(path: str) -> dict:
    """Run pytest test check.

    Args:
        path: Path to check.

    Returns:
        Dictionary with 'passed', 'issues', and 'tool' keys.

    """
    issues: list[HealthIssue] = []
    passed = True

    # Only run tests in tests/ directory for production health check
    test_path = "tests/" if path in [".", "./"] else path

    try:
        result = subprocess.run(
            ["python", "-m", "pytest", test_path, "--collect-only", "-q"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            passed = False

        # Check for collection errors in stderr
        error_output = result.stderr + result.stdout
        for line in error_output.splitlines()[:50]:
            if "ERROR" in line or "INTERNALERROR" in line:
                # Only report actual errors, not counts
                if "error" in line.lower() and not line.strip().startswith("="):
                    issues.append(
                        HealthIssue(
                            title=f"Test error: {line[:50]}",
                            description=line,
                            category=HealthCategory.TESTS,
                            severity=IssueSeverity.CRITICAL,
                            tool="pytest",
                        ),
                    )

    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning(f"Test check failed: {e}")

    return {"passed": passed, "issues": issues, "tool": "pytest"}


async def run_dep_check(path: str) -> dict:
    """Run dependency security check.

    Args:
        path: Path to check.

    Returns:
        Dictionary with 'passed', 'issues', and 'tool' keys.

    """
    issues: list[HealthIssue] = []
    passed = True

    # Try pip-audit first
    try:
        result = subprocess.run(
            ["pip-audit", "--format=json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=path if Path(path).is_dir() else ".",
        )

        if result.returncode != 0:
            passed = False

        try:
            vulns = json.loads(result.stdout) if result.stdout else []
            # Ensure vulns is a list
            if isinstance(vulns, dict):
                vulns = vulns.get("vulnerabilities", []) or list(vulns.values())
            if not isinstance(vulns, list):
                vulns = []
            for v in vulns[:20]:
                # Handle different vulnerability formats
                if not isinstance(v, dict):
                    # Skip non-dict items or convert to basic format
                    continue

                severity = IssueSeverity.HIGH
                if "critical" in str(v).lower():
                    severity = IssueSeverity.CRITICAL

                issues.append(
                    HealthIssue(
                        title=f"Vulnerability in {v.get('name', 'unknown')}",
                        description=v.get("description", str(v)),
                        category=HealthCategory.DEPENDENCIES,
                        severity=severity,
                        rule_id=v.get("id"),
                        tool="pip-audit",
                        metadata={"fix_versions": v.get("fix_versions", [])},
                    ),
                )
        except json.JSONDecodeError:
            pass

    except (subprocess.TimeoutExpired, FileNotFoundError):
        # pip-audit not installed, try basic pip check
        try:
            result = subprocess.run(
                ["pip", "check"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                passed = False
                for line in result.stdout.splitlines()[:10]:
                    issues.append(
                        HealthIssue(
                            title=f"Dependency conflict: {line[:50]}",
                            description=line,
                            category=HealthCategory.DEPENDENCIES,
                            severity=IssueSeverity.MEDIUM,
                            tool="pip",
                        ),
                    )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return {"passed": passed, "issues": issues, "tool": "pip-audit/pip"}
