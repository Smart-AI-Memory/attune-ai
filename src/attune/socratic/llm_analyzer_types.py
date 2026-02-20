"""Data types for LLM-powered goal analysis.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMAnalysisResult:
    """Result from LLM goal analysis."""

    intent: str
    domain: str
    confidence: float
    ambiguities: list[str]
    assumptions: list[str]
    constraints: list[str]
    keywords: list[str]
    suggested_agents: list[str]
    suggested_questions: list[dict[str, Any]]
    raw_response: str = ""
    secondary_domains: list[str] = field(default_factory=list)
    detected_requirements: list[str] = field(default_factory=list)

    @property
    def primary_domain(self) -> str:
        """Alias for domain (for MCP server compatibility)."""
        return self.domain


@dataclass
class LLMQuestionResult:
    """Result from LLM question generation."""

    questions: list[dict[str, Any]]
    confidence_after_answers: float
    ready_to_generate: bool
    reasoning: str


@dataclass
class LLMAgentRecommendation:
    """Result from LLM agent recommendation."""

    agents: list[dict[str, Any]]
    workflow_stages: list[dict[str, Any]]
    estimated_cost_tier: str
    estimated_duration: str
