"""Health Check Analyzers

Standalone functions for building check tasks, parsing fixes,
applying fixes, and calculating health scores.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
import subprocess

from .models import (
    FixStatus,
    HealthCategory,
    HealthFix,
    HealthIssue,
    IssueSeverity,
)

logger = logging.getLogger(__name__)


def build_check_task(
    path: str,
    checks_run: dict,
    issues: list[HealthIssue],
    auto_fix: bool,
    context: dict,
) -> str:
    """Build the check task description for the crew.

    Args:
        path: Target path being checked.
        checks_run: Dictionary of check results.
        issues: List of health issues found.
        auto_fix: Whether auto-fix is enabled.
        context: Additional context for the task.

    Returns:
        Task description string for the crew.
    """
    issues_summary = "\n".join(
        f"  - [{i.severity.value.upper()}] {i.category.value}: {i.title}" for i in issues[:30]
    )

    task = f"""Analyze health check results and generate fixes.

Target: {path}
Auto-fix enabled: {auto_fix}

Checks Run:
- Lint (ruff): {"PASS" if checks_run.get("lint", {}).get("passed") else "FAIL"}
- Types (mypy): {"PASS" if checks_run.get("types", {}).get("passed") else "FAIL"}
- Tests (pytest): {"PASS" if checks_run.get("tests", {}).get("passed") else "FAIL"}
- Dependencies: {"PASS" if checks_run.get("deps", {}).get("passed") else "FAIL"}

Issues Found ({len(issues)}):
{issues_summary}

Workflow:
1. Health Lead coordinates analysis
2. Lint Fixer analyzes and suggests fixes for lint issues
3. Type Resolver suggests type annotations
4. Test Doctor diagnoses test failures
5. Dep Auditor suggests dependency updates

For each issue, provide:
- Root cause analysis
- Fix recommendation (code if applicable)
- Safety assessment (safe to auto-fix or needs review)
- Priority (1=critical, 2=high, 3=medium, 4=low)

Generate a prioritized fix plan.
"""

    if context.get("past_checks"):
        task += f"""
Past Health Checks Found: {len(context["past_checks"])}
Consider patterns from past fixes.
"""

    return task


def parse_fixes(result: dict, issues: list[HealthIssue]) -> list[HealthFix]:
    """Parse fixes from workflow result.

    Args:
        result: Workflow execution result dictionary.
        issues: List of health issues to generate fixes for.

    Returns:
        List of health fixes (suggested or structured).
    """
    fixes: list[HealthFix] = []

    # Check for structured fixes in metadata
    metadata = result.get("metadata", {})
    if "fixes" in metadata:
        for f in metadata["fixes"]:
            fixes.append(
                HealthFix(
                    title=f.get("title", "Fix"),
                    description=f.get("description", ""),
                    category=HealthCategory(f.get("category", "general")),
                    status=FixStatus.SUGGESTED,
                    file_path=f.get("file_path"),
                    before_code=f.get("before_code"),
                    after_code=f.get("after_code"),
                    patch=f.get("patch"),
                ),
            )
        return fixes

    # Generate suggested fixes based on issues
    for issue in issues:
        if issue.category == HealthCategory.LINT and issue.rule_id:
            fixes.append(
                HealthFix(
                    title=f"Fix {issue.rule_id}",
                    description=f"Run: ruff check --fix --select {issue.rule_id}",
                    category=issue.category,
                    status=FixStatus.SUGGESTED,
                    file_path=issue.file_path,
                    related_issues=[issue.title],
                ),
            )

    return fixes


async def apply_fixes(
    fixes: list[HealthFix],
    path: str,
    fix_safe_only: bool = True,
) -> list[HealthFix]:
    """Apply safe auto-fixes.

    Args:
        fixes: List of fixes to apply.
        path: Target path for fixes.
        fix_safe_only: Whether to only apply safe fixes.

    Returns:
        Updated list of fixes with applied statuses.
    """
    updated_fixes: list[HealthFix] = []

    for fix in fixes:
        if fix.category == HealthCategory.LINT and fix_safe_only:
            # Run ruff --fix for lint issues
            try:
                result = subprocess.run(
                    ["python", "-m", "ruff", "check", path, "--fix"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                fix.status = FixStatus.APPLIED if result.returncode == 0 else FixStatus.FAILED
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                fix.status = FixStatus.FAILED
        else:
            fix.status = FixStatus.SUGGESTED

        updated_fixes.append(fix)

    return updated_fixes


def calculate_health_score(issues: list[HealthIssue]) -> float:
    """Calculate health score from issues.

    Uses category-capped deductions to prevent one category (e.g., lint)
    from dominating the score. This makes the score more meaningful -
    50 lint warnings shouldn't tank a project that passes tests and has
    no security issues.

    Category caps:
    - lint: max -15 points
    - types: max -20 points
    - tests: max -25 points
    - security/dependencies: max -30 points
    - general: max -10 points

    Args:
        issues: List of health issues to score.

    Returns:
        Health score from 0.0 to 100.0.
    """
    if not issues:
        return 100.0

    # Per-issue deductions by severity
    severity_deductions = {
        IssueSeverity.CRITICAL: 15,
        IssueSeverity.HIGH: 8,
        IssueSeverity.MEDIUM: 2,
        IssueSeverity.LOW: 0.5,
        IssueSeverity.INFO: 0,
    }

    # Maximum deduction per category (prevents one area from tanking score)
    category_caps = {
        HealthCategory.LINT: 15,
        HealthCategory.TYPES: 20,
        HealthCategory.TESTS: 25,
        HealthCategory.DEPENDENCIES: 30,
        HealthCategory.SECURITY: 30,
        HealthCategory.GENERAL: 10,
    }

    # Calculate deductions per category
    category_deductions: dict[HealthCategory, float] = {}
    for issue in issues:
        cat = issue.category
        deduction = severity_deductions.get(issue.severity, 0)
        category_deductions[cat] = category_deductions.get(cat, 0) + deduction

    # Apply caps per category
    total_deduction = 0.0
    for cat, deduction in category_deductions.items():
        cap = category_caps.get(cat, 10)
        total_deduction += min(deduction, cap)

    return max(0.0, 100.0 - total_deduction)
