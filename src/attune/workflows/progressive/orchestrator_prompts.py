"""Tier-specific prompt building for the MetaOrchestrator.

Generates XML-enhanced prompts with failure context for each tier level
(cheap, capable, premium) during progressive tier escalation.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import Any

from attune.workflows.progressive.core import Tier


class TierPromptMixin:
    """Mixin providing tier-specific prompt building methods.

    Used by MetaOrchestrator to generate XML-enhanced prompts
    with failure context from previous tiers.
    """

    def build_tier_prompt(
        self,
        tier: Tier,
        base_task: str,
        failure_context: dict[str, Any] | None = None,
    ) -> str:
        """Build XML-enhanced prompt with failure context.

        Creates tier-appropriate prompts:
        - CHEAP: Simple, focused prompt
        - CAPABLE: Enhanced with failure analysis from cheap tier
        - PREMIUM: Comprehensive with full escalation context

        Args:
            tier: Which tier this prompt is for
            base_task: Base task description
            failure_context: Context from previous tier (if escalating)

        Returns:
            XML-enhanced prompt string

        """
        if tier == Tier.CHEAP:
            return self._build_cheap_prompt(base_task)
        if tier == Tier.CAPABLE:
            return self._build_capable_prompt(base_task, failure_context)
        # PREMIUM
        return self._build_premium_prompt(base_task, failure_context)

    def _build_cheap_prompt(self, base_task: str) -> str:
        """Build simple prompt for cheap tier.

        Args:
            base_task: Task description

        Returns:
            XML-enhanced prompt

        """
        return f"""<task>
  <objective>{base_task}</objective>

  <quality_requirements>
    <pass_rate>70%+</pass_rate>
    <coverage>60%+</coverage>
    <syntax>No syntax errors</syntax>
  </quality_requirements>

  <instructions>
    Generate high-quality output that meets the quality requirements.
    Focus on correctness and completeness.
  </instructions>
</task>"""

    def _build_capable_prompt(self, base_task: str, failure_context: dict[str, Any] | None) -> str:
        """Build enhanced prompt for capable tier with failure context.

        Args:
            base_task: Task description
            failure_context: Context from cheap tier

        Returns:
            XML-enhanced prompt with failure analysis

        """
        if not failure_context:
            # No context, use enhanced base prompt
            return f"""<task>
  <objective>{base_task}</objective>

  <quality_requirements>
    <pass_rate>80%+</pass_rate>
    <coverage>70%+</coverage>
    <quality_score>80+</quality_score>
  </quality_requirements>

  <instructions>
    Generate high-quality output with comprehensive coverage.
    Ensure all edge cases are handled correctly.
  </instructions>
