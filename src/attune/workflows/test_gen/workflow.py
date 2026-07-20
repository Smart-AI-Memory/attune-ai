"""Test Generation Workflow — Agent SDK Native.

Delegates test generation to three specialized Claude Agent SDK
subagents (function-identifier, test-designer, test-writer) and
synthesizes their output into a unified WorkflowResult.

Prior to v4.2.0 this was a mixin-based multi-stage pipeline. The
SDK-native implementation replaces that with `claude_agent_sdk.query()`
and `AgentDefinition` subagents while preserving the same public
interface (`TestGenerationWorkflow`, `test-gen` slug) and
re-exports used by downstream code.

Copyright 2025-2026 Smart-AI-Memory
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
    iter_agent_messages,
    resolve_cwd_for_path,
    sdk_isolation_kwargs,
)
from ..base import BaseWorkflow, ModelTier
from ..data_classes import WorkflowResult
from .config import DEFAULT_SKIP_PATTERNS  # noqa: F401 — re-exported

logger = logging.getLogger(__name__)

# Depth → max agent turns mapping
_DEPTH_MAX_TURNS: dict[str, int] = {
    "quick": 10,
    "standard": 20,
    "deep": 40,
}

_SUBAGENT_NAMES = [
    "function-identifier",
    "test-designer",
    "test-writer",
]

_SYSTEM_PROMPT = """\
You are a test generation orchestrator. Coordinate three specialized \
subagents to analyze the codebase and synthesize their output into a \
single structured report. Be thorough but concise. Cite file paths and \
line numbers when possible.\
"""

_TASK_PROMPT_TEMPLATE = """\
Analyze the codebase at {path} using the three specialized subagents \
below. Each subagent should focus on its domain and produce structured \
markdown output.

After all subagents finish, synthesize their output into a single \
report with these sections:

## Summary
Overall test generation summary — how many functions were analyzed, \
how many test cases were designed, and how many test files were written.

## Coverage
Current coverage analysis and areas that need testing.

## Test Gaps
Functions and modules that lack adequate test coverage.

## Suggestions
Actionable next steps for improving test coverage, ordered by priority.\
"""


class TestGenerationWorkflow(BaseWorkflow):
    """SDK-native test generation with three specialized subagents.

    Delegates all analysis to Claude Agent SDK subagents:
    - **function-identifier** — scans the codebase for untested or
      under-tested functions, prioritising public API and complex logic
    - **test-designer** — designs comprehensive test cases covering
      happy paths, edge cases, and error handling
    - **test-writer** — writes pytest code following project conventions

    The orchestrator synthesizes findings into a unified report.

    Usage::

        workflow = TestGenerationWorkflow()
        result = await workflow.execute(path="src/", depth="standard")
    """

    name = "test-gen"
    description = "Agent SDK-powered test generation with 3 specialized subagents"
    stages = ["agent-gen"]
    tier_map = {"agent-gen": ModelTier.CAPABLE}

    def __init__(self, **kwargs: Any) -> None:
        """Initialize workflow.

        Args:
            **kwargs: Passed to BaseWorkflow.__init__().
        """
        super().__init__(**kwargs)

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK test generation.

        Args:
            **kwargs: Keyword arguments.
                path (str): Required. Directory or file to generate
                    tests for.
                depth (str): Generation depth — "quick", "standard",
                    or "deep". Defaults to "standard".

        Returns:
            WorkflowResult with generated tests, coverage info,
            and metadata.
        """
        path_arg: str = kwargs.get("path", "")
        depth: str = kwargs.get("depth", "standard")

        if not path_arg:
            return self._error_result("path argument is required")

        resolved_path = str(Path(path_arg).resolve())
        max_turns = _DEPTH_MAX_TURNS.get(depth, 20)

        started_at = datetime.now()

        try:
            run_result = await self._run_agent_gen(resolved_path, max_turns, depth=depth)
            self._track_sdk_run_telemetry(stage="agent", agent_run_result=run_result)
            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                report_title="Test generation",
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
            # INTENTIONAL: Catch-all for unknown SDK errors to
            # return a structured WorkflowResult rather than
            # crashing the CLI.
            logger.exception(
                "Agent SDK test generation failed: %s",
                type(exc).__name__,
            )
            return self._error_result(f"Agent SDK error: {type(exc).__name__}: {exc}")

    async def _run_agent_gen(
        self, resolved_path: str, max_turns: int, depth: str = "standard"
    ) -> AgentRunResult:
        """Run the Agent SDK test generation and return result text.

        Args:
            resolved_path: Absolute path to generate tests for.
            max_turns: Maximum agent turns.
            depth: Agent depth for budget calculation.

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
                        "function-identifier": claude_agent_sdk.AgentDefinition(
                            description="Identifies untested or under-tested functions.",
                            prompt=(
                                "You are a function identifier. Scan the "
                                "codebase and identify functions that are "
                                "untested or under-tested. For each function, "
                                "report: file path, function name, signature, "
                                "current test coverage status, and complexity "
                                "level. Prioritize public API functions and "
                                "functions with complex logic."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("function-identifier"),
                        ),
                        "test-designer": claude_agent_sdk.AgentDefinition(
                            description="Designs test cases for identified functions.",
                            prompt=(
                                "You are a test designer. For each function "
                                "identified by the function-identifier, design "
                                "comprehensive test cases covering: happy path "
                                "scenarios, edge cases (empty input, boundary "
                                "values, None/null), error handling paths, and "
                                "integration points. Report each test case with "
                                "a descriptive name, input values, and expected "
                                "outcome."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("test-designer"),
                        ),
                        "test-writer": claude_agent_sdk.AgentDefinition(
                            description="Writes pytest test code following project conventions.",
                            prompt=(
                                "You are a test writer. Using the test cases "
                                "designed by the test-designer, write pytest "
                                "test code that follows project conventions: "
                                "use pytest fixtures, parametrize where "
                                "appropriate, include type hints, add "
                                "docstrings, and follow the naming convention "
                                "test_{function}_{scenario}_{expected}. Group "
                                "related tests in classes."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("test-writer"),
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


def main() -> None:
    """CLI entry point for test generation workflow."""
    import asyncio

    async def run() -> None:
        """Run test generation workflow and print results."""
        workflow = TestGenerationWorkflow()
        result = await workflow.execute(path=".", depth="standard")

        print("\nTest Generation Results")
        print("=" * 50)
        print(f"Provider: {result.provider}")
        print(f"Success: {result.success}")
        if result.final_output:
            print(f"\nOutput:\n{result.final_output}")
        print("\nCost Report:")
        print(f"  Total Cost: ${result.cost_report.total_cost:.4f}")
        savings = result.cost_report.savings
        pct = result.cost_report.savings_percent
        print(f"  Savings: ${savings:.4f} ({pct:.1f}%)")

    asyncio.run(run())
