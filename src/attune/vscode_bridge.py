"""VS Code Extension Bridge

Provides functions to write data that the VS Code extension can pick up.
Enables Claude Code CLI output to appear in VS Code webview panels.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from attune.security.path_validation import _validate_file_path


@dataclass
class ReviewFinding:
    """A code review finding."""

    id: str
    file: str
    line: int
    severity: str  # 'critical' | 'high' | 'medium' | 'low' | 'info'
    category: str  # 'security' | 'performance' | 'maintainability' | 'style' | 'correctness'
    message: str
    column: int = 1
    details: str | None = None
    recommendation: str | None = None


@dataclass
class CodeReviewResult:
    """Code review results for VS Code bridge."""

    findings: list[dict[str, Any]]
    summary: dict[str, Any]
    verdict: str  # 'approve' | 'approve_with_suggestions' | 'request_changes' | 'reject'
    security_score: int
    formatted_report: str
    model_tier_used: str
    timestamp: str


def get_empathy_dir() -> Path:
    """Get the .attune directory, creating if needed.

    Note: Function retains 'empathy' name for backward compatibility.
    """
    attune_dir = Path(".attune")
    attune_dir.mkdir(exist_ok=True)
    return attune_dir


def write_code_review_results(
    findings: list[dict[str, Any]] | None = None,
    summary: dict[str, Any] | None = None,
    verdict: str = "approve_with_suggestions",
    security_score: int = 85,
    formatted_report: str = "",
    model_tier_used: str = "capable",
) -> Path:
    """Write code review results for VS Code extension to pick up.

    Args:
        findings: List of finding dicts with keys: id, file, line, severity, category, message
        summary: Summary dict with keys: total_findings, by_severity, by_category, files_affected
        verdict: One of 'approve', 'approve_with_suggestions', 'request_changes', 'reject'
        security_score: 0-100 score
        formatted_report: Markdown formatted report
        model_tier_used: 'cheap', 'capable', or 'premium'

    Returns:
        Path to the written file

    """
    findings = findings or []

    # Build summary if not provided
    if summary is None:
        by_severity: dict[str, int] = {}
        by_category: dict[str, int] = {}
        files_affected: set[str] = set()

        for f in findings:
            sev = f.get("severity", "info")
            cat = f.get("category", "correctness")
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_category[cat] = by_category.get(cat, 0) + 1
            if f.get("file"):
                files_affected.add(f["file"])

        summary = {
            "total_findings": len(findings),
            "by_severity": by_severity,
            "by_category": by_category,
            "files_affected": list(files_affected),
        }

    result = CodeReviewResult(
        findings=findings,
        summary=summary,
        verdict=verdict,
        security_score=security_score,
        formatted_report=formatted_report,
        model_tier_used=model_tier_used,
        timestamp=datetime.now().isoformat(),
    )

    output_path = get_empathy_dir() / "code-review-results.json"
    validated_path = _validate_file_path(str(output_path))

    with open(validated_path, "w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2)

    return output_path


def write_pr_review_results(
    pr_number: int | str,
    title: str,
    findings: list[dict[str, Any]],
    verdict: str = "approve_with_suggestions",
    summary_text: str = "",
) -> Path:
    """Write PR review results for VS Code extension.

    Convenience wrapper for PR reviews from GitHub.

    Args:
        pr_number: The PR number
        title: PR title
        findings: List of review findings
        verdict: Review verdict
        summary_text: Summary of the review

    Returns:
        Path to the written file

    """
    formatted_report = f"""## PR #{pr_number}: {title}

{summary_text}

### Findings ({len(findings)})

"""
    for f in findings:
        formatted_report += f"- **{f.get('severity', 'info').upper()}** [{f.get('file', 'unknown')}:{f.get('line', 0)}]: {f.get('message', '')}\n"

    return write_code_review_results(
        findings=findings,
        verdict=verdict,
        formatted_report=formatted_report,
        model_tier_used="capable",
    )


# Quick helper for Claude Code to call
def send_to_vscode(
    message: str,
    findings: list[dict[str, Any]] | None = None,
    verdict: str = "approve_with_suggestions",
) -> str:
    """Quick helper to send review results to VS Code.

    Usage in Claude Code:
        from attune.vscode_bridge import send_to_vscode
        send_to_vscode("Review complete", findings=[...])

    Returns:
        Confirmation message

    """
    path = write_code_review_results(
        findings=findings or [],
        formatted_report=message,
        verdict=verdict,
    )
    return f"Results written to {path} - VS Code will update automatically"