</task>"""

        # Extract detailed failure context
        previous_cqs = failure_context.get("previous_cqs", 0)
        reason = failure_context.get("reason", "Quality below threshold")
        failures = failure_context.get("failures", [])
        examples = failure_context.get("examples", [])

        # Analyze failure patterns
        failure_patterns = self.analyze_failure_patterns(failures) if failures else {}

        # Build detailed prompt with failure analysis
        prompt_parts = [
            "<task>",
            f"  <objective>{base_task}</objective>",
            "",
            "  <context_from_previous_tier>",
            "    <tier>cheap</tier>",
            f"    <quality_score>{previous_cqs:.1f}</quality_score>",
            f"    <escalation_reason>{reason}</escalation_reason>",
            "",
        ]

        # Add failure pattern analysis
        if failure_patterns:
            prompt_parts.append("    <failure_analysis>")
            prompt_parts.append(
                f"      <total_failures>{failure_patterns.get('total_failures', 0)}</total_failures>",
            )
            prompt_parts.append("      <patterns>")

            error_types = failure_patterns.get("error_types", {})
            for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
                prompt_parts.append(f'        <pattern type="{error_type}" count="{count}" />')

            prompt_parts.append("      </patterns>")

            primary_issue = failure_patterns.get("primary_issue", "unknown")
            prompt_parts.append(f"      <primary_issue>{primary_issue}</primary_issue>")
            prompt_parts.append("    </failure_analysis>")
            prompt_parts.append("")

        # Add concrete failure examples (max 3)
        if examples:
            prompt_parts.append("    <failed_attempts>")
            prompt_parts.append("      <!-- Examples of what the cheap tier produced -->")

            for i, example in enumerate(examples[:3], 1):
                error = example.get("error", "Unknown error")
                code_snippet = example.get("code", "")[:200]  # Limit snippet length

                prompt_parts.append(f'      <example number="{i}">')
                prompt_parts.append(f"        <error>{self._escape_xml(error)}</error>")
                if code_snippet:
                    prompt_parts.append(
                        f"        <code_snippet>{self._escape_xml(code_snippet)}</code_snippet>",
                    )
                prompt_parts.append("      </example>")

            prompt_parts.append("    </failed_attempts>")
            prompt_parts.append("")

        prompt_parts.extend(
            [
                "    <improvement_needed>",
                "      The cheap tier struggled with these items. Analyze the failure",
                "      patterns above and generate improved solutions that specifically",
                "      address these issues.",
                "    </improvement_needed>",
                "  </context_from_previous_tier>",
                "",
                "  <your_task>",
                "    Generate improved output that avoids the specific failure patterns identified above.",
                "",
                "    <quality_requirements>",
                "      <pass_rate>80%+</pass_rate>",
                "      <coverage>70%+</coverage>",
                "      <quality_score>80+</quality_score>",
                "    </quality_requirements>",
                "",
                "    <focus_areas>",
            ],
        )

        # Add targeted focus areas based on failure patterns
        if failure_patterns:
            error_types = failure_patterns.get("error_types", {})
            if "async_errors" in error_types:
                prompt_parts.append(
                    '      <focus area="async">Proper async/await patterns and error handling</focus>',
                )
            if "mocking_errors" in error_types:
                prompt_parts.append(
                    '      <focus area="mocking">Correct mock setup and teardown</focus>',
                )
            if "syntax_errors" in error_types:
                prompt_parts.append(
                    '      <focus area="syntax">Valid Python syntax and imports</focus>',
                )
            if "other_errors" in error_types:
                prompt_parts.append(
                    '      <focus area="general">Edge cases and error handling</focus>',
                )
        else:
            # Default focus areas
            prompt_parts.extend(
                [
                    '      <focus area="syntax">Correct syntax and structure</focus>',
                    '      <focus area="coverage">Comprehensive test coverage</focus>',
                    '      <focus area="errors">Proper error handling</focus>',
                    '      <focus area="edge_cases">Edge case coverage</focus>',
                ],
            )

        prompt_parts.extend(["    </focus_areas>", "  </your_task>", "</task>"])

        return "\n".join(prompt_parts)

    def _build_premium_prompt(self, base_task: str, failure_context: dict[str, Any] | None) -> str:
        """Build comprehensive prompt for premium tier.

        Args:
            base_task: Task description
            failure_context: Context from previous tiers

        Returns:
            XML-enhanced prompt with full escalation context

        """
        if not failure_context:
            return f"""<task>
  <objective>{base_task}</objective>

  <quality_requirements>
    <pass_rate>95%+</pass_rate>
    <coverage>85%+</coverage>
    <quality_score>95+</quality_score>
  </quality_requirements>

  <expert_instructions>
    Apply expert-level techniques to generate exceptional output.
    This is the highest tier - excellence is expected.
  </expert_instructions>
