"""Internal workflow bridge for wizard LLM access.

Provides a thin ``BaseWorkflow`` subclass that gives wizards access
to all 12 mixins (LLM calls, caching, telemetry, XML prompts,
response parsing, cost tracking, etc.) without inheriting the
linear stage-pipeline execution model.

Wizards call mixin methods directly via ``self._workflow``:

    response = await self._workflow._call_llm(prompt, tier, "analyze")
    prompt   = self._workflow._render_xml_prompt(role=..., goal=..., ...)
    parsed   = self._workflow._parse_xml_response(response_text)

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import Any

from attune.workflows.base import BaseWorkflow
from attune.workflows.compat import ModelTier


class WizardInternalWorkflow(BaseWorkflow):
    """Thin BaseWorkflow wrapper that gives wizards access to all mixins.

    This is NOT a real multi-stage workflow. It exists solely to instantiate
    BaseWorkflow's 12 mixins so that ``BaseWizard`` can delegate LLM calls,
    XML prompt rendering, caching, telemetry, and response parsing to them.

    Args:
        provider: Model provider string (e.g. "anthropic").
        **kwargs: Forwarded to ``BaseWorkflow.__init__``.

    """

    name = "wizard-internal"
    description = "Internal workflow bridge for wizard LLM access"
    stages: list[str] = []
    tier_map: dict[str, ModelTier] = {}

    def __init__(self, provider: str | None = None, **kwargs: Any) -> None:
        super().__init__(provider=provider, **kwargs)

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Not used -- wizards call mixin methods directly.

        Raises:
            NotImplementedError: Always.

        """
        raise NotImplementedError("Wizards do not use run_stage")
