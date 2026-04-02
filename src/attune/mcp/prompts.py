"""Prompt handling for Attune AI MCP Server.

Provides prompt list and prompt message generation for MCP prompt resources.
"""

from __future__ import annotations

import re
from typing import Any


def _sanitize_prompt_arg(value: str) -> str:
    """Sanitize a user-supplied value before prompt interpolation.

    Strips characters that could manipulate prompt structure:
    backticks, newlines, and control characters.

    Args:
        value: Raw user input.

    Returns:
        Sanitized string safe for prompt interpolation.
    """
    # Remove backticks (prevent code fence injection)
    # Remove newlines (prevent prompt structure manipulation)
    # Remove control characters
    sanitized = re.sub(r"[`\n\r\x00-\x1f]", "", value)
    # Truncate to reasonable length
    return sanitized[:500]


def get_prompt_list(prompts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Get list of available prompts.

    Args:
        prompts: Prompt definitions dictionary

    Returns:
        List of prompt definitions

    """
    return list(prompts.values())


def get_prompt_messages(
    prompts: dict[str, dict[str, Any]],
    prompt_name: str,
    arguments: dict[str, str],
) -> list[dict[str, Any]]:
    """Get messages for a specific prompt.

    Args:
        prompts: Prompt definitions dictionary
        prompt_name: Name of the prompt to retrieve
        arguments: Prompt arguments provided by the caller

    Returns:
        List of messages for the prompt

    Raises:
        ValueError: If prompt_name is not found

    """
    if prompt_name not in prompts:
        raise ValueError(f"Unknown prompt: {prompt_name}")

    if prompt_name == "security-scan":
        path = _sanitize_prompt_arg(arguments.get("path", "src/"))
        return [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        f"Run a comprehensive security audit on `{path}`. "
                        "Check for: eval/exec usage (CWE-95), path traversal (CWE-22), "
                        "hardcoded secrets, broad exception handling (BLE001), "
                        "and shell injection risks (B602). "
                        "Report findings in a severity-sorted table with file:line, CWE, "
                        "and recommended fix."
                    ),
                },
            },
        ]
    if prompt_name == "test-gen":
        module = _sanitize_prompt_arg(arguments.get("module", ""))
        batch = arguments.get("batch", "false").lower() == "true"
        if batch:
            return [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            "Generate behavioral tests in batch mode for all untested modules. "
                            "Use Given/When/Then structure, pytest fixtures, and target 80%+ coverage. "
                            "Run: `uv run attune workflow run test-gen-behavioral --batch`"
                        ),
                    },
                },
            ]
        return [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        f"Generate behavioral tests for `{module}`. "
                        "Use Given/When/Then structure, pytest fixtures, and test naming convention "
                        "`test_{{function}}_{{scenario}}_{{expected}}()`. "
                        f"Run: `uv run attune workflow run test-gen-behavioral --path {module}`"
                    ),
                },
            },
        ]
    if prompt_name == "cost-report":
        days = _sanitize_prompt_arg(arguments.get("days", "30"))
        return [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        f"Generate a cost optimization report for the last {days} days. "
                        "Show: total LLM spend by workflow, cache hit rates, "
                        "savings from tier routing (cheap vs capable vs premium), "
                        "and recommendations for further optimization. "
                        "Run: `uv run attune telemetry report`"
                    ),
                },
            },
        ]
    raise ValueError(f"Unknown prompt: {prompt_name}")
