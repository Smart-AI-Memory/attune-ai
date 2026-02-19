"""Code Review Crew Package

A multi-agent crew that performs comprehensive code reviews.
Demonstrates CrewAI's hierarchical collaboration patterns with:
- 5 specialized agents with distinct roles
- Hierarchical task delegation from Review Lead
- Memory Graph integration for cross-review learning
- Structured output with verdict and recommendations

Usage:
    from attune.agent_factory.crews import CodeReviewCrew

    crew = CodeReviewCrew(api_key="...")
    report = await crew.review(diff="...", files_changed=["src/api.py"])

    print(f"Verdict: {report.verdict}")
    for finding in report.critical_findings:
        print(f"  - {finding.title}: {finding.suggestion}")

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .config import XML_PROMPT_TEMPLATES, CodeReviewConfig
from .crew import CodeReviewCrew
from .models import (
    CodeReviewReport,
    FindingCategory,
    ReviewFinding,
    Severity,
    Verdict,
)

__all__ = [
    "CodeReviewConfig",
    "CodeReviewCrew",
    "CodeReviewReport",
    "FindingCategory",
    "ReviewFinding",
    "Severity",
    "Verdict",
    "XML_PROMPT_TEMPLATES",
]
