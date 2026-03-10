"""Code review classification mixin.

Extracted from code_review.py for maintainability.

Contains:
    ClassifyMixin:
        _classify — CHEAP classification of change type, complexity, and risk

Expected host attributes (provided by BaseWorkflow / its mixins):
    _call_llm          : async method (from LLMMixin)
    core_modules       : list[str]
    file_threshold     : int
    enable_auth_strategy : bool
    _needs_architect_review : bool
    _auth_mode_used    : str | None
    _gather_project_context : method (from ArchitectMixin)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging

from .base import ModelTier

logger = logging.getLogger(__name__)


class ClassifyMixin:
    """Mixin providing the classification stage for code review."""

    async def _classify(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Classify the type of change."""
        diff = input_data.get("diff", "")
        target = input_data.get("target", "")
        files_changed = input_data.get("files_changed", [])

        # If target provided instead of diff, use it as the code to review
        code_to_review = diff or target

        # Handle project-level review when target is "." or empty
        if not code_to_review or code_to_review.strip() in (".", "", "./"):
            # Gather project context for project-level review
            project_context = self._gather_project_context()
            if not project_context:
                # Return early with helpful error message if no context found
                return (
                    {
                        "classification": "ERROR: No code provided for review",
                        "error": True,
                        "error_message": (
                            "No code was provided for review. Please ensure you:\n"
                            "1. Have a file open in the editor, OR\n"
                            "2. Select a specific file to review, OR\n"
                            '3. Provide code content directly via --input \'{"diff": "..."}\'\n\n'
                            "Tip: Use 'Select File...' option in the workflow picker."
                        ),
                        "change_type": "none",
                        "files_changed": [],
                        "file_count": 0,
                        "needs_architect_review": False,
                        "is_core_module": False,
                        "code_to_review": "",
                    },
                    0,
                    0,
                )
            code_to_review = project_context
            # Mark as project-level review
            input_data["is_project_review"] = True

        # === AUTH STRATEGY INTEGRATION ===
        if self.enable_auth_strategy:
            try:
                import logging
                from pathlib import Path

                from attune.models import (
                    count_lines_of_code,
                    get_auth_strategy,
                    get_module_size_category,
                )

                logger = logging.getLogger(__name__)

                # Calculate module size (for file) or total LOC (for directory)
                target_path = target or diff
                total_lines = 0
                if target_path:
                    target_obj = Path(target_path)
                    if target_obj.exists():
                        if target_obj.is_file():
                            total_lines = count_lines_of_code(target_obj)
                        elif target_obj.is_dir():
                            for py_file in target_obj.rglob("*.py"):
                                try:
                                    total_lines += count_lines_of_code(py_file)
                                except (OSError, UnicodeDecodeError):
                                    pass

                if total_lines > 0:
                    strategy = get_auth_strategy()
                    recommended_mode = strategy.get_recommended_mode(total_lines)
                    self._auth_mode_used = recommended_mode.value

                    size_category = get_module_size_category(total_lines)
                    logger.info(
                        "Code review target: %s (%s LOC, %s)",
                        target_path,
                        f"{total_lines:,}",
                        size_category,
                    )
                    logger.info("Recommended auth mode: %s", recommended_mode.value)

                    cost_estimate = strategy.estimate_cost(total_lines, recommended_mode)
                    if recommended_mode.value == "subscription":
                        logger.info("Cost: %s", cost_estimate["quota_cost"])
                    else:
                        logger.info("Cost: ~$%.4f", cost_estimate["monetary_cost"])

            except (AttributeError, ImportError, TypeError) as e:
                logger = logging.getLogger(__name__)
                logger.warning("Auth strategy detection failed: %s", e)

        system = """You are a code review classifier. Analyze the code and classify:
1. Change type: bug_fix, feature, refactor, docs, test, config, or security
2. Complexity: low, medium, high
3. Risk level: low, medium, high

Respond with a brief classification summary."""

        user_message = f"""Classify this code change:

Files: {", ".join(files_changed) if files_changed else "Not specified"}

Code:
{code_to_review[:4000]}"""

        response, input_tokens, output_tokens = await self._call_llm(
            tier,
            system,
            user_message,
            max_tokens=500,
        )

        # Parse response to determine if architect review needed
        is_high_complexity = "high" in response.lower() and (
            "complexity" in response.lower() or "risk" in response.lower()
        )
        is_core = (
            any(any(core in f for core in self.core_modules) for f in files_changed)
            if files_changed
            else False
        )

        self._needs_architect_review = (
            len(files_changed) >= self.file_threshold
            or is_core
            or is_high_complexity
            or input_data.get("is_core_module", False)
        )

        return (
            {
                "classification": response,
                "change_type": "feature",  # Will be refined by LLM
                "files_changed": files_changed,
                "file_count": len(files_changed),
                "needs_architect_review": self._needs_architect_review,
                "is_core_module": is_core,
                "code_to_review": code_to_review,
            },
            input_tokens,
            output_tokens,
        )
