"""Convenience API for EscalationChain.

Provides a simple ``escalate()`` function for common use cases.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from attune.workflows.escalation.chain import EscalationChain
from attune.workflows.escalation.evaluator import SemanticEvaluator
from attune.workflows.escalation.models import EscalationResult
from attune.workflows.escalation.validators import ConfidenceValidator, StructureValidator


async def escalate(
    prompt: str,
    required_fields: list[str] | None = None,
    min_confidence: float | None = None,
    system_prompt: str | None = None,
    retries: int = 0,
    use_evaluator: bool = False,
) -> EscalationResult:
    """Run a prompt through the escalation chain.

    Quick-start API with sensible defaults. Backward compatible —
    ``retries=0`` produces identical behavior to a plain LLM call with
    no retry logic.

    Args:
        prompt: User prompt to send.
        required_fields: Field names that must be present in the JSON response.
            Adds a StructureValidator when provided.
        min_confidence: Minimum ``confidence`` value (0.0–1.0) required in
            the response dict. Adds a ConfidenceValidator when provided.
        system_prompt: Optional system prompt sent with every call.
        retries: Same-model retries before escalating. Default 0 (opt-in).
        use_evaluator: When True, adds a SemanticEvaluator (Haiku, always gate).

    Returns:
        EscalationResult with the response and full audit trail.

    Example:
        >>> # Minimal — same as a direct LLM call
        >>> result = await escalate("What is 2+2?", required_fields=["answer"])

        >>> # Opt in to retry-with-feedback
        >>> result = await escalate(
        ...     "What is 2+2?",
        ...     required_fields=["answer"],
        ...     retries=1,
        ... )

        >>> # Full feedback loop with semantic evaluation
        >>> result = await escalate(
        ...     "Analyze this dataset...",
        ...     required_fields=["analysis", "conclusion"],
        ...     use_evaluator=True,
        ...     retries=2,
        ... )

    """
    validators = []
    if required_fields:
        validators.append(StructureValidator(required_fields))
    if min_confidence is not None:
        validators.append(ConfidenceValidator(min_confidence=min_confidence))

    evaluator = SemanticEvaluator() if use_evaluator else None

    chain = EscalationChain(
        validators=validators,
        evaluator=evaluator,
        retries_per_model=retries,
        system_prompt=system_prompt,
    )

    return await chain.run(prompt)
