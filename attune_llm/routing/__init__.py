"""Empathy Framework Model Routing

Smart routing of tasks to appropriate model tiers for cost optimization:
- CHEAP tier: Triage, summarization, classification (Haiku/GPT-4o-mini)
- CAPABLE tier: Code generation, analysis, sub-agent work (Sonnet/GPT-4o)
- PREMIUM tier: Coordination, synthesis, critical decisions (Opus/o1)

Example:
    >>> from attune_llm.routing import ModelRouter
    >>>
    >>> router = ModelRouter()
    >>> model = router.route("summarize", provider="anthropic")
    >>> print(model)  # claude-haiku-4-5-20251001
    >>>
    >>> model = router.route("coordinate", provider="anthropic")
    >>> print(model)  # claude-opus-4-20250514
    >>>
    >>> cost = router.estimate_cost("fix_bug", input_tokens=5000, output_tokens=1000)
    >>> print(f"Estimated cost: ${cost:.4f}")

Copyright 2025 Smart AI Memory, LLC
Licensed under Fair Source 0.9

"""

from .model_router import ModelRouter, ModelTier, TaskRouting

__all__ = [
    "ModelRouter",
    "ModelTier",
    "TaskRouting",
]
