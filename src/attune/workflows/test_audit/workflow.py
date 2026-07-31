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
    SdkSubprocessError,
    _last_subprocess_argv,
    build_result_text,
    capture_subprocess_failure,
    classify_subprocess_failure,
    collect_agent_output,
    get_max_budget_usd,
    get_subagent_model,
    iter_agent_messages,
    resolve_cwd_for_path,
    sdk_isolation_kwargs,
)
from ..base import BaseWorkflow, ModelTier
from ..data_classes import WorkflowResult
from ..validation import InputSchema

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
        result = await workflow.execute(path="src/", depth="standard")
    """

    name = "test-audit"
    description = "Autonomous test coverage audit with Agent SDK subagents"
    stages = ["agent-audit"]
    tier_map = {"agent-audit": ModelTier.CAPABLE}

    def __init__(self, *, system_prompt_suffix: str = "", **kwargs: Any) -> None:
        """Initialize workflow.

        Args:
            system_prompt_suffix: Optional string appended to the
                orchestrator's system prompt at call time. Lets a
                wrapping caller (e.g. discovery-sweep's
                ``TestAuditSource``) augment the prompt at the
                workflow-INSTANCE level without mutating the class
                template. Empty string (default) preserves prior
                behavior for every other caller.
            **kwargs: Passed to BaseWorkflow.__init__().
        """
        super().__init__(**kwargs)
        self._system_prompt_suffix = system_prompt_suffix

    input_schema = InputSchema(
        optional_fields={
            "path": str,
            "depth": str,
            "max_budget_usd": (int, float),
            "src_path": str,
        },
    )

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK test audit.

        Args:
            **kwargs: Keyword arguments.
                path (str): Required. Directory or file to audit.
                src_path (str): Deprecated alias for ``path``;
                    emits ``DeprecationWarning``. Removed in v7.0.
                depth (str): Audit depth — "quick", "standard",
                    or "deep". Defaults to "standard".

        Returns:
            WorkflowResult with findings, suggestions, and metadata.
        """
        self.validate_input(kwargs)
        import warnings as _warnings  # local to keep formatter from stripping

        path_arg: str = kwargs.get("path", "") or kwargs.get("src_path", "")
        depth: str = kwargs.get("depth", "standard")

        legacy_set = bool(kwargs.get("src_path"))
        new_set = bool(kwargs.get("path"))
        if legacy_set and not new_set:
            _warnings.warn(
                "TestAuditWorkflow.execute(src_path=...) is deprecated; "
                "use execute(path=...) instead. The legacy kwarg will "
                "be removed in v7.0.",
                DeprecationWarning,
                stacklevel=2,
            )
        elif legacy_set and new_set:
            _warnings.warn(
                "TestAuditWorkflow.execute(): both `path=` and "
                "`src_path=` supplied; `path=` takes precedence and "
                "`src_path=` is deprecated.",
                DeprecationWarning,
                stacklevel=2,
            )

        if not path_arg:
            return self._error_result("path argument is required (was: src_path)")

        resolved_path = str(Path(path_arg).resolve())
        max_turns = _DEPTH_MAX_TURNS.get(depth, 20)
        # Optional explicit per-call USD cap (discovery-sweep plumbs each
        # source's allocation down here; budget-enforcement spec FR-1).
        # None → today's depth-derived cap, no behavior change.
        max_budget_usd: float | None = kwargs.get("max_budget_usd")

        started_at = datetime.now()

        try:
            run_result = await self._run_agent_audit(
                resolved_path, max_turns, depth=depth, max_budget_usd=max_budget_usd
            )
            self._track_sdk_run_telemetry(stage="agent", agent_run_result=run_result)

            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                report_title="Test audit",
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
            # a structured WorkflowResult rather than crashing. Phase 6
            # of docs/specs/sdk-error-message-fidelity/.
            logger.exception("Agent SDK test audit failed: %s", type(exc).__name__)
            stderr = capture_subprocess_failure(_last_subprocess_argv(exc))
            kind, summary = classify_subprocess_failure(stderr)
            sdk_err = SdkSubprocessError(
                message=summary, stderr=stderr, kind=kind, original_exc=exc
            )
            return self._error_result(
                sdk_err.format_user_message(),
                sdk_stderr=stderr,
                sdk_error_kind=kind,
            )

    async def _run_agent_audit(
        self,
        resolved_path: str,
        max_turns: int,
        depth: str = "standard",
        max_budget_usd: float | None = None,
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
        system_prompt = _SYSTEM_PROMPT + (self._system_prompt_suffix or "")
        async for message in iter_agent_messages(
            claude_agent_sdk.query(
                prompt=_TASK_PROMPT_TEMPLATE.format(src_path=resolved_path),
                options=claude_agent_sdk.ClaudeAgentOptions(
                    **sdk_isolation_kwargs(),
                    system_prompt=system_prompt,
                    cwd=resolve_cwd_for_path(resolved_path),
                    max_budget_usd=get_max_budget_usd(depth, explicit=max_budget_usd),
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
            )
        ):
            sdk_result = collect_agent_output(message, assistant_parts, result_parts)
            if sdk_result is not None:
                run_result = sdk_result
        run_result.result_text = build_result_text(assistant_parts, result_parts)
        return run_result
