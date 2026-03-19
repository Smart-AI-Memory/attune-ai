"""Test Audit Workflow.

Autonomous test coverage audit with Agent SDK subagents.
Three specialized subagents (coverage-auditor, gap-analyzer,
test-planner) analyze the codebase and synthesize findings
into a unified WorkflowResult.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import claude_agent_sdk

from ..agent_sdk_adapter import (
    AgentRunResult,
    AgentSDKResultAdapter,
    build_result_text,
    collect_agent_output,
    get_max_budget_usd,
    get_subagent_model,
)
from ..base import BaseWorkflow, ModelTier
from ..data_classes import CostReport, WorkflowResult, WorkflowStage

# Backward-compatibility re-exports — subpackage modules still exist.
from .coverage_parser import ModuleCoverage, parse_coverage_json  # noqa: F401
from .prompts import BATCH_TASK_TEMPLATE  # noqa: F401

logger = logging.getLogger(__name__)


_DEPTH_MAX_TURNS: dict[str, int] = {
    "quick": 10,
    "standard": 20,
    "deep": 40,
}

_SUBAGENT_NAMES = [
    "coverage-auditor",
    "gap-analyzer",
    "test-planner",
]

_SYSTEM_PROMPT = """\
You are a senior test audit orchestrator. Coordinate three specialized \
subagents to audit the test suite and synthesize their findings into a \
single structured report. Be thorough but concise. Cite file paths and \
line numbers when possible.\
"""

_TASK_PROMPT_TEMPLATE = """\
Audit the test suite for the codebase at {src_path} using the three \
specialized subagents below. Each subagent should focus on its domain \
and report findings as structured markdown.

After all subagents finish, synthesize their findings into a single \
report with these sections:

## Summary
Overall test health score (0-100) and a 2-3 sentence executive summary.

## Coverage
Findings from the coverage auditor including line, branch, and function \
coverage metrics.

## Test Gaps
Findings from the gap analyzer including untested code paths, missing \
edge cases, and untested error handling.

## Suggestions
Prioritized test plan from the test planner with estimated effort for \
each suggested test.\
"""


class TestAuditWorkflow(BaseWorkflow):
    """Autonomous test coverage audit with Agent SDK subagents.

    Delegates all analysis to three Agent SDK subagents rather
    than using the mixin stage system. Each subagent focuses on
    a specific audit domain (coverage, gaps, planning). The
    orchestrator synthesizes findings into a unified report.

    Usage::

        workflow = TestAuditWorkflow()
        result = await workflow.execute(src_path="src/", depth="standard")
    """

    name = "test-audit"
    description = "Autonomous test coverage audit with Agent SDK subagents"
    stages = ["agent-audit"]
    tier_map = {"agent-audit": ModelTier.CAPABLE}

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK test audit.

        Args:
            **kwargs: Keyword arguments.
                src_path (str): Required. Directory or file to audit.
                depth (str): Audit depth — "quick", "standard",
                    or "deep". Defaults to "standard".

        Returns:
            WorkflowResult with findings, suggestions, and metadata.
        """
        src_path_arg: str = kwargs.get("src_path", "")
        depth: str = kwargs.get("depth", "standard")

        if not src_path_arg:
            return self._error_result("src_path argument is required")

        resolved_path = str(Path(src_path_arg).resolve())
        max_turns = _DEPTH_MAX_TURNS.get(depth, 20)

        started_at = datetime.now()

        try:
            run_result = await self._run_agent_audit(resolved_path, max_turns, depth=depth)

            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                result_text=run_result.result_text,
                subagent_names=_SUBAGENT_NAMES,
                started_at=started_at,
                completed_at=completed_at,
                metadata={
                    "src_path": resolved_path,
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
            # a structured WorkflowResult rather than crashing.
            logger.exception("Agent SDK test audit failed: %s", type(exc).__name__)
            return self._error_result(f"Agent SDK error: {type(exc).__name__}: {exc}")

    async def _run_agent_audit(
        self, resolved_path: str, max_turns: int, depth: str = "standard"
    ) -> AgentRunResult:
        """Run the Agent SDK audit and return result text.

        Args:
            resolved_path: Absolute path to audit.
            max_turns: Maximum agent turns.
            depth: Agent depth for budget calculation.

        Returns:
            AgentRunResult with findings and SDK metadata.
        """
        assistant_parts: list[str] = []
        result_parts: list[str] = []
        run_result = AgentRunResult(result_text="No results returned.")
        async for message in claude_agent_sdk.query(
            prompt=_TASK_PROMPT_TEMPLATE.format(src_path=resolved_path),
            options=claude_agent_sdk.ClaudeAgentOptions(
                system_prompt=_SYSTEM_PROMPT,
                cwd=resolved_path,
                max_budget_usd=get_max_budget_usd(depth),
                allowed_tools=["Read", "Glob", "Grep", "Bash", "Agent"],
                permission_mode="default",
                max_turns=max_turns,
                agents={
                    "coverage-auditor": claude_agent_sdk.AgentDefinition(
                        description="Coverage auditor that analyzes test coverage metrics.",
                        prompt=(
                            "You are a test coverage auditor. Focus on: "
                            "running pytest --cov to collect coverage data, "
                            "analyzing line, branch, and function coverage, "
                            "identifying modules with low coverage, and "
                            "reporting coverage percentages per module. "
                            "Use Bash to run coverage commands when possible."
                        ),
                        tools=["Read", "Glob", "Grep", "Bash"],
                        model=get_subagent_model("coverage-auditor"),
                    ),
                    "gap-analyzer": claude_agent_sdk.AgentDefinition(
                        description="Gap analyzer that finds untested code paths.",
                        prompt=(
                            "You are a test gap analyzer. Focus on: "
                            "untested code paths, missing edge cases, "
                            "untested error handling branches, uncovered "
                            "exception handlers, and missing boundary "
                            "condition tests. Report each gap with file "
                            "path, line number, and risk assessment."
                        ),
                        tools=["Read", "Glob", "Grep"],
                        model=get_subagent_model("gap-analyzer"),
                    ),
                    "test-planner": claude_agent_sdk.AgentDefinition(
                        description="Test planner that creates prioritized test plans.",
                        prompt=(
                            "You are a test planner. Based on coverage "
                            "gaps and untested paths, create a prioritized "
                            "test plan. For each suggested test include: "
                            "test name, target file and function, test "
                            "type (unit/integration/e2e), estimated effort "
                            "(small/medium/large), and priority (high/"
                            "medium/low). Order by priority then effort."
                        ),
                        tools=["Read", "Glob", "Grep"],
                        model=get_subagent_model("test-planner"),
                    ),
                },
            ),
        ):
            sdk_result = collect_agent_output(message, assistant_parts, result_parts)
            if sdk_result is not None:
                run_result = sdk_result
        run_result.result_text = build_result_text(assistant_parts, result_parts)
        return run_result

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
                    name="agent-audit",
                    tier=ModelTier.CAPABLE,
                    description="Agent SDK test audit",
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
