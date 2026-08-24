"""Refactor Planning Workflow

Prioritizes tech debt with Agent SDK subagents.

Stages:
1. agent-plan (CAPABLE) - Three specialized subagents scan, analyze,
   and generate a prioritized refactoring roadmap.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import claude_agent_sdk

from .agent_sdk_adapter import (
    AgentRunResult,
    AgentSDKResultAdapter,
    build_result_text,
    collect_agent_output,
    get_max_budget_usd,
    get_subagent_model,
    iter_agent_messages,
    resolve_cwd_for_path,
    sdk_error_from_exception,
    sdk_isolation_kwargs,
)
from .base import BaseWorkflow, ModelTier
from .data_classes import WorkflowResult
from .refactor_plan_report import (
    format_refactor_plan_report,  # noqa: F401 - re-exported
    main,  # noqa: F401 - re-exported
)
from .step_config import WorkflowStepConfig
from .validation import InputSchema

logger = logging.getLogger(__name__)

# Define step configurations for executor-based execution
REFACTOR_PLAN_STEPS = {
    "plan": WorkflowStepConfig(
        name="plan",
        task_type="architectural_decision",  # Premium tier task
        tier_hint="premium",
        description="Generate prioritized refactoring roadmap",
        max_tokens=3000,
    ),
}

# Debt markers and their severity
DEBT_MARKERS = {
    "TODO": {"severity": "low", "weight": 1},
    "FIXME": {"severity": "medium", "weight": 3},
    "HACK": {"severity": "high", "weight": 5},
    "XXX": {"severity": "medium", "weight": 3},
    "BUG": {"severity": "high", "weight": 5},
    "OPTIMIZE": {"severity": "low", "weight": 2},
    "REFACTOR": {"severity": "medium", "weight": 3},
}

_DEPTH_MAX_TURNS: dict[str, int] = {
    "quick": 10,
    "standard": 20,
    "deep": 40,
}

_SUBAGENT_NAMES = [
    "debt-scanner",
    "impact-analyzer",
    "plan-generator",
]

_SYSTEM_PROMPT = """\
You are a senior refactoring plan orchestrator. You coordinate three \
specialized subagents to produce a unified refactoring roadmap. \
Be thorough but concise. Cite file paths and line numbers when possible.\
"""

_TASK_PROMPT_TEMPLATE = """\
Analyze the codebase at {path} using the three specialized subagents \
below. Each subagent should focus on its domain and report findings \
as structured markdown.

After all subagents finish, synthesize their findings into a single \
report with these sections:

## Summary
Overall tech debt score (0-100) and a 2-3 sentence executive summary of \
the refactoring opportunities found.

## Refactoring
Prioritized list of refactoring opportunities with effort estimates \
(small/medium/large) and risk levels (low/medium/high) for each item.

