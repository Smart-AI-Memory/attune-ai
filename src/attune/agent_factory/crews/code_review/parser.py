"""Code Review Parsing Utilities

Standalone functions for parsing code review findings from structured
and unstructured output, determining verdicts, and generating summaries.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging

from .models import (
    FindingCategory,
    ReviewFinding,
    Severity,
    Verdict,
)

logger = logging.getLogger(__name__)


def parse_findings(result: dict) -> list[ReviewFinding]:
    """Parse findings from workflow result.

    Args:
        result: Workflow result dictionary with 'output' and 'metadata' keys.

    Returns:
        List of parsed ReviewFinding objects.
    """
    findings = []

    output = result.get("output", "")
    metadata = result.get("metadata", {})

    # Check for structured findings in metadata
    if "findings" in metadata:
        for f in metadata["findings"]:
            findings.append(dict_to_finding(f))
        return findings

    # Parse from text output (fallback)
    findings = parse_text_findings(output)

    return findings


def dict_to_finding(data: dict) -> ReviewFinding:
    """Convert dictionary to ReviewFinding.

    Args:
        data: Dictionary with finding fields.

    Returns:
        A ReviewFinding instance.
    """
    return ReviewFinding(
        title=data.get("title", "Untitled Finding"),
        description=data.get("description", ""),
        severity=Severity(data.get("severity", "medium")),
        category=FindingCategory(data.get("category", "other")),
        file_path=data.get("file_path"),
        line_number=data.get("line_number"),
        code_snippet=data.get("code_snippet"),
        suggestion=data.get("suggestion"),
        before_code=data.get("before_code"),
        after_code=data.get("after_code"),
        confidence=data.get("confidence", 1.0),
        metadata=data.get("metadata", {}),
    )


def parse_text_findings(text: str) -> list[ReviewFinding]:
    """Parse findings from unstructured text output.

    Args:
        text: Raw text output from the review workflow.

    Returns:
        List of ReviewFinding objects extracted from the text.
    """
    findings = []

    severity_keywords = {
        Severity.CRITICAL: ["critical", "security", "vulnerability"],
        Severity.HIGH: ["high", "important", "must fix"],
        Severity.MEDIUM: ["medium", "should", "consider"],
        Severity.LOW: ["low", "minor", "nitpick"],
        Severity.INFO: ["info", "suggestion", "optional"],
    }

    category_keywords = {
        FindingCategory.SECURITY: ["security", "injection", "xss", "auth"],
        FindingCategory.ARCHITECTURE: ["architecture", "design", "solid"],
        FindingCategory.QUALITY: ["quality", "smell", "duplicate"],
        FindingCategory.PERFORMANCE: ["performance", "slow", "optimize"],
        FindingCategory.TESTING: ["test", "coverage", "assertion"],
        FindingCategory.DOCUMENTATION: ["doc", "comment", "readme"],
    }

    lines = text.split("\n")
    current_finding = None

    for line in lines:
        line_lower = line.lower().strip()

        # Detect severity
        detected_severity = Severity.MEDIUM
        for sev, keywords in severity_keywords.items():
            if any(kw in line_lower for kw in keywords):
                detected_severity = sev
                break

        # Detect category
        detected_category = FindingCategory.OTHER
        for cat, keywords in category_keywords.items():
            if any(kw in line_lower for kw in keywords):
                detected_category = cat
                break

        # Simple finding detection
        if any(
            indicator in line_lower
            for indicator in ["issue", "finding", "problem", "fix", "should"]
        ):
            if current_finding:
                findings.append(current_finding)

            current_finding = ReviewFinding(
                title=line[:100].strip(),
                description=line,
                severity=detected_severity,
                category=detected_category,
            )

    if current_finding:
        findings.append(current_finding)

    return findings


def determine_verdict(findings: list[ReviewFinding]) -> Verdict:
    """Determine review verdict based on findings.

    Args:
        findings: List of review findings to evaluate.

    Returns:
        The appropriate Verdict based on finding severities.
    """
    if not findings:
        return Verdict.APPROVE

    critical_count = len([f for f in findings if f.severity == Severity.CRITICAL])
    high_count = len([f for f in findings if f.severity == Severity.HIGH])
    medium_count = len([f for f in findings if f.severity == Severity.MEDIUM])

    # Reject if too many critical issues
    if critical_count >= 3:
        return Verdict.REJECT

    # Request changes for critical or many high issues
    if critical_count > 0 or high_count > 3:
        return Verdict.REQUEST_CHANGES

    # Approve with suggestions for medium/low issues
    if high_count > 0 or medium_count > 0:
        return Verdict.APPROVE_WITH_SUGGESTIONS

    return Verdict.APPROVE


def generate_summary(findings: list[ReviewFinding], verdict: Verdict) -> str:
    """Generate executive summary of review.

    Args:
        findings: List of review findings.
        verdict: The review verdict.

    Returns:
        A formatted summary string.
    """
    if not findings:
        return "Code review passed with no issues identified."

    critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
    high = sum(1 for f in findings if f.severity == Severity.HIGH)
    medium = sum(1 for f in findings if f.severity == Severity.MEDIUM)
    low = sum(1 for f in findings if f.severity == Severity.LOW)

    verdict_text = {
        Verdict.APPROVE: "Approved - ready to merge",
        Verdict.APPROVE_WITH_SUGGESTIONS: "Approved with suggestions",
        Verdict.REQUEST_CHANGES: "Changes requested before merge",
        Verdict.REJECT: "Rejected - requires significant rework",
    }

    summary_parts = [
        f"Code review verdict: {verdict_text.get(verdict, verdict.value)}",
        f"Total findings: {len(findings)}",
    ]

    if critical > 0:
        summary_parts.append(f"  - {critical} CRITICAL (blocking)")
    if high > 0:
        summary_parts.append(f"  - {high} HIGH (should address)")
    if medium > 0:
        summary_parts.append(f"  - {medium} MEDIUM (recommended)")
    if low > 0:
        summary_parts.append(f"  - {low} LOW (nice to have)")

    # Add top categories
    by_category: dict[str, int] = {}
    for f in findings:
        cat = f.category.value
        by_category[cat] = by_category.get(cat, 0) + 1

    if by_category:
        top_cats = sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:3]
        summary_parts.append("\nTop issue categories:")
        for cat, count in top_cats:
            summary_parts.append(f"  - {cat}: {count}")

    return "\n".join(summary_parts)
