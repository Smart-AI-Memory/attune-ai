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


class ArchitectMixin:
    """Mixin providing the architect review stage for code review."""

    def _gather_project_context(self) -> str:
        """Gather project context for project-level reviews.

        Reads project metadata and key files to provide context to the LLM.
        Returns formatted project context string, or empty string if no context found.
        """
        context_parts = []
        cwd = Path.cwd()

        # Get project name from directory or config files
        project_name = cwd.name
        context_parts.append(f"# Project: {project_name}")
        context_parts.append(f"# Path: {cwd}")
        context_parts.append("")

        # Check for pyproject.toml
        pyproject = cwd / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()[:2000]
                context_parts.append("## pyproject.toml")
                context_parts.append("```toml")
                context_parts.append(content)
                context_parts.append("```")
                context_parts.append("")
            except OSError:
                pass

        # Check for package.json
        package_json = cwd / "package.json"
        if package_json.exists():
            try:
                content = package_json.read_text()[:2000]
                context_parts.append("## package.json")
                context_parts.append("```json")
                context_parts.append(content)
                context_parts.append("```")
                context_parts.append("")
            except OSError:
                pass

        # Check for README
        for readme_name in ["README.md", "README.rst", "README.txt", "README"]:
            readme = cwd / readme_name
            if readme.exists():
                try:
                    content = readme.read_text()[:3000]
                    context_parts.append(f"## {readme_name}")
                    context_parts.append(content)
                    context_parts.append("")
                    break
                except OSError:
                    pass

        # Get directory structure (top 2 levels)
        context_parts.append("## Project Structure")
        context_parts.append("```")
        try:
            for root, dirs, files in os.walk(cwd):
                # Skip hidden and common ignored directories
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d
                    not in (
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
                    )
                ]
                level = root.replace(str(cwd), "").count(os.sep)
                if level < 2:
                    indent = "  " * level
                    folder_name = os.path.basename(root) or project_name
                    context_parts.append(f"{indent}{folder_name}/")
                    # Show key files at this level
                    key_files = [
                        f
                        for f in files
                        if f.endswith(
                            (".py", ".ts", ".js", ".json", ".yaml", ".yml", ".toml", ".md"),
                        )
                        and not f.startswith(".")
                    ][:10]
                    for f in key_files:
                        context_parts.append(f"{indent}  {f}")
                if level >= 2:
                    break
        except OSError:
            context_parts.append("(Unable to read directory structure)")
        context_parts.append("```")

        # Return empty if we only have the header
        if len(context_parts) <= 3:
            return ""

        return "\n".join(context_parts)

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
            except Exception:
                # Fall back to legacy _call_llm if executor fails
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
