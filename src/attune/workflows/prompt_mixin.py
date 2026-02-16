"""Prompt Building Mixin for BaseWorkflow.

Extracted from BaseWorkflow to improve maintainability.
Provides prompt construction methods including XML template support.

Expected attributes on the host class:
    name (str): Workflow name
    description (str): Workflow description
    stages (list[str]): Stage names
    _config (WorkflowConfig | None): Workflow configuration
    get_tier_for_stage(stage_name): Returns tier for a stage
    get_model_for_tier(tier): Returns model for a tier

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class PromptMixin:
    """Mixin providing prompt building and rendering methods."""

    # Expected attributes (set by BaseWorkflow.__init__)
    name: str
    description: str
    stages: list[str]
    _config: Any  # WorkflowConfig | None

    def describe(self) -> str:
        """Get a human-readable description of the workflow."""
        lines = [
            f"Workflow: {self.name}",
            f"Description: {self.description}",
            "",
            "Stages:",
        ]

        for stage_name in self.stages:
            tier = self.get_tier_for_stage(stage_name)
            model = self.get_model_for_tier(tier)
            lines.append(f"  {stage_name}: {tier.value} ({model})")

        return "\n".join(lines)

    def _build_cached_system_prompt(
        self,
        role: str,
        guidelines: list[str] | None = None,
        documentation: str | None = None,
        examples: list[dict[str, str]] | None = None,
    ) -> str:
        """Build system prompt optimized for Anthropic prompt caching.

        Prompt caching works best with:
        - Static content (guidelines, docs, coding standards)
        - Frequent reuse (>3 requests within 5 min)
        - Large context (>1024 tokens)

        Structure: Static content goes first (cacheable), dynamic content
        goes in user messages (not cached).

        Args:
            role: The role for the AI (e.g., "expert code reviewer")
            guidelines: List of static guidelines/rules
            documentation: Static documentation or reference material
            examples: Static examples for few-shot learning

        Returns:
            System prompt with static content first for optimal caching

        Example:
            >>> prompt = workflow._build_cached_system_prompt(
            ...     role="code reviewer",
            ...     guidelines=[
            ...         "Follow PEP 8 style guide",
            ...         "Check for security vulnerabilities",
            ...     ],
            ...     documentation="Coding standards:\\n- Use type hints\\n- Add docstrings",
            ... )
            >>> # This prompt will be cached by Anthropic for 5 minutes
            >>> # Subsequent calls with same prompt read from cache (90% cost reduction)
        """
        parts = []

        # 1. Role definition (static)
        parts.append(f"You are a {role}.")

        # 2. Guidelines (static - most important for caching)
        if guidelines:
            parts.append("\n# Guidelines\n")
            for i, guideline in enumerate(guidelines, 1):
                parts.append(f"{i}. {guideline}")

        # 3. Documentation (static - good caching candidate)
        if documentation:
            parts.append("\n# Reference Documentation\n")
            parts.append(documentation)

        # 4. Examples (static - excellent for few-shot learning)
        if examples:
            parts.append("\n# Examples\n")
            for i, example in enumerate(examples, 1):
                input_text = example.get("input", "")
                output_text = example.get("output", "")
                parts.append(f"\nExample {i}:")
                parts.append(f"Input: {input_text}")
                parts.append(f"Output: {output_text}")

        # Dynamic content (user-specific context, current task) should go
        # in the user message, NOT in system prompt
        parts.append(
            "\n# Instructions\n"
            "The user will provide the specific task context in their message. "
            "Apply the above guidelines and reference documentation to their request."
        )

        return "\n".join(parts)

    # =========================================================================
    # XML Prompt Integration (Phase 4)
    # =========================================================================

    def _get_xml_config(self) -> dict[str, Any]:
        """Get XML prompt configuration for this workflow.

        Returns:
            Dictionary with XML configuration settings.

        """
        if self._config is None:
            return {}
        return self._config.get_xml_config_for_workflow(self.name)

    def _is_xml_enabled(self) -> bool:
        """Check if XML prompts are enabled for this workflow.

        Defaults to True — XML prompts are enabled unless explicitly disabled
        via workflow config. Benchmarks on Claude 4.x show XML is cost-neutral
        with better structured parsing.
        """
        config = self._get_xml_config()
        return bool(config.get("enabled", True))

    def _render_xml_prompt(
        self,
        role: str,
        goal: str,
        instructions: list[str],
        constraints: list[str],
        input_type: str,
        input_payload: str,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """Render a prompt using XML template if enabled.

        Args:
            role: The role for the AI (e.g., "security analyst").
            goal: The primary objective.
            instructions: Step-by-step instructions.
            constraints: Rules and guidelines.
            input_type: Type of input ("code", "diff", "document").
            input_payload: The content to process.
            extra: Additional context data.

        Returns:
            Rendered prompt string (XML if enabled, plain text otherwise).

        """
        from attune.prompts import PromptContext, XmlPromptTemplate, get_template

        config = self._get_xml_config()

        if not config.get("enabled", True):
            # Fall back to plain text (XML explicitly disabled)
            return self._render_plain_prompt(
                role,
                goal,
                instructions,
                constraints,
                input_type,
                input_payload,
            )

        # Create context
        context = PromptContext(
            role=role,
            goal=goal,
            instructions=instructions,
            constraints=constraints,
            input_type=input_type,
            input_payload=input_payload,
            extra=extra or {},
        )

        # Get template
        template_name = config.get("template_name", self.name)
        template = get_template(template_name)

        if template is None:
            # Create a basic XML template if no built-in found
            template = XmlPromptTemplate(
                name=self.name,
                schema_version=config.get("schema_version", "1.0"),
            )

        return template.render(context)

    def _render_plain_prompt(
        self,
        role: str,
        goal: str,
        instructions: list[str],
        constraints: list[str],
        input_type: str,
        input_payload: str,
    ) -> str:
        """Render a plain text prompt (fallback when XML is disabled)."""
        parts = [f"You are a {role}.", "", f"Goal: {goal}", ""]

        if instructions:
            parts.append("Instructions:")
            for i, inst in enumerate(instructions, 1):
                parts.append(f"{i}. {inst}")
            parts.append("")

        if constraints:
            parts.append("Guidelines:")
            for constraint in constraints:
                parts.append(f"- {constraint}")
            parts.append("")

        if input_payload:
            parts.append(f"Input ({input_type}):")
            parts.append(input_payload)

        return "\n".join(parts)
