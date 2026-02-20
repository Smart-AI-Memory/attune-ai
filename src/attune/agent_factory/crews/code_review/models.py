"""Code Review Models

Enums and dataclasses for code review findings, reports, and verdicts.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """Review finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(Enum):
    """Code review finding categories."""

    SECURITY = "security"
    ARCHITECTURE = "architecture"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    STYLE = "style"
    BUG = "bug"
    OTHER = "other"


class Verdict(Enum):
    """Code review verdict."""

    APPROVE = "approve"
    APPROVE_WITH_SUGGESTIONS = "approve_with_suggestions"
    REQUEST_CHANGES = "request_changes"
    REJECT = "reject"


@dataclass
class ReviewFinding:
    """A single finding from the code review."""

    title: str
    description: str
    severity: Severity
    category: FindingCategory
    file_path: str | None = None
    line_number: int | None = None
    code_snippet: str | None = None
    suggestion: str | None = None
    before_code: str | None = None
    after_code: str | None = None
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert finding to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "suggestion": self.suggestion,
            "before_code": self.before_code,
            "after_code": self.after_code,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class CodeReviewReport:
    """Complete code review report."""

    target: str
    findings: list[ReviewFinding]
    verdict: Verdict
    summary: str = ""
    review_duration_seconds: float = 0.0
    agents_used: list[str] = field(default_factory=list)
    memory_graph_hits: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def critical_findings(self) -> list[ReviewFinding]:
        """Get critical severity findings."""
        return [f for f in self.findings if f.severity == Severity.CRITICAL]

    @property
    def high_findings(self) -> list[ReviewFinding]:
        """Get high severity findings."""
        return [f for f in self.findings if f.severity == Severity.HIGH]

    @property
    def findings_by_category(self) -> dict[str, list[ReviewFinding]]:
        """Group findings by category."""
        result: dict[str, list[ReviewFinding]] = {}
        for finding in self.findings:
            cat = finding.category.value
            if cat not in result:
                result[cat] = []
            result[cat].append(finding)
        return result

    @property
    def quality_score(self) -> float:
        """Calculate overall quality score (0-100, higher is better)."""
        if not self.findings:
            return 100.0

        # Start with 100 and deduct based on severity
        deductions = {
            Severity.CRITICAL: 25,
            Severity.HIGH: 15,
            Severity.MEDIUM: 5,
            Severity.LOW: 2,
            Severity.INFO: 0.5,
        }

        total_deduction = sum(deductions[f.severity] * f.confidence for f in self.findings)
        return max(0.0, 100.0 - total_deduction)

    @property
    def has_blocking_issues(self) -> bool:
        """Check if there are issues that should block merge."""
        return len(self.critical_findings) > 0 or len(self.high_findings) > 3

    def to_dict(self) -> dict:
        """Convert report to dictionary."""
        return {
            "target": self.target,
            "findings": [f.to_dict() for f in self.findings],
            "verdict": self.verdict.value,
            "summary": self.summary,
            "review_duration_seconds": self.review_duration_seconds,
            "agents_used": self.agents_used,
            "memory_graph_hits": self.memory_graph_hits,
            "quality_score": self.quality_score,
            "has_blocking_issues": self.has_blocking_issues,
            "finding_counts": {
                "critical": len(self.critical_findings),
                "high": len(self.high_findings),
                "total": len(self.findings),
            },
            "metadata": self.metadata,
        }
