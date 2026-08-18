"""Outline stage mixin for document generation workflow.

Handles the first stage: analyzing source code and generating
a structured documentation outline.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
import re
from pathlib import Path

from attune.context import TokenBudgetAllocator

from ..base import ModelTier

logger = logging.getLogger(__name__)


class OutlineStageMixin:
    """Mixin providing the outline generation stage.

    Requires the host class to provide:
    - ``self.enable_auth_strategy``: bool
    - ``self._auth_mode_used``: str | None
    - ``self._call_llm()``: LLM call method
    """

    async def _outline(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Generate document outline from source."""
        source_code = input_data.get("source_code", "")
        target = input_data.get("target", "")
        doc_type = input_data.get("doc_type", "general")
        audience = input_data.get("audience", "developers")

        # Use target if source_code not provided
        content_to_document = source_code or target

        # If target looks like a file path and source_code wasn't provided, read the file
        if not source_code and target:
            content_to_document = self._read_target_file(target, content_to_document)

        # Auth strategy integration
        if self.enable_auth_strategy:
            self._detect_auth_strategy(target, content_to_document)

        system = """You are an expert technical writer specializing in API Reference documentation.

IMPORTANT: This is API REFERENCE documentation, not a tutorial. Focus on documenting EVERY function/class with structured Args/Returns/Raises format.

Create a detailed, structured outline for API Reference documentation:

1. **Logical Section Structure** (emphasize API reference sections):
   - Overview/Introduction (brief)
   - Quick Start (1 complete example)
   - API Reference - Functions (one subsection per function with Args/Returns/Raises)
   - API Reference - Classes (one subsection per class with Args/Returns/Raises for methods)
   - Usage Examples (showing how to combine multiple functions)
   - Additional reference sections as needed

2. **For Each Section**:
   - Clear purpose and what readers will learn
   - Specific topics to cover
   - Types of examples to include (with actual code)

3. **Key Requirements**:
   - Include sections for real, copy-paste ready code examples
   - Plan for comprehensive API documentation with all parameters
   - Include edge cases and error handling examples
   - Add best practices and common patterns

Format as a numbered list with section titles and detailed descriptions."""

        user_message = f"""Create a comprehensive documentation outline:

Document Type: {doc_type}
Target Audience: {audience}

IMPORTANT: This documentation should be production-ready with:
- Real, executable code examples (not placeholders)
- Complete API reference with parameter types and descriptions
- Usage guides showing common patterns
- Edge case handling and error scenarios
- Best practices for the target audience

Content to document:
{TokenBudgetAllocator().fit_source(content_to_document, token_limit=1000)}

Generate an outline that covers all these aspects comprehensively."""

        response, input_tokens, output_tokens = await self._call_llm(
            tier,
            system,
            user_message,
            max_tokens=1000,
        )

        return (
            {
                "outline": response,
                "doc_type": doc_type,
                "audience": audience,
                "content_to_document": content_to_document,
            },
            input_tokens,
            output_tokens,
        )

    def _read_target_file(self, target: str, fallback: str) -> str:
        """Read target file content if it exists.

        Args:
            target: File path to read.
            fallback: Content to return if file cannot be read.

        Returns:
            File content or fallback string.

        """
        target_path = Path(target)
        if target_path.exists() and target_path.is_file():
            try:
                content = target_path.read_text(encoding="utf-8")
                return f"# File: {target}\n\n{content}"
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Could not read file {target}: {e}")
        elif target_path.suffix in (
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".java",
            ".go",
            ".rs",
            ".md",
            ".txt",
        ):
            logger.warning(
                f"Target appears to be a file path but doesn't exist: {target}",
            )
        return fallback

    def _detect_auth_strategy(self, target: str, content: str) -> None:
        """Detect module size and recommend auth mode.

        Args:
            target: Target file path.
            content: Content to document.

        """
        try:
            from attune.models import (
                count_lines_of_code,
                get_auth_strategy,
                get_module_size_category,
            )

            module_lines = 0
            if target and Path(target).exists():
                module_lines = count_lines_of_code(target)
            elif content:
                module_lines = len(
                    [
                        line
                        for line in content.split("\n")
                        if line.strip() and not line.strip().startswith("#")
                    ],
                )

            if module_lines > 0:
                strategy = get_auth_strategy()
                recommended_mode = strategy.get_recommended_mode(module_lines)
                self._auth_mode_used = recommended_mode.value
                size_category = get_module_size_category(module_lines)

                logger.info(f"Module: {target or 'source'} ({module_lines} LOC, {size_category})")
                logger.info(f"Recommended auth mode: {recommended_mode.value}")

                cost_estimate = strategy.estimate_cost(module_lines, recommended_mode)
                if recommended_mode.value == "subscription":
                    logger.info(
                        f"Cost: {cost_estimate['quota_cost']} "
                        f"(fits in {cost_estimate['fits_in_context']} context)",
                    )
                else:
                    logger.info(
                        f"Cost: ~${cost_estimate['monetary_cost']:.4f} (1M context window)",
                    )

        except Exception as e:  # noqa: BLE001
            logger.warning(f"Auth strategy detection failed: {e}")

    def _parse_outline_sections(self, outline: str) -> list[str]:
        """Parse top-level section titles from the outline.

        Only matches main sections like "1. Introduction", "2. Setup", etc.
        Ignores sub-sections like "2.1 Prerequisites" or nested items.

        Args:
            outline: Raw outline text from LLM.

        Returns:
            List of section title strings.

        """
        sections: list[str] = []
        top_level_pattern = re.compile(r"^(\d+)\.\s+([A-Za-z].*)")

        for line in outline.split("\n"):
            stripped = line.strip()
            match = top_level_pattern.match(stripped)
            if match:
                title = match.group(2).strip()
                if " - " in title:
                    title = title.split(" - ")[0].strip()
                sections.append(title)

        return sections
