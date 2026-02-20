"""PR Review data models.

Dataclass definitions for PR review workflow results.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field


@dataclass
class PRReviewResult:
    """Result from PRReviewWorkflow execution."""

    success: bool
    verdict: str  # "approve", "approve_with_suggestions", "request_changes", "reject"
    code_quality_score: float
    security_risk_score: float
    combined_score: float
    code_review: dict | None
    security_audit: dict | None
    all_findings: list[dict]
    code_findings: list[dict]
    security_findings: list[dict]
    critical_count: int
    high_count: int
    blockers: list[str]
    warnings: list[str]
    recommendations: list[str]
    summary: str
    agents_used: list[str]
    duration_seconds: float
    cost: float = 0.0  # Total cost from code review and security audit crews
    metadata: dict = field(default_factory=dict)
