"""Agent SDK Refactor Plan Workflow.

Delegates a full refactoring plan to the Claude Agent SDK, using three
specialized subagents (debt-scanner, impact-analyzer, plan-generator)
and synthesizing their findings into a unified WorkflowResult.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import claude_agent_sdk

from .agent_sdk_adapter import AgentSDKResultAdapter
from .base import BaseWorkflow, ModelTier
from .data_classes import CostReport, WorkflowResult, WorkflowStage

logger = logging.getLogger(__name__)


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

_MAIN_PROMPT_TEMPLATE = """\
You are a senior refactoring plan orchestrator. Analyze the codebase at {path} \
using the three specialized subagents below. Each subagent should focus on \
its domain and report findings as structured markdown.

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
longer-term improvements.

Be thorough but concise. Cite file paths and line numbers when possible.\
"""


class RefactorPlanAgentSDKWorkflow(BaseWorkflow):
    """Refactoring plan workflow powered by the Claude Agent SDK.

    Delegates all analysis to three Agent SDK subagents rather
    than using the mixin stage system. Each subagent focuses on
    a specific refactoring domain (debt scanning, impact analysis,
    plan generation). The orchestrator synthesizes findings into a
    unified report.

    Usage::

        workflow = RefactorPlanAgentSDKWorkflow()
        result = await workflow.execute(path="src/", depth="standard")
    """

    name = "refactor-plan-sdk"
    description = "Agent SDK-powered refactoring plan with 3 specialized subagents"
    stages = ["agent-plan"]
    tier_map = {"agent-plan": ModelTier.CAPABLE}

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
        path_arg: str = kwargs.get("path", "")
        depth: str = kwargs.get("depth", "standard")

        if not path_arg:
            return self._error_result("path argument is required")

        resolved_path = str(Path(path_arg).resolve())
        max_turns = _DEPTH_MAX_TURNS.get(depth, 20)

        started_at = datetime.now()

        try:
            result_text = await self._run_agent_plan(resolved_path, max_turns)

            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                result_text=result_text,
                subagent_names=_SUBAGENT_NAMES,
                started_at=started_at,
                completed_at=completed_at,
                metadata={
                    "path": resolved_path,
                    "depth": depth,
                    "max_turns": max_turns,
                },
            )

        except ImportError as exc:
            logger.error("Agent SDK import failed: %s", exc)
            return self._error_result(f"Agent SDK unavailable: {exc}")
        except (ConnectionError, TimeoutError) as exc:
            logger.error("Agent SDK network error: %s", exc)
            return self._error_result(f"Agent SDK connection failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            # INTENTIONAL: Catch-all for unknown SDK errors to return
            # a structured WorkflowResult rather than crashing.
            logger.exception("Agent SDK refactor plan failed: %s", type(exc).__name__)
            return self._error_result(f"Agent SDK error: {type(exc).__name__}: {exc}")

    async def _run_agent_plan(self, resolved_path: str, max_turns: int) -> str:
        """Run the Agent SDK refactoring plan and return result text.

        Args:
            resolved_path: Absolute path to analyze.
            max_turns: Maximum agent turns.

        Returns:
            The agent's final result text.
        """
        result_parts: list[str] = []
        async for message in claude_agent_sdk.query(
            prompt=_MAIN_PROMPT_TEMPLATE.format(path=resolved_path),
            options=claude_agent_sdk.ClaudeAgentOptions(
                cwd=resolved_path,
                allowed_tools=["Read", "Glob", "Grep", "Agent"],
                permission_mode="default",
                max_turns=max_turns,
                agents={
                    "debt-scanner": claude_agent_sdk.AgentDefinition(
                        description="Tech debt scanner that finds code smells and duplication.",
                        prompt=(
                            "You are a tech debt scanner. Focus on: "
                            "code smells, duplication, complex conditionals, "
                            "dead code, overly long functions, and deeply "
                            "nested logic. Report each finding with file "
                            "path, line number, severity, and a brief "
                            "description of the issue."
                        ),
                        tools=["Read", "Glob", "Grep"],
                    ),
                    "impact-analyzer": claude_agent_sdk.AgentDefinition(
                        description="Impact analyzer for refactoring risk assessment.",
                        prompt=(
                            "You are a refactoring impact analyzer. Focus on: "
                            "test coverage of affected code, dependency chains, "
                            "API surface changes, and downstream consumers. "
                            "For each refactoring candidate, report the impact "
                            "on tests, dependencies, and public interfaces."
                        ),
                        tools=["Read", "Glob", "Grep"],
                    ),
                    "plan-generator": claude_agent_sdk.AgentDefinition(
                        description="Plan generator that creates prioritized refactoring plans.",
                        prompt=(
                            "You are a refactoring plan generator. Using "
                            "findings from the debt scanner and impact "
                            "analyzer, create a prioritized refactoring plan. "
                            "For each item include: effort estimate "
                            "(small/medium/large), risk level (low/medium/high), "
                            "expected benefit, and suggested implementation order."
                        ),
                        tools=["Read", "Glob", "Grep"],
                    ),
                },
            ),
        ):
            if isinstance(message, claude_agent_sdk.ResultMessage):
                result_parts.append(message.result)

        return "\n".join(result_parts) if result_parts else "No results returned."

    def _error_result(self, message: str) -> WorkflowResult:
        """Build a failed WorkflowResult with the given error message.

        Args:
            message: Human-readable error description.

        Returns:
            WorkflowResult with success=False.
        """
        now = datetime.now()
        return WorkflowResult(
            success=False,
            stages=[
                WorkflowStage(
                    name="agent-plan",
                    tier=ModelTier.CAPABLE,
                    description="Agent SDK refactor plan",
                ),
            ],
            final_output=None,
            cost_report=CostReport(
                total_cost=0.0,
                baseline_cost=0.0,
                savings=0.0,
                savings_percent=0.0,
            ),
            started_at=now,
            completed_at=now,
            total_duration_ms=0,
            provider="anthropic",
            error=message,
        )
