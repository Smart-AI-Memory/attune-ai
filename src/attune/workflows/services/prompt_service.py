"""Prompt building service for workflows.

Standalone service extracted from PromptMixin. Provides prompt construction
including XML template support and caching-optimized system prompts.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import Any


class PromptService:
    """Service for building and rendering prompts.

    Supports plain text and XML-formatted prompts with Anthropic prompt
    caching optimization.

    Args:
        workflow_name: Name of the workflow
        xml_config: Optional XML configuration dict. Keys:
            - enabled (bool): Whether XML prompts are enabled
            - template_name (str): Template name to use
            - schema_version (str): XML schema version
            - enforce_response_xml (bool): Whether to enforce XML in responses

    Example:
        >>> prompt_svc = PromptService("code-review", xml_config={"enabled": True})
        >>> prompt = prompt_svc.render_xml(
        ...     role="security analyst",
        ...     goal="Find vulnerabilities",
        ...     instructions=["Check for SQL injection"],
        ...     constraints=["Focus on user input paths"],
        ...     input_type="code",
        ...     input_payload=code_content,
        ... )

    """

    def __init__(
        self,
        workflow_name: str,
        xml_config: dict[str, Any] | None = None,
    ) -> None:
        self._workflow_name = workflow_name
        self._xml_config = xml_config or {}

    @property
    def xml_enabled(self) -> bool:
        """Whether XML prompts are enabled.

        Defaults to True — XML prompts produce better structured output
        at cost-neutral token overhead on Claude 4.x models.
        """
        return bool(self._xml_config.get("enabled", True))

    @property
    def xml_config(self) -> dict[str, Any]:
        """Get the XML configuration dict."""
        return self._xml_config

    def build_cached_system_prompt(
        self,
        role: str,
        guidelines: list[str] | None = None,
        documentation: str | None = None,
        examples: list[dict[str, str]] | None = None,
    ) -> str:
        """Build system prompt optimized for Anthropic prompt caching.

        Static content goes first (cacheable), dynamic content goes in user messages.

        Args:
            role: The role for the AI (e.g., "expert code reviewer")
            guidelines: List of static guidelines/rules
            documentation: Static documentation or reference material
            examples: Static examples for few-shot learning

        Returns:
            System prompt with static content first for optimal caching

        """
        parts = []

        parts.append(f"You are a {role}.")

        if guidelines:
            parts.append("\n# Guidelines\n")
            for i, guideline in enumerate(guidelines, 1):
                parts.append(f"{i}. {guideline}")

        if documentation:
            parts.append("\n# Reference Documentation\n")
            parts.append(documentation)

        if examples:
            parts.append("\n# Examples\n")
            for i, example in enumerate(examples, 1):
                input_text = example.get("input", "")
                output_text = example.get("output", "")
                parts.append(f"\nExample {i}:")
                parts.append(f"Input: {input_text}")
                parts.append(f"Output: {output_text}")

        parts.append(
            "\n# Instructions\n"
            "The user will provide the specific task context in their message. "
            "Apply the above guidelines and reference documentation to their request.",
        )

        return "\n".join(parts)

    def render_xml(
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

        Falls back to plain text if XML is disabled.

        Args:
            role: The role for the AI
            goal: The primary objective
            instructions: Step-by-step instructions
            constraints: Rules and guidelines
            input_type: Type of input ("code", "diff", "document")
            input_payload: The content to process
            extra: Additional context data

        Returns:
            Rendered prompt string (XML if enabled, plain text otherwise)

        """
        if not self.xml_enabled:
            return self.render_plain(
                role,
                goal,
                instructions,
                constraints,
                input_type,
                input_payload,
            )

        from attune.prompts import PromptContext, XmlPromptTemplate, get_template

        context = PromptContext(
            role=role,
            goal=goal,
            instructions=instructions,
            constraints=constraints,
            input_type=input_type,
            input_payload=input_payload,
            extra=extra or {},
        )

        template_name = self._xml_config.get("template_name", self._workflow_name)
        template = get_template(template_name)

        if template is None:
            template = XmlPromptTemplate(
                name=self._workflow_name,
                schema_version=self._xml_config.get("schema_version", "1.0"),
            )

        return template.render(context)

    def render_plain(
        self,
        role: str,
        goal: str,
        instructions: list[str],
        constraints: list[str],
        input_type: str,
        input_payload: str,
    ) -> str:
        """Render a plain text prompt.

        Args:
            role: The role for the AI
            goal: The primary objective
            instructions: Step-by-step instructions
            constraints: Rules and guidelines
            input_type: Type of input
            input_payload: The content to process

        Returns:
            Rendered plain text prompt

        """
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
