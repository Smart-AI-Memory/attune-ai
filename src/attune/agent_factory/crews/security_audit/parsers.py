"""Security Audit Parsers

Functions for parsing security findings from structured and
unstructured workflow output, and for generating report summaries.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from .models import FindingCategory, SecurityFinding, Severity


def parse_findings(result: dict) -> list[SecurityFinding]:
    """Parse findings from workflow result.

    Args:
        result: Workflow result dict with 'output' and/or
            'metadata' keys.

    Returns:
        List of parsed SecurityFinding objects.
    """
    metadata = result.get("metadata", {})

    # Check for structured findings in metadata
    if "findings" in metadata:
        return [dict_to_finding(f) for f in metadata["findings"]]

    # Parse from text output (fallback)
    output = result.get("output", "")
    return parse_text_findings(output)


def dict_to_finding(data: dict) -> SecurityFinding:
    """Convert dictionary to SecurityFinding.

    Args:
        data: Dictionary with finding fields.

    Returns:
        A SecurityFinding instance.
    """
    return SecurityFinding(
        title=data.get("title", "Untitled Finding"),
        description=data.get("description", ""),
        severity=Severity(data.get("severity", "medium")),
        category=FindingCategory(data.get("category", "other")),
        file_path=data.get("file_path"),
        line_number=data.get("line_number"),
        code_snippet=data.get("code_snippet"),
        remediation=data.get("remediation"),
        cwe_id=data.get("cwe_id"),
        cvss_score=data.get("cvss_score"),
        confidence=data.get("confidence", 1.0),
        metadata=data.get("metadata", {}),
    )


def parse_text_findings(text: str) -> list[SecurityFinding]:
    """Parse findings from unstructured text output.

    Uses heuristic keyword matching to extract findings from
    free-form text when structured metadata is unavailable.

    Args:
        text: Raw text output from the audit workflow.

    Returns:
        List of SecurityFinding objects extracted from text.
    """
    findings: list[SecurityFinding] = []

    severity_keywords = {
        Severity.CRITICAL: ["critical", "rce", "remote code execution"],
        Severity.HIGH: ["high", "injection", "authentication bypass"],
        Severity.MEDIUM: ["medium", "xss", "csrf"],
        Severity.LOW: ["low", "information disclosure"],
        Severity.INFO: ["info", "informational", "best practice"],
    }

    category_keywords = {
        FindingCategory.INJECTION: [
            "sql injection",
            "command injection",
            "ldap",
        ],
        FindingCategory.XSS: [
            "xss",
            "cross-site scripting",
            "script injection",
        ],
        FindingCategory.BROKEN_AUTH: [
            "authentication",
            "session",
            "password",
        ],
        FindingCategory.SENSITIVE_DATA: [
            "sensitive data",
            "encryption",
            "plaintext",
        ],
        FindingCategory.MISCONFIGURATION: [
            "misconfiguration",
            "default",
            "exposed",
        ],
    }

    lines = text.split("\n")
    current_finding: SecurityFinding | None = None

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
            for indicator in [
                "vulnerability",
                "issue",
                "finding",
                "detected",
            ]
        ):
            if current_finding:
                findings.append(current_finding)

            current_finding = SecurityFinding(
                title=line[:100].strip(),
                description=line,
                severity=detected_severity,
                category=detected_category,
            )

    if current_finding:
        findings.append(current_finding)

    return findings


def generate_summary(findings: list[SecurityFinding]) -> str:
    """Generate executive summary of findings.

    Args:
        findings: List of SecurityFinding objects to summarise.

    Returns:
        Human-readable summary string.
    """
    if not findings:
        return "No security issues were identified during the audit."

    critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
    high = sum(1 for f in findings if f.severity == Severity.HIGH)
    medium = sum(1 for f in findings if f.severity == Severity.MEDIUM)
    low = sum(1 for f in findings if f.severity == Severity.LOW)

    summary_parts = [f"Security audit identified {len(findings)} findings:"]

    if critical > 0:
        summary_parts.append(f"  - {critical} CRITICAL (immediate action required)")
    if high > 0:
        summary_parts.append(f"  - {high} HIGH (address within 7 days)")
    if medium > 0:
        summary_parts.append(f"  - {medium} MEDIUM (address within 30 days)")
    if low > 0:
        summary_parts.append(f"  - {low} LOW (address in next sprint)")

    # Add top categories
    by_category: dict[str, int] = {}
    for f in findings:
        cat = f.category.value
        by_category[cat] = by_category.get(cat, 0) + 1

    if by_category:
        top_cats = sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:3]
        summary_parts.append("\nTop vulnerability categories:")
        for cat, count in top_cats:
            summary_parts.append(f"  - {cat}: {count}")

    return "\n".join(summary_parts)
