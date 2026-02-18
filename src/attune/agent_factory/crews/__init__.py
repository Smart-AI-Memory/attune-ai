"""Attune AI - Pre-built Crews

Ready-to-use multi-agent crews for common tasks.
Each crew leverages CrewAI's hierarchical collaboration patterns
with XML-enhanced prompts for structured output.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from attune.agent_factory.crews.base import CrewBase
from attune.agent_factory.crews.code_review import (
    CodeReviewConfig,
    CodeReviewCrew,
    CodeReviewReport,
    ReviewFinding,
    Verdict,
)
from attune.agent_factory.crews.health_check import (
    HealthCheckConfig,
    HealthCheckCrew,
    HealthCheckReport,
    HealthFix,
    HealthIssue,
)
from attune.agent_factory.crews.refactoring import (
    CodeCheckpoint,
    RefactoringCategory,
    RefactoringConfig,
    RefactoringCrew,
    RefactoringFinding,
    RefactoringReport,
    UserProfile,
)
from attune.agent_factory.crews.security_audit import (
    SecurityAuditConfig,
    SecurityAuditCrew,
    SecurityFinding,
    SecurityReport,
)

__all__ = [
    "CodeCheckpoint",
    "CodeReviewConfig",
    # Base
    "CrewBase",
    # Code Review Crew
    "CodeReviewCrew",
    "CodeReviewReport",
    "HealthCheckConfig",
    # Health Check Crew
    "HealthCheckCrew",
    "HealthCheckReport",
    "HealthFix",
    "HealthIssue",
    "RefactoringCategory",
    "RefactoringConfig",
    # Refactoring Crew
    "RefactoringCrew",
    "RefactoringFinding",
    "RefactoringReport",
    "ReviewFinding",
    "SecurityAuditConfig",
    # Security Audit Crew
    "SecurityAuditCrew",
    "SecurityFinding",
    "SecurityReport",
    "UserProfile",
    "Verdict",
]