## Suggestions
Actionable next steps ordered by priority, including quick wins and \
longer-term improvements.\
"""


class RefactorPlanWorkflow(BaseWorkflow):
    """Prioritize tech debt with Agent SDK subagents.

    Delegates all analysis to three Agent SDK subagents rather
    than using the mixin stage system. Each subagent focuses on
    a specific refactoring domain (debt scanning, impact analysis,
    plan generation). The orchestrator synthesizes findings into a
    unified report.

    Usage::

        workflow = RefactorPlanWorkflow()
        result = await workflow.execute(path="src/", depth="standard")
    """

    name = "refactor-plan"
    description = "Prioritize tech debt with Agent SDK subagents"
    stages = ["agent-plan"]
    tier_map = {"agent-plan": ModelTier.CAPABLE}

    def __init__(self, **kwargs: Any) -> None:
        """Initialize refactor planning workflow.

        Args:
            **kwargs: Additional arguments passed to BaseWorkflow.

        """
        kwargs.setdefault("enable_post_simplification", True)
        super().__init__(**kwargs)

    input_schema = InputSchema(
        optional_fields={"path": str, "depth": str},
    )

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK refactoring plan.

        Args:
            **kwargs: Keyword arguments.
                path (str): Required. Directory or file to analyze.
                depth (str): Analysis depth — "quick", "standard",
                    or "deep". Defaults to "standard".

        Returns:
            WorkflowResult with findings, suggestions, and metadata.
        """
        self.validate_input(kwargs)
        path_arg: str = kwargs.get("path", "")
        depth: str = kwargs.get("depth", "standard")

        if not path_arg:
            return self._error_result("path argument is required")

        resolved_path = str(Path(path_arg).resolve())
        max_turns = _DEPTH_MAX_TURNS.get(depth, 20)

        started_at = datetime.now()

        try:
            run_result = await self._run_agent_plan(resolved_path, max_turns, depth)
            self._track_sdk_run_telemetry(stage="agent", agent_run_result=run_result)

            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                report_title="Refactor plan",
                result_text=run_result.result_text,
                subagent_names=_SUBAGENT_NAMES,
                started_at=started_at,
                completed_at=completed_at,
                metadata={
                    "path": resolved_path,
                    "depth": depth,
                    "max_turns": max_turns,
                },
                agent_run_result=run_result,
            )

        except ImportError as exc:
            logger.error("Agent SDK import failed: %s", exc)
            return self._error_result(f"Agent SDK unavailable: {exc}")
        except (ConnectionError, TimeoutError) as exc:
            logger.error("Agent SDK network error: %s", exc)
            return self._error_result(f"Agent SDK connection failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            # INTENTIONAL: Catch-all for unknown SDK errors to return
            # a structured WorkflowResult rather than crashing. Phase 4
            # of docs/specs/sdk-error-message-fidelity/ — capture +
            # classify the real claude CLI stderr instead of showing
            # the legacy three-cause menu.
            logger.exception("Agent SDK refactor plan failed: %s", type(exc).__name__)
            sdk_err = sdk_error_from_exception(exc)
            return self._error_result(
                sdk_err.format_user_message(),
                sdk_stderr=sdk_err.stderr,
                sdk_error_kind=sdk_err.kind,
            )

    async def _run_agent_plan(
        self, resolved_path: str, max_turns: int, depth: str = "standard"
    ) -> AgentRunResult:
        """Run the Agent SDK refactoring plan and return result text.

        Args:
            resolved_path: Absolute path to analyze.
            max_turns: Maximum agent turns.

        Returns:
            AgentRunResult with findings and SDK metadata.
        """
        assistant_parts: list[str] = []
        result_parts: list[str] = []
        run_result = AgentRunResult(result_text="No results returned.")
        async for message in iter_agent_messages(
            claude_agent_sdk.query(
                prompt=_TASK_PROMPT_TEMPLATE.format(path=resolved_path),
                options=claude_agent_sdk.ClaudeAgentOptions(
                    **sdk_isolation_kwargs(),
                    system_prompt=_SYSTEM_PROMPT,
                    cwd=resolve_cwd_for_path(resolved_path),
                    max_budget_usd=get_max_budget_usd(depth),
                    allowed_tools=["Read", "Glob", "Grep", "Agent"],
                    permission_mode="default",
                    max_turns=max_turns,
                    agents={
                        "debt-scanner": claude_agent_sdk.AgentDefinition(
                            description=(
                                "Tech debt scanner that finds code smells" " and duplication."
                            ),
                            prompt=(
                                "You are a tech debt scanner. Focus on: "
                                "code smells, duplication, complex conditionals, "
                                "dead code, overly long functions, and deeply "
                                "nested logic. Report each finding with file "
                                "path, line number, severity, and a brief "
                                "description of the issue."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("debt-scanner"),
                        ),
                        "impact-analyzer": claude_agent_sdk.AgentDefinition(
                            description=("Impact analyzer for refactoring risk assessment."),
                            prompt=(
                                "You are a refactoring impact analyzer. Focus on: "
                                "test coverage of affected code, dependency chains, "
                                "API surface changes, and downstream consumers. "
                                "For each refactoring candidate, report the impact "
                                "on tests, dependencies, and public interfaces."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("impact-analyzer"),
                        ),
                        "plan-generator": claude_agent_sdk.AgentDefinition(
                            description=(
                                "Plan generator that creates prioritized" " refactoring plans."
                            ),
                            prompt=(
                                "You are a refactoring plan generator. Using "
                                "findings from the debt scanner and impact "
                                "analyzer, create a prioritized refactoring plan. "
                                "For each item include: effort estimate "
                                "(small/medium/large), risk level (low/medium/high), "
                                "expected benefit, and suggested implementation order."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("plan-generator"),
                        ),
                    },
                ),
            )
        ):
            sdk_result = collect_agent_output(message, assistant_parts, result_parts)
            if sdk_result is not None:
                run_result = sdk_result
        run_result.result_text = build_result_text(assistant_parts, result_parts)
        return run_result
