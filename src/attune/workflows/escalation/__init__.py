"""EscalationChain — retry-with-feedback LLM escalation.

A general-purpose wrapper that starts on the cheapest model tier, retries
with injected failure feedback, and escalates only when retries are
exhausted. Optionally adds a semantic evaluator (Layer 2) after structural
validators pass.

Usage::

    from attune.workflows.escalation import escalate, EscalationChain
    from attune.workflows.escalation import StructureValidator, SemanticEvaluator

    # Simple convenience API
    result = await escalate(
        "What is 2+2?",
        required_fields=["answer"],
        retries=1,
    )

    # Full control
    chain = EscalationChain(
        validators=[StructureValidator(["answer", "confidence"])],
        evaluator=SemanticEvaluator(gate="last_tier"),
        retries_per_model=2,
    )
    result = await chain.run("Explain quantum entanglement.")
    print(result.summary())

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from attune.workflows.escalation.chain import EscalationChain
from attune.workflows.escalation.convenience import escalate
from attune.workflows.escalation.evaluator import Evaluator, SemanticEvaluator
from attune.workflows.escalation.models import (
    AttemptResult,
    EscalationResult,
    FeedbackType,
    ValidationFeedback,
)
from attune.workflows.escalation.validators import (
    ConfidenceValidator,
    StructureValidator,
    Validator,
)

__all__ = [
    "AttemptResult",
    "ConfidenceValidator",
    "EscalationChain",
    "EscalationResult",
    "Evaluator",
    "FeedbackType",
    "SemanticEvaluator",
    "StructureValidator",
    "ValidationFeedback",
    "Validator",
    "escalate",
]