</task>"""

        # Extract comprehensive escalation context
        previous_tier = failure_context.get("previous_tier", Tier.CAPABLE)
        previous_cqs = failure_context.get("previous_cqs", 0)
        reason = failure_context.get("reason", "Previous tier unsuccessful")
        failures = failure_context.get("failures", [])
        examples = failure_context.get("examples", [])

        # Analyze persistent failure patterns
        failure_patterns = self.analyze_failure_patterns(failures) if failures else {}

        prompt_parts = [
            "<task>",
            f"  <objective>{base_task}</objective>",
            "",
            "  <escalation_context>",
            f"    <previous_tier>{previous_tier.value}</previous_tier>",
            f"    <quality_score>{previous_cqs:.1f}</quality_score>",
            f"    <escalation_reason>{self._escape_xml(reason)}</escalation_reason>",
            "",
            "    <progression_analysis>",
            "      This task has been escalated through multiple tiers:",
            "      1. CHEAP tier: Initial attempt with basic models",
            "      2. CAPABLE tier: Enhanced attempt with better models",
            "      3. PREMIUM tier (current): Final expert-level attempt",
            "",
            "      The fact that this reached premium tier indicates a complex",
            "      or difficult case requiring expert-level handling.",
            "    </progression_analysis>",
            "",
        ]

        # Add detailed failure analysis
        if failure_patterns:
            prompt_parts.append("    <persistent_issues>")
            prompt_parts.append(
                f"      <total_failures>{failure_patterns.get('total_failures', 0)}</total_failures>",
            )
            prompt_parts.append("      <failure_patterns>")

            error_types = failure_patterns.get("error_types", {})
            for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
                prompt_parts.append(f'        <pattern type="{error_type}" count="{count}">')

                # Add specific guidance per error type
                if error_type == "async_errors":
                    prompt_parts.append(
                        "          <guidance>Use proper async/await patterns, handle timeouts correctly</guidance>",
                    )
                elif error_type == "mocking_errors":
                    prompt_parts.append(
                        "          <guidance>Ensure mocks are properly configured and reset</guidance>",
                    )
                elif error_type == "syntax_errors":
                    prompt_parts.append(
                        "          <guidance>Double-check syntax, imports, and type annotations</guidance>",
                    )

                prompt_parts.append("        </pattern>")

            prompt_parts.append("      </failure_patterns>")
            prompt_parts.append(
                f"      <primary_issue>{failure_patterns.get('primary_issue', 'unknown')}</primary_issue>",
            )
            prompt_parts.append("    </persistent_issues>")
            prompt_parts.append("")

        # Add concrete examples from capable tier
        if examples:
            prompt_parts.append("    <capable_tier_attempts>")
            prompt_parts.append("      <!-- Examples from the capable tier's attempts -->")

            for i, example in enumerate(examples[:3], 1):
                error = example.get("error", "Unknown error")
                code_snippet = example.get("code", "")[:300]  # More context for premium
                quality_score = example.get("quality_score", 0)

                prompt_parts.append(f'      <attempt number="{i}" quality_score="{quality_score}">')
                prompt_parts.append(f"        <error>{self._escape_xml(error)}</error>")
                if code_snippet:
                    prompt_parts.append(
                        f"        <code_snippet>{self._escape_xml(code_snippet)}</code_snippet>",
                    )
                prompt_parts.append("      </attempt>")

            prompt_parts.append("    </capable_tier_attempts>")
            prompt_parts.append("")

        prompt_parts.extend(
            [
                "  </escalation_context>",
                "",
                "  <expert_task>",
                "    <critical_notice>",
                "      You are the FINAL tier in the progressive escalation system.",
                "      Previous tiers (cheap and capable) have attempted this task",
                "      multiple times and could not achieve the required quality.",
                "",
                "      This is the last automated attempt before human review.",
                "      Excellence is not optional - it is required.",
                "    </critical_notice>",
                "",
                "    <expert_techniques>",
                "      Apply sophisticated approaches:",
                "      - Deep analysis of why previous attempts failed",
                "      - Production-grade error handling and edge cases",
                "      - Comprehensive documentation and clarity",
                "      - Defensive programming against subtle bugs",
            ],
        )

        # Add specific techniques based on failure patterns
        if failure_patterns:
            error_types = failure_patterns.get("error_types", {})
            if "async_errors" in error_types:
                prompt_parts.append(
                    "      - Advanced async patterns (asyncio.gather, proper timeouts)",
                )
            if "mocking_errors" in error_types:
                prompt_parts.append(
                    "      - Sophisticated mocking (pytest fixtures, proper lifecycle)",
                )
            if "syntax_errors" in error_types:
                prompt_parts.append("      - Rigorous syntax validation before submission")

        prompt_parts.extend(
            [
                "    </expert_techniques>",
                "",
                "    <quality_requirements>",
                "      <pass_rate>95%+</pass_rate>",
                "      <coverage>85%+</coverage>",
                "      <quality_score>95+</quality_score>",
                "      <zero_syntax_errors>MANDATORY</zero_syntax_errors>",
                "    </quality_requirements>",
                "",
                "    <success_criteria>",
                "      Your implementation must:",
                "      1. Address ALL failure patterns identified above",
                "      2. Achieve exceptional quality scores (95+)",
                "      3. Have zero syntax errors or runtime failures",
                "      4. Include comprehensive edge case coverage",
                "      5. Be production-ready with proper documentation",
                "    </success_criteria>",
                "  </expert_task>",
                "</task>",
            ],
        )

        return "\n".join(prompt_parts)

    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters.

        Args:
            text: Text to escape

        Returns:
            XML-safe text

        """
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
