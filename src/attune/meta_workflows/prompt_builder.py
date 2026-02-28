"""Prompt building utilities for meta-workflow agents.

Provides functions for constructing LLM prompts from agent specifications,
including role-based instruction generation and template loading.

Created: 2026-02-19
Purpose: Extracted from workflow.py for focused module design
"""

import json
import logging

from attune.meta_workflows.models import AgentSpec
from attune.orchestration.agent_templates import get_template

logger = logging.getLogger(__name__)


def get_generic_instructions(role: str) -> str:
    """Generate generic instructions based on agent role.

    Maps common role keywords to appropriate instruction sets.
    Used as a fallback when a named template is not found.

    Args:
        role: Agent role name

    Returns:
        Generic instructions appropriate for the role

    """
    role_lower = role.lower()

    if "analyst" in role_lower or "analyze" in role_lower:
        return (
            "You are an expert analyst. Your job is to thoroughly analyze "
            "the provided information, identify key patterns, issues, and "
            "opportunities. Provide detailed findings with specific evidence "
            "and actionable recommendations."
        )
    if "reviewer" in role_lower or "review" in role_lower:
        return (
            "You are a careful reviewer. Your job is to review the provided "
            "content for quality, accuracy, completeness, and adherence to "
            "best practices. Identify any issues, gaps, or areas for improvement "
            "and provide specific feedback."
        )
    if "generator" in role_lower or "create" in role_lower or "writer" in role_lower:
        return (
            "You are a skilled content generator. Your job is to create "
            "high-quality content based on the provided requirements and context. "
            "Ensure your output is well-structured, accurate, and follows "
            "established conventions."
        )
    if "validator" in role_lower or "verify" in role_lower:
        return (
            "You are a thorough validator. Your job is to verify the provided "
            "content meets all requirements and standards. Check for correctness, "
            "completeness, and consistency. Report any issues found."
        )
    if "synthesizer" in role_lower or "combine" in role_lower:
        return (
            "You are an expert synthesizer. Your job is to combine multiple "
            "inputs into a cohesive, well-organized output. Identify common "
            "themes, resolve conflicts, and produce a unified result that "
            "captures the key insights from all sources."
        )
    if "test" in role_lower:
        return (
            "You are a testing specialist. Your job is to analyze code and "
            "create comprehensive test cases that cover edge cases, error "
            "conditions, and normal operation. Ensure tests are well-documented "
            "and maintainable."
        )
    if "doc" in role_lower:
        return (
            "You are a documentation specialist. Your job is to analyze content "
            "and create or improve documentation that is clear, accurate, and "
            "helpful. Follow documentation best practices and maintain consistency."
        )
    return (
        f"You are a {role} agent. Complete your assigned task thoroughly "
        "and provide clear, well-structured output. Follow best practices "
        "and provide actionable results."
    )


def build_agent_prompt(agent: AgentSpec) -> str:
    """Build prompt for agent from specification.

    Loads the base template for the agent's role and constructs a
    complete prompt including configuration, success criteria, and
    available tools.

    Args:
        agent: Agent specification

    Returns:
        Formatted prompt string

    """
    # Load base template
    base_template = get_template(agent.base_template)
    if base_template is not None:
        instructions = base_template.default_instructions
    else:
        # Fallback if template not found - use role-based generic prompt
        logger.warning(f"Template {agent.base_template} not found, using generic prompt")
        instructions = get_generic_instructions(agent.role)

    # Build prompt
    prompt_parts = [
        f"Role: {agent.role}",
        f"\nInstructions:\n{instructions}",
    ]

    # Add config if present
    if agent.config:
        prompt_parts.append(f"\nConfiguration:\n{json.dumps(agent.config, indent=2)}")

    # Add success criteria if present
    if agent.success_criteria:
        prompt_parts.append(f"\nSuccess Criteria:\n{json.dumps(agent.success_criteria, indent=2)}")

    # Add tools if present
    if agent.tools:
        prompt_parts.append(f"\nAvailable Tools: {', '.join(agent.tools)}")

    return "\n".join(prompt_parts)
