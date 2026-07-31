"""Performance Audit Workflow — Agent SDK Native.

Delegates performance auditing to three specialized Claude Agent SDK
subagents (complexity-analyzer, bottleneck-finder, optimization-advisor)
and synthesizes their findings into a unified WorkflowResult.

Prior to v4.2.0 this was a mixin-based multi-stage pipeline. The
SDK-native implementation replaces that with `claude_agent_sdk.query()`
and `AgentDefinition` subagents while preserving the same public
interface (`PerformanceAuditWorkflow`, `perf-audit` slug) and
re-exports used by downstream code.

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import claude_agent_sdk

from .agent_sdk_adapter import (
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
from .base import BaseWorkflow, ModelTier
from .data_classes import WorkflowResult
from .validation import InputSchema

logger = logging.getLogger(__name__)

__all__ = [
    "PerformanceAuditWorkflow",
]

# Depth → max agent turns mapping
_DEPTH_MAX_TURNS: dict[str, int] = {
    "quick": 10,
    "standard": 20,
    "deep": 40,
}

_SUBAGENT_NAMES = [
    "complexity-analyzer",
    "bottleneck-finder",
    "optimization-advisor",
]

_SYSTEM_PROMPT = """\
You are a senior performance audit orchestrator. You coordinate three \
specialized subagents to produce a unified performance audit report. \
Be thorough but concise. Cite file paths and line numbers when possible.\
"""

_TASK_PROMPT_TEMPLATE = """\
Audit the codebase at {path} using the three specialized subagents \
below. Each subagent should focus on its domain and report findings \
as structured markdown.

After all subagents finish, synthesize their findings into a single \
report with these sections:

## Summary
Overall performance health score (0-100) and a 2-3 sentence executive \
summary.

## Performance
Key performance findings across the codebase.

## Complexity
Findings from the complexity analyzer — cyclomatic complexity, nesting \
depth, and oversized functions.

## Optimization
Findings from the bottleneck finder and optimization advisor — N+1 \
patterns, unnecessary list copies, blocking I/O, missing caching, and \
prioritized suggestions with estimated impact.

