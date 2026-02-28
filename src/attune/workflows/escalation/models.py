"""Data structures for the EscalationChain.

No logic lives here — pure data containers used across
chain.py, evaluator.py, and validators.py.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FeedbackType(Enum):
    """What kind of feedback triggered a retry or escalation.

    Attributes:
        STRUCTURAL: Rule-based validator caught a problem.
        SEMANTIC: Evaluator LLM judged the response poor quality.
        PARSE_FAILURE: Response could not be parsed as expected JSON.
        EXCEPTION: API or processing error during the attempt.

    """

    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    PARSE_FAILURE = "parse_failure"
    EXCEPTION = "exception"


@dataclass
class ValidationFeedback:
    """Structured feedback from a single validation step.

    Attributes:
        feedback_type: Category of the failure.
        validator_name: Class or function that produced this feedback.
        message: Human-readable description of the problem.
        severity: "error" (blocks success) or "warning" (informational).
        suggestion: Optional actionable hint injected into the retry prompt.

    """

    feedback_type: FeedbackType
    validator_name: str
    message: str
    severity: str = "error"
    suggestion: str | None = None


@dataclass
class AttemptResult:
    """Result of a single LLM call within the chain.

    Attributes:
        model: Model ID used for this attempt.
        attempt_number: Which attempt on this model tier (1 = first, 2 = retry, …).
        raw_response: Raw string content from the LLM.
        parsed_response: Parsed value (dict for JSON, str otherwise), or None on failure.
        success: True only when all validators and evaluator pass.
        feedback: List of feedback items from failed checks.
        is_retry: True when this is a same-model retry (not the first attempt).
        evaluator_model: Model ID used for semantic evaluation, if any.
        latency_ms: Wall-clock time for the LLM call in milliseconds.
        input_tokens: Input tokens consumed.
        output_tokens: Output tokens generated.

    """

    model: str
    attempt_number: int
    raw_response: str
    parsed_response: Any | None
    success: bool
    feedback: list[ValidationFeedback] = field(default_factory=list)
    is_retry: bool = False
    evaluator_model: str | None = None
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class EscalationResult:
    """Final result of running the EscalationChain.

    Attributes:
        success: True if any attempt passed all checks.
        response: The accepted parsed response, or best partial on failure.
        final_model: Model ID that produced the accepted (or best) response.
        attempts: Full ordered list of AttemptResult objects.
        total_retries: Number of same-model retries across all tiers.
        total_escalations: Number of tier upgrades (Haiku→Sonnet counts as 1).
        total_cost_estimate: Accumulated cost in USD across all attempts.

    """

    success: bool
    response: Any | None
    final_model: str
    attempts: list[AttemptResult] = field(default_factory=list)
    total_retries: int = 0
    total_escalations: int = 0
    total_cost_estimate: float = 0.0

    def summary(self) -> str:
        """Return a one-line human-readable summary of the result.

        Returns:
            String starting with ✓ on success or ✗ on failure.

        Example:
            >>> result.summary()
            '✓ claude-haiku-4-5-20251001, 1 retry(ies)'

        """
        if self.success:
            parts = [f"✓ {self.final_model}"]
            if self.total_retries:
                parts.append(f"{self.total_retries} retry(ies)")
            if self.total_escalations:
                parts.append(f"{self.total_escalations} escalation(s)")
            return ", ".join(parts)
        return f"✗ Failed after {len(self.attempts)} attempt(s)"
