"""Code review architect review mixin.

Extracted from code_review.py for maintainability.

Contains:
    ArchitectMixin:
        _architect_review      — PREMIUM deep architectural review
        _gather_project_context — gather project metadata for project-level reviews

Expected host attributes (provided by BaseWorkflow / its mixins):
    _call_llm              : async method (from LLMMixin)
    _is_xml_enabled        : method (from PromptMixin)
    _render_xml_prompt     : method (from PromptMixin)
    _parse_xml_response    : method (from ParsingMixin)
    _executor              : optional executor (from ExecutorMixin)
    _api_key               : optional API key (from BaseWorkflow)
    run_step_with_executor : async method (from ExecutorMixin)
    _auth_mode_used        : str | None

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .base import ModelTier
from .code_review_report import format_code_review_report

logger = logging.getLogger(__name__)


_EXCLUDED_DIRS = frozenset(
    {
        "node_modules",
        "__pycache__",
        "venv",
        ".venv",
        "dist",
        "build",
        ".git",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
        "htmlcov",
    }
)

_KEY_EXTENSIONS = (".py", ".ts", ".js", ".json", ".yaml", ".yml", ".toml", ".md")


def _read_file_snippet(path: Path, max_chars: int) -> str:
    """Read file content up to *max_chars*, empty string on error.

    Args:
        path: File to read.
        max_chars: Maximum characters to return.

    Returns:
        File content truncated to *max_chars*, or ``""`` on I/O error.
    """
    try:
        return path.read_text(encoding="utf-8")[:max_chars]
    except OSError:
        return ""


def _build_directory_tree(root_dir: Path, max_depth: int = 2) -> str:
    """Build a text representation of the directory tree.

    Args:
        root_dir: Directory to walk.
        max_depth: Maximum depth to descend (default 2).

    Returns:
        Indented tree string, or error placeholder.
    """
    project_name = root_dir.name
    lines: list[str] = []
    try:
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in _EXCLUDED_DIRS]
            level = root.replace(str(root_dir), "").count(os.sep)
            if level >= max_depth:
                break
            indent = "  " * level
            folder_name = os.path.basename(root) or project_name
            lines.append(f"{indent}{folder_name}/")
            key_files = [f for f in files if f.endswith(_KEY_EXTENSIONS) and not f.startswith(".")][
                :10
            ]
            for f in key_files:
                lines.append(f"{indent}  {f}")
    except OSError:
        lines.append("(Unable to read directory structure)")
    return "\n".join(lines)


class ArchitectMixin:
    """Mixin providing the architect review stage for code review."""

    def _gather_project_context(self) -> str:
        """Gather project context for project-level reviews.

        Reads project metadata and key files to provide context to the LLM.
        Returns formatted project context string, or empty string if no
        context found.
        """
        parts: list[str] = []
        cwd = Path.cwd()
        project_name = cwd.name

        parts.append(f"# Project: {project_name}")
        parts.append(f"# Path: {cwd}")
        parts.append("")

        # Project metadata files
        for filename, heading, lang, limit in [
            ("pyproject.toml", "pyproject.toml", "toml", 2000),
            ("package.json", "package.json", "json", 2000),
        ]:
            content = _read_file_snippet(cwd / filename, limit)
            if content:
                parts.extend([f"## {heading}", f"```{lang}", content, "```", ""])

        # README (first match wins)
        for readme_name in ["README.md", "README.rst", "README.txt", "README"]:
            content = _read_file_snippet(cwd / readme_name, 3000)
            if content:
                parts.extend([f"## {readme_name}", content, ""])
                break

        # Directory tree
        tree = _build_directory_tree(cwd)
        parts.extend(["## Project Structure", "```", tree, "```"])

        # Return empty if we only have the header
        if len(parts) <= 3:
            return ""

        return "\n".join(parts)

    async def _architect_review(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Deep architectural review.

        Supports XML-enhanced prompts when enabled in workflow config.
        """
        # Import step config here to avoid circular imports at module level
        from .step_config import WorkflowStepConfig

        code_to_review = input_data.get("code_to_review", "")
        scan_results = input_data.get("scan_results", "")
        classification = input_data.get("classification", "")

        # Build input payload
        input_payload = f"""Classification: {classification}

Security Scan Results:
{scan_results[:2000]}

Code:
{code_to_review[:4000]}"""

        # Check if XML prompts are enabled
        if self._is_xml_enabled():
            from attune.prompts.examples import CODE_REVIEW_EXAMPLES

            user_message = self._render_xml_prompt(
                role="senior software architect",
                goal="Perform comprehensive code review with architectural assessment",
                instructions=[
                    "Assess design patterns used (or missing)",
                    "Evaluate SOLID principles compliance",
                    "Check separation of concerns",
                    "Analyze coupling and cohesion",
                    "Provide specific improvement recommendations with examples",
                    "Suggest refactoring and testing improvements",
                    "Provide verdict: approve, approve_with_suggestions, or reject",
                ],
                constraints=[
                    "Be specific and actionable",
                    "Reference file locations where possible",
                    "Prioritize issues by impact",
                ],
                input_type="code",
                input_payload=input_payload,
                examples=CODE_REVIEW_EXAMPLES,
            )
            system = None
        else:
            system = """You are a senior software architect. Provide a comprehensive review:

1. ARCHITECTURAL ASSESSMENT:
   - Design patterns used (or missing)
   - SOLID principles compliance
   - Separation of concerns
   - Coupling and cohesion

2. RECOMMENDATIONS:
   - Specific improvements with examples
   - Refactoring suggestions
   - Testing recommendations

3. VERDICT:
   - APPROVE: Code is production-ready
   - APPROVE_WITH_SUGGESTIONS: Minor improvements recommended
   - REQUEST_CHANGES: Issues must be addressed
   - REJECT: Fundamental problems

Provide actionable, specific feedback."""

            user_message = f"""Perform an architectural review:

{input_payload}"""

        # Try executor-based execution first (Phase 3 pattern)
        if self._executor is not None or self._api_key:
            try:
                step = WorkflowStepConfig(
                    name="architect_review",
                    task_type="architectural_decision",  # Premium tier task
                    tier_hint="premium",
                    description="Comprehensive architectural code review",
                    max_tokens=3000,
                )
                response, input_tokens, output_tokens, cost = await self.run_step_with_executor(
                    step=step,
                    prompt=user_message,
                    system=system,
                )
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Fall back to legacy _call_llm if executor fails
                response, input_tokens, output_tokens = await self._call_llm(
                    tier,
                    system or "",
                    user_message,
                    max_tokens=3000,
                )
        else:
            # Legacy path for backward compatibility
            response, input_tokens, output_tokens = await self._call_llm(
                tier,
                system or "",
                user_message,
                max_tokens=3000,
            )

        # Parse XML response if enforcement is enabled
        parsed_data = self._parse_xml_response(response)

        # Determine verdict from response or parsed data
        verdict = "approve_with_suggestions"
        if parsed_data.get("xml_parsed"):
            extra = parsed_data.get("_parsed_response")
            if extra and hasattr(extra, "extra"):
                parsed_verdict = extra.extra.get("verdict", "").lower()
                if parsed_verdict in [
                    "approve",
                    "approve_with_suggestions",
                    "request_changes",
                    "reject",
                ]:
                    verdict = parsed_verdict

        if verdict == "approve_with_suggestions":
            # Fall back to text parsing
            if "REQUEST_CHANGES" in response.upper() or "REJECT" in response.upper():
                verdict = "request_changes"
            elif "APPROVE" in response.upper() and "SUGGESTIONS" not in response.upper():
                verdict = "approve"

        result: dict = {
            "architectural_review": response,
            "verdict": verdict,
            "recommendations": [],
            "model_tier_used": tier.value,
            "auth_mode_used": self._auth_mode_used,
        }

        # Merge parsed XML data if available
        if parsed_data.get("xml_parsed"):
            result.update(
                {
                    "xml_parsed": True,
                    "summary": parsed_data.get("summary"),
                    "findings": parsed_data.get("findings", []),
                    "checklist": parsed_data.get("checklist", []),
                },
            )

        # Add formatted report for human readability
        formatted_report = format_code_review_report(result, input_data)
        result["formatted_report"] = formatted_report

        # Also add as top-level display_output for better UX
        result["display_output"] = formatted_report

        return (result, input_tokens, output_tokens)
