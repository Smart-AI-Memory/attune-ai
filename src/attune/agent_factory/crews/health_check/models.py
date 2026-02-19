"""Health Check Models

Enums and dataclasses for health check reports, issues, and fixes.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field
from enum import Enum


class HealthCategory(Enum):
    """Health check categories."""

    LINT = "lint"
    TYPES = "types"
    TESTS = "tests"
    DEPENDENCIES = "dependencies"
    SECURITY = "security"
    GENERAL = "general"


class IssueSeverity(Enum):
    """Issue severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FixStatus(Enum):
    """Status of an attempted fix."""

    APPLIED = "applied"
    SUGGESTED = "suggested"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class HealthIssue:
    """A single health issue found."""

    title: str
    description: str
    category: HealthCategory
    severity: IssueSeverity
    file_path: str | None = None
    line_number: int | None = None
    code_snippet: str | None = None
    tool: str | None = None
    rule_id: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert issue to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "tool": self.tool,
            "rule_id": self.rule_id,
            "metadata": self.metadata,
        }


@dataclass
class HealthFix:
    """A fix applied or suggested."""

    title: str
    description: str
    category: HealthCategory
    status: FixStatus
    file_path: str | None = None
    before_code: str | None = None
    after_code: str | None = None
    patch: str | None = None
    related_issues: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert fix to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "status": self.status.value,
            "file_path": self.file_path,
            "before_code": self.before_code,
            "after_code": self.after_code,
            "patch": self.patch,
            "related_issues": self.related_issues,
            "metadata": self.metadata,
        }


@dataclass
class HealthCheckReport:
    """Complete health check report."""

    target: str
    issues: list[HealthIssue]
    fixes: list[HealthFix]
    health_score: float
    check_duration_seconds: float = 0.0
    agents_used: list[str] = field(default_factory=list)
    memory_graph_hits: int = 0
    checks_run: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    @property
    def critical_issues(self) -> list[HealthIssue]:
        """Get critical severity issues."""
        return [i for i in self.issues if i.severity == IssueSeverity.CRITICAL]

    @property
    def applied_fixes(self) -> list[HealthFix]:
        """Get successfully applied fixes."""
        return [f for f in self.fixes if f.status == FixStatus.APPLIED]

    @property
    def issues_by_category(self) -> dict[str, list[HealthIssue]]:
        """Group issues by category."""
        result: dict[str, list[HealthIssue]] = {}
        for issue in self.issues:
            cat = issue.category.value
            if cat not in result:
                result[cat] = []
            result[cat].append(issue)
        return result

    @property
    def is_healthy(self) -> bool:
        """Check if project is healthy (score >= 80)."""
        return self.health_score >= 80.0

    def to_dict(self) -> dict:
        """Convert report to dictionary."""
        return {
            "target": self.target,
            "issues": [i.to_dict() for i in self.issues],
            "fixes": [f.to_dict() for f in self.fixes],
            "health_score": self.health_score,
            "check_duration_seconds": self.check_duration_seconds,
            "agents_used": self.agents_used,
            "memory_graph_hits": self.memory_graph_hits,
            "checks_run": self.checks_run,
            "is_healthy": self.is_healthy,
            "issue_counts": {
                "critical": len(self.critical_issues),
                "total": len(self.issues),
                "by_category": {k: len(v) for k, v in self.issues_by_category.items()},
            },
            "fix_counts": {
                "applied": len(self.applied_fixes),
                "total": len(self.fixes),
            },
            "metadata": self.metadata,
        }
