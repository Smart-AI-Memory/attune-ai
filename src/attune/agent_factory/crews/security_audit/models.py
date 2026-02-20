"""Security Audit Models

Data types for security audit findings and reports.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """Security finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(Enum):
    """Security finding categories (OWASP-aligned)."""

    INJECTION = "injection"
    BROKEN_AUTH = "broken_authentication"
    SENSITIVE_DATA = "sensitive_data_exposure"
    XXE = "xml_external_entities"
    BROKEN_ACCESS = "broken_access_control"
    MISCONFIGURATION = "security_misconfiguration"
    XSS = "cross_site_scripting"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    VULNERABLE_COMPONENTS = "vulnerable_components"
    INSUFFICIENT_LOGGING = "insufficient_logging"
    OTHER = "other"


@dataclass
class SecurityFinding:
    """A single security finding from the audit."""

    title: str
    description: str
    severity: Severity
    category: FindingCategory
    file_path: str | None = None
    line_number: int | None = None
    code_snippet: str | None = None
    remediation: str | None = None
    cwe_id: str | None = None
    cvss_score: float | None = None
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
            "remediation": self.remediation,
            "cwe_id": self.cwe_id,
            "cvss_score": self.cvss_score,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class SecurityReport:
    """Complete security audit report."""

    target: str
    findings: list[SecurityFinding]
    summary: str = ""
    audit_duration_seconds: float = 0.0
    agents_used: list[str] = field(default_factory=list)
    memory_graph_hits: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def critical_findings(self) -> list[SecurityFinding]:
        """Get critical severity findings."""
        return [f for f in self.findings if f.severity == Severity.CRITICAL]

    @property
    def high_findings(self) -> list[SecurityFinding]:
        """Get high severity findings."""
        return [f for f in self.findings if f.severity == Severity.HIGH]

    @property
    def findings_by_category(self) -> dict[str, list[SecurityFinding]]:
        """Group findings by category."""
        result: dict[str, list[SecurityFinding]] = {}
        for finding in self.findings:
            cat = finding.category.value
            if cat not in result:
                result[cat] = []
            result[cat].append(finding)
        return result

    @property
    def risk_score(self) -> float:
        """Calculate overall risk score (0-100)."""
        if not self.findings:
            return 0.0

        weights = {
            Severity.CRITICAL: 25,
            Severity.HIGH: 15,
            Severity.MEDIUM: 5,
            Severity.LOW: 2,
            Severity.INFO: 0.5,
        }

        total = sum(weights[f.severity] * f.confidence for f in self.findings)
        return min(100.0, total)

    def to_dict(self) -> dict:
        """Convert report to dictionary."""
        return {
            "target": self.target,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "audit_duration_seconds": self.audit_duration_seconds,
            "agents_used": self.agents_used,
            "memory_graph_hits": self.memory_graph_hits,
            "risk_score": self.risk_score,
            "finding_counts": {
                "critical": len(self.critical_findings),
                "high": len(self.high_findings),
                "total": len(self.findings),
            },
            "metadata": self.metadata,
        }
