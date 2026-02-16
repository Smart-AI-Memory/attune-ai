"""Prompt Context

Provides dataclass for structured prompt context used by XML templates.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptContext:
    """Context for rendering XML prompts.

    Provides a structured way to pass information to prompt templates,
    ensuring consistency across different workflows.

    Attributes:
        role: The role the AI should assume (e.g., "security analyst").
        goal: The primary objective (e.g., "identify vulnerabilities").
        instructions: Step-by-step instructions for the task.
        constraints: Rules, limits, and guidelines to follow.
        input_type: Type of input content ("code", "diff", "document", "question").
        input_payload: The actual content to analyze or process.
        extra: Additional context-specific data.
        examples: One-shot input/output pairs for few-shot learning.
            Each dict has "input" and "output" keys.

    """

    role: str
    goal: str
    instructions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    input_type: str = "code"
    input_payload: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
    examples: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate context after initialization."""
        if not self.role:
            raise ValueError("role is required")
        if not self.goal:
            raise ValueError("goal is required")

    @classmethod
    def for_security_audit(
        cls,
        code: str,
        findings_summary: str = "",
        risk_level: str = "",
        examples: list[dict[str, str]] | None = None,
        **extra: Any,
    ) -> PromptContext:
        """Create a context for security audit workflows.

        Args:
            code: The code to audit.
            findings_summary: Summary of detected findings.
            risk_level: Current risk assessment level.
            examples: One-shot examples. Defaults to SECURITY_AUDIT_EXAMPLES.
            **extra: Additional context data.

        """
        if examples is None:
            from attune.prompts.examples import SECURITY_AUDIT_EXAMPLES

            examples = SECURITY_AUDIT_EXAMPLES

        return cls(
            role="application security engineer",
            goal="Identify security vulnerabilities and provide remediation guidance",
            instructions=[
                "Analyze the code for security vulnerabilities",
                "Focus on OWASP Top 10 categories",
                "Provide severity ratings (critical, high, medium, low)",
                "Include specific file and line references where applicable",
                "Suggest concrete remediation steps for each finding",
            ],
            constraints=[
                "Be specific and actionable",
                "Prioritize findings by severity",
                "Include code examples for fixes when helpful",
            ],
            input_type="code",
            input_payload=code,
            extra={
                "findings_summary": findings_summary,
                "risk_level": risk_level,
                **extra,
            },
            examples=examples,
        )

    @classmethod
    def for_code_review(
        cls,
        code_or_diff: str,
        input_type: str = "code",
        context: str = "",
        examples: list[dict[str, str]] | None = None,
        **extra: Any,
    ) -> PromptContext:
        """Create a context for code review workflows.

        Args:
            code_or_diff: The code or diff to review.
            input_type: Either "code" or "diff".
            context: Additional context about the change.
            examples: One-shot examples. Defaults to CODE_REVIEW_EXAMPLES.
            **extra: Additional context data.

        """
        if examples is None:
            from attune.prompts.examples import CODE_REVIEW_EXAMPLES

            examples = CODE_REVIEW_EXAMPLES

        return cls(
            role="senior staff engineer performing code review",
            goal="Review code quality, identify issues, and suggest improvements",
            instructions=[
                "Identify bugs, security risks, and performance issues",
                "Evaluate code structure and maintainability",
                "Check for missing error handling",
                "Identify tests that should be added or updated",
                "Suggest improvements while respecting existing patterns",
            ],
            constraints=[
                "Be direct and technical",
                "Reference specific files and lines",
                "Keep feedback actionable",
                "Maximum 500 words",
            ],
            input_type=input_type,
            input_payload=code_or_diff,
            extra={
                "context": context,
                **extra,
            },
            examples=examples,
        )

    @classmethod
    def for_perf_audit(
        cls,
        code: str,
        context: str = "",
        examples: list[dict[str, str]] | None = None,
        **extra: Any,
    ) -> PromptContext:
        """Create a context for performance audit workflows.

        Args:
            code: The code to audit for performance issues.
            context: Additional context about the codebase or performance goals.
            examples: One-shot examples. Defaults to PERF_AUDIT_EXAMPLES.
            **extra: Additional context data.

        """
        if examples is None:
            from attune.prompts.examples import PERF_AUDIT_EXAMPLES

            examples = PERF_AUDIT_EXAMPLES

        return cls(
            role="senior performance engineer",
            goal="Identify performance bottlenecks and optimization opportunities",
            instructions=[
                "Analyze code for performance bottlenecks",
                "Identify algorithmic complexity issues (O(n^2), etc.)",
                "Check for memory inefficiencies and resource leaks",
                "Look for blocking operations in async code",
                "Suggest concrete optimizations with expected impact",
            ],
            constraints=[
                "Be specific about time and space complexity",
                "Prioritize by expected impact",
                "Include before/after code examples",
                "Rate each finding: critical, high, medium, low",
            ],
            input_type="code",
            input_payload=code,
            extra={
                "context": context,
                **extra,
            },
            examples=examples,
        )

    @classmethod
    def for_research(
        cls,
        question: str,
        context: str = "",
        **extra: Any,
    ) -> PromptContext:
        """Create a context for research/synthesis workflows.

        Args:
            question: The research question to answer.
            context: Related context or codebase information.
            **extra: Additional context data.

        """
        return cls(
            role="staff engineer conducting technical research",
            goal="Research and synthesize information to answer the question",
            instructions=[
                "Explain key concepts and tradeoffs",
                "Relate the answer to the provided context if relevant",
                "Propose 1-2 concrete next steps or decisions",
            ],
            constraints=[
                "Be clear and pragmatic",
                "3-5 short paragraphs",
                "Focus on actionable insights",
            ],
            input_type="question",
            input_payload=question,
            extra={
                "context": context,
                **extra,
            },
        )

    def with_extra(self, **kwargs: Any) -> PromptContext:
        """Return a new context with additional extra fields."""
        new_extra = {**self.extra, **kwargs}
        return PromptContext(
            role=self.role,
            goal=self.goal,
            instructions=self.instructions.copy(),
            constraints=self.constraints.copy(),
            input_type=self.input_type,
            input_payload=self.input_payload,
            extra=new_extra,
            examples=self.examples.copy(),
        )
