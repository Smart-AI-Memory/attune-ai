"""Security Audit Crew Package

A multi-agent crew that performs comprehensive security audits.
Demonstrates CrewAI's hierarchical collaboration patterns with:
- 5 specialized agents with distinct roles
- Hierarchical task delegation from Security Lead
- Memory Graph integration for cross-analysis learning
- Structured output with severity scoring

Usage:
    from attune.agent_factory.crews import SecurityAuditCrew

    crew = SecurityAuditCrew(api_key="...")
    report = await crew.audit("path/to/codebase")

    print(f"Found {len(report.findings)} security issues")
    for finding in report.critical_findings:
        print(f"  - {finding.title}: {finding.remediation}")

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .config import SecurityAuditConfig
from .crew import SecurityAuditCrew
from .models import (
    FindingCategory,
    SecurityFinding,
    SecurityReport,
    Severity,
)
from .prompts import XML_PROMPT_TEMPLATES

__all__ = [
    "XML_PROMPT_TEMPLATES",
    "FindingCategory",
    "SecurityAuditConfig",
    "SecurityAuditCrew",
    "SecurityFinding",
    "SecurityReport",
    "Severity",
]
