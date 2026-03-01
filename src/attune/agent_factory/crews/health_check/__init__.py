"""Health Check Crew Package

A multi-agent crew that diagnoses and fixes project health issues.
Uses XML-enhanced prompts for structured, consistent output.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .config import XML_PROMPT_TEMPLATES, HealthCheckConfig
from .crew import HealthCheckCrew
from .models import (
    FixStatus,
    HealthCategory,
    HealthCheckReport,
    HealthFix,
    HealthIssue,
    IssueSeverity,
)

__all__ = [
    "XML_PROMPT_TEMPLATES",
    "FixStatus",
    "HealthCategory",
    "HealthCheckConfig",
    "HealthCheckCrew",
    "HealthCheckReport",
    "HealthFix",
    "HealthIssue",
    "IssueSeverity",
]
