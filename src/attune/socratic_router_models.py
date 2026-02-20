"""Socratic Router Models - Data models for intent classification.

Defines the core data structures used by the Socratic Router:
- IntentCategory: Enum of user intent types
- WorkflowOption: A selectable workflow option
- IntentClassification: Result of classifying user intent

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IntentCategory(Enum):
    """High-level categories of user intent."""

    FIX = "fix"  # Debug, fix bugs, resolve errors
    IMPROVE = "improve"  # Refactor, optimize, clean up
    VALIDATE = "validate"  # Test, review, audit
    SHIP = "ship"  # Commit, PR, release
    UNDERSTAND = "understand"  # Explain, document, explore
    CREATE = "create"  # Build new wizards, agents, teams, workflows
    UNKNOWN = "unknown"  # Needs clarification


@dataclass
class WorkflowOption:
    """A workflow option for AskUserQuestion.

    Attributes:
        label: Short label for the option (1-5 words)
        description: What this option does
        skill: The skill to invoke
        args: Arguments for the skill
    """

    label: str
    description: str
    skill: str
    args: str = ""

    def to_ask_user_option(self) -> dict[str, str]:
        """Convert to AskUserQuestion option format."""
        return {"label": self.label, "description": self.description}


@dataclass
class IntentClassification:
    """Result of classifying user intent.

    Attributes:
        category: Primary intent category
        confidence: Confidence score (0-1)
        keywords_matched: Keywords that triggered this classification
        suggested_question: Question to ask via AskUserQuestion
        options: Workflow options to present
    """

    category: IntentCategory
    confidence: float
    keywords_matched: list[str]
    suggested_question: str
    options: list[WorkflowOption]
