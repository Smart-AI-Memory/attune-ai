"""LLM-Powered Explanation Generator

Uses LLM to generate richer, more natural workflow explanations
as an alternative to the rule-based WorkflowExplainer.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import os

from .blueprint import WorkflowBlueprint
from .explainer_types import AudienceLevel, DetailLevel


class LLMExplanationGenerator:
    """Uses LLM to generate richer, more natural explanations."""

    EXPLAIN_PROMPT = """Generate a clear, helpful explanation of this workflow for a {audience} audience.

Workflow: {name}
Description: {description}
Domain: {domain}
Agents: {agents}
Stages: {stages}

Write a {detail_level} explanation that:
1. Explains what the workflow does in plain language
2. Describes each agent's role
3. Walks through the process step by step
4. Highlights the value and benefits

Format as markdown with clear sections."""

    def __init__(self, api_key: str | None = None):
        """Initialize the generator.

        Args:
            api_key: Anthropic API key

        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None

    def _get_client(self):
        """Lazy-load Anthropic client."""
        if self._client is None and self.api_key:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                pass
        return self._client

    def generate(
        self,
        blueprint: WorkflowBlueprint,
        audience: AudienceLevel = AudienceLevel.BUSINESS,
        detail_level: DetailLevel = DetailLevel.STANDARD,
    ) -> str:
        """Generate LLM-powered explanation.

        Args:
            blueprint: The workflow blueprint
            audience: Target audience
            detail_level: Level of detail

        Returns:
            Generated explanation markdown

        """
        client = self._get_client()
        if not client:
            # Fallback to rule-based explainer (lazy import to avoid circular)
            from .explainer import WorkflowExplainer

            explainer = WorkflowExplainer(audience=audience, detail_level=detail_level)
            return explainer.explain_workflow(blueprint).to_markdown()

        # Format workflow info for prompt
        agents_str = "\n".join(
            f"- {a.name} ({a.role.value}): {a.description}" for a in blueprint.agents
        )

        stages_str = "\n".join(
            f"- {s.name}: {', '.join(s.agent_ids)}" + (" (parallel)" if s.parallel else "")
            for s in blueprint.stages
        )

        prompt = self.EXPLAIN_PROMPT.format(
            audience=audience.value,
            name=blueprint.name,
            description=blueprint.description,
            domain=blueprint.domain,
            agents=agents_str,
            stages=stages_str,
            detail_level=detail_level.value,
        )

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text if response.content else ""
        except Exception:
            # Fallback (lazy import to avoid circular)
            from .explainer import WorkflowExplainer

            explainer = WorkflowExplainer(audience=audience, detail_level=detail_level)
            return explainer.explain_workflow(blueprint).to_markdown()