## Suggestions
Actionable next steps ordered by estimated performance impact.\
"""


class PerformanceAuditWorkflow(BaseWorkflow):
    """SDK-native performance audit with three specialized subagents.

    Delegates all analysis to Claude Agent SDK subagents:
    - **complexity-analyzer** — cyclomatic complexity, nesting depth,
      oversized functions
    - **bottleneck-finder** — N+1 patterns, list copies, blocking I/O,
      missing caching
    - **optimization-advisor** — prioritized fixes with effort estimates

    The orchestrator synthesizes findings into a unified report.

    Usage::

        workflow = PerformanceAuditWorkflow()
        result = await workflow.execute(path="src/", depth="standard")
    """

    name = "perf-audit"
    description = "Agent SDK-powered performance audit with 3 specialized " "subagents"
    stages = ["agent-audit"]
    tier_map = {"agent-audit": ModelTier.CAPABLE}

    def __init__(self, *, system_prompt_suffix: str = "", **kwargs: Any) -> None:
        """Initialize workflow.

        Args:
            system_prompt_suffix: Optional string appended to the
                orchestrator's system prompt at call time. Lets a
                wrapping caller (e.g. discovery-sweep's
                ``PerfAuditSource``) augment the prompt at the
                workflow-INSTANCE level without mutating the class
                template. Empty string (default) preserves prior
                behavior for every other caller.
            **kwargs: Passed to BaseWorkflow.__init__().
        """
        super().__init__(**kwargs)
        self._system_prompt_suffix = system_prompt_suffix

    input_schema = InputSchema(
        optional_fields={"path": str, "depth": str, "max_budget_usd": (int, float)},
    )

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK performance audit.

        Args:
            **kwargs: Keyword arguments.
                path (str): Required. Directory or file to audit.
                depth (str): Audit depth — "quick", "standard",
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
        # Optional explicit per-call USD cap (discovery-sweep plumbs each
        # source's allocation down here; budget-enforcement spec FR-1).
        # None → today's depth-derived cap, no behavior change.
        max_budget_usd: float | None = kwargs.get("max_budget_usd")

        started_at = datetime.now()

        try:
            run_result = await self._run_agent_audit(
                resolved_path, max_turns, depth, max_budget_usd=max_budget_usd
            )
            self._track_sdk_run_telemetry(stage="agent", agent_run_result=run_result)
            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                report_title="Performance audit",
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
            # crashing the CLI. Phase 4 of
            # docs/specs/sdk-error-message-fidelity/ — capture the
            # real claude CLI stderr via a second subprocess call,
            # classify it into a known kind, and thread the typed
            # fields onto WorkflowResult.metadata so the dashboard
            # can render the truth instead of regex-guessing.
            logger.exception(
                "Agent SDK perf audit failed: %s",
                type(exc).__name__,
            )
            stderr = capture_subprocess_failure(_last_subprocess_argv(exc))
            kind, summary = classify_subprocess_failure(stderr)
            sdk_err = SdkSubprocessError(
                message=summary,
                stderr=stderr,
                kind=kind,
                original_exc=exc,
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

        Returns:
            AgentRunResult with findings and SDK metadata.
        """
        assistant_parts: list[str] = []
        result_parts: list[str] = []
        run_result = AgentRunResult(result_text="No results returned.")
        system_prompt = _SYSTEM_PROMPT + (self._system_prompt_suffix or "")
        async for message in iter_agent_messages(
            claude_agent_sdk.query(
                prompt=_TASK_PROMPT_TEMPLATE.format(path=resolved_path),
                options=claude_agent_sdk.ClaudeAgentOptions(
                    **sdk_isolation_kwargs(),
                    system_prompt=system_prompt,
                    cwd=resolve_cwd_for_path(resolved_path),
                    max_budget_usd=get_max_budget_usd(depth, explicit=max_budget_usd),
                    allowed_tools=["Read", "Glob", "Grep", "Agent"],
                    permission_mode="default",
                    max_turns=max_turns,
                    agents={
                        "complexity-analyzer": claude_agent_sdk.AgentDefinition(
                            description=(
                                "Complexity analyzer that measures " "code complexity metrics."
                            ),
                            prompt=(
                                "You are a complexity analyzer. Focus "
                                "on: cyclomatic complexity, nesting "
                                "depth, large functions (>50 lines), "
                                "overly complex conditionals, and deep "
                                "class hierarchies. Report each finding "
                                "with file path, line number, metric "
                                "value, and simplification advice."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("complexity-analyzer"),
                        ),
                        "bottleneck-finder": claude_agent_sdk.AgentDefinition(
                            description=(
                                "Bottleneck finder that identifies " "performance issues."
                            ),
                            prompt=(
                                "You are a bottleneck finder. Focus "
                                "on: N+1 query patterns, unnecessary "
                                "list copies, blocking I/O in async "
                                "code, missing caching opportunities, "
                                "and inefficient data structures. "
                                "Report each finding with file path, "
                                "estimated performance impact, and a "
                                "concrete fix."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("bottleneck-finder"),
                        ),
                        "optimization-advisor": claude_agent_sdk.AgentDefinition(
                            description=(
                                "Optimization advisor that prioritizes " "and recommends fixes."
                            ),
                            prompt=(
                                "You are an optimization advisor. "
                                "Review the findings from the "
                                "complexity analyzer and bottleneck "
                                "finder. Prioritize them by estimated "
                                "impact (high/medium/low), suggest "
                                "concrete optimizations with code "
                                "examples, and estimate the effort "
                                "required for each fix."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("optimization-advisor"),
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
    """CLI entry point for performance audit workflow."""
    import asyncio

    async def run() -> None:
        """Run the performance audit."""
        workflow = PerformanceAuditWorkflow()
        result = await workflow.execute(path=".", depth="standard")
        output = result.final_output or {}

        print("\nPerformance Audit Results")
        print("=" * 50)
        print(f"Success: {result.success}")
        if result.error:
            print(f"Error: {result.error}")
        elif output:
            print(output)

    asyncio.run(run())


if __name__ == "__main__":
    main()
