"""Refactoring Crew Package

A 2-agent crew that performs interactive code refactoring analysis.
Designed for Level 4 Empathy with session memory, rollback capability,
and learning from user preferences over time.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .config import XML_PROMPT_TEMPLATES
from .crew import RefactoringCrew
from .types import (
    CodeCheckpoint,
    Impact,
    RefactoringCategory,
    RefactoringConfig,
    RefactoringFinding,
    RefactoringReport,
    Severity,
    UserProfile,
)

__all__ = [
    "XML_PROMPT_TEMPLATES",
    "CodeCheckpoint",
    "Impact",
    "RefactoringCategory",
    "RefactoringConfig",
    "RefactoringCrew",
    "RefactoringFinding",
    "RefactoringReport",
    "Severity",
    "UserProfile",
]
