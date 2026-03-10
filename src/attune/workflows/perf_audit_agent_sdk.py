"""Agent SDK Performance Audit Workflow.

Delegates a full performance audit to the Claude Agent SDK, using three
specialized subagents (complexity-analyzer, bottleneck-finder,
optimization-advisor) and synthesizing their findings into a unified
WorkflowResult.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .agent_sdk_adapter import AgentSDKResultAdapter
from .base import BaseWorkflow, ModelTier
from .data_classes import CostReport, WorkflowResult, WorkflowStage

logger = logging.getLogger(__name__)

# Module-level availability guard for claude_agent_sdk
_SDK_AVAILABLE = False
try:
    import claude_agent_sdk  # type: ignore[import-untyped]

    _SDK_AVAILABLE = True
except ImportError:
    claude_agent_sdk = None  # type: ignore[assignment]

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

_MAIN_PROMPT_TEMPLATE = """\
You are a senior performance audit orchestrator. Audit the codebase at {path} \
using the three specialized subagents below. Each subagent should focus on \
its domain and report findings as structured markdown.

After all subagents finish, synthesize their findings into a single \
report with these sections:

## Summary
Overall performance health score (0-100) and a 2-3 sentence executive summary.

## Performance
Key performance findings across the codebase.

## Complexity
Findings from the complexity analyzer — cyclomatic complexity, nesting \
depth, and oversized functions.

## Optimization
Findings from the bottleneck finder and optimization advisor — N+1 patterns, \
unnecessary list copies, blocking I/O, missing caching, and prioritized \
suggestions with estimated impact.

## Suggestions
Actionable next steps ordered by estimated performance impact.

Be thorough but concise. Cite file paths and line numbers when possible.\
"""


class PerfAuditAgentSDKWorkflow(BaseWorkflow):
    """Performance audit workflow powered by the Claude Agent SDK.

    Delegates all analysis to three Agent SDK subagents rather
    than using the mixin stage system. Each subagent focuses on
    a specific audit domain (complexity, bottlenecks, optimization).
    The orchestrator synthesizes findings into a unified report.

    Usage::

        workflow = PerfAuditAgentSDKWorkflow()
        result = await workflow.execute(path="src/", depth="standard")
    """

    name = "perf-audit-sdk"
    description = "Agent SDK-powered performance audit with 3 specialized subagents"
    stages = ["agent-audit"]
    tier_map = {"agent-audit": ModelTier.CAPABLE}

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
        path_arg: str = kwargs.get("path", "")
        depth: str = kwargs.get("depth", "standard")

        if not path_arg:
            return self._error_result("path argument is required")

        if not _SDK_AVAILABLE:
            return self._error_result(
                "claude-agent-sdk not installed. " "Install with: pip install claude-agent-sdk"
            )

        resolved_path = str(Path(path_arg).resolve())
        max_turns = _DEPTH_MAX_TURNS.get(depth, 20)

        started_at = datetime.now()

        try:
            result_text = await self._run_agent_audit(resolved_path, max_turns)

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
            logger.exception("Agent SDK perf audit failed: %s", type(exc).__name__)
            return self._error_result(f"Agent SDK error: {type(exc).__name__}: {exc}")

    async def _run_agent_audit(self, resolved_path: str, max_turns: int) -> str:
        """Run the Agent SDK audit and return result text.

        Args:
            resolved_path: Absolute path to audit.
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
                    "complexity-analyzer": claude_agent_sdk.AgentDefinition(
                        description="Complexity analyzer that measures code complexity metrics.",
                        prompt=(
                            "You are a complexity analyzer. Focus on: "
                            "cyclomatic complexity, nesting depth, "
                            "large functions (>50 lines), overly complex "
                            "conditionals, and deep class hierarchies. "
                            "Report each finding with file path, line "
                            "number, metric value, and simplification "
                            "advice."
                        ),
                        tools=["Read", "Glob", "Grep"],
                    ),
                    "bottleneck-finder": claude_agent_sdk.AgentDefinition(
                        description="Bottleneck finder that identifies performance issues.",
                        prompt=(
                            "You are a bottleneck finder. Focus on: "
                            "N+1 query patterns, unnecessary list copies, "
                            "blocking I/O in async code, missing caching "
                            "opportunities, and inefficient data structures. "
                            "Report each finding with file path, estimated "
                            "performance impact, and a concrete fix."
                        ),
                        tools=["Read", "Glob", "Grep"],
                    ),
                    "optimization-advisor": claude_agent_sdk.AgentDefinition(
                        description="Optimization advisor that prioritizes and recommends fixes.",
                        prompt=(
                            "You are an optimization advisor. Review the "
                            "findings from the complexity analyzer and "
                            "bottleneck finder. Prioritize them by "
                            "estimated impact (high/medium/low), suggest "
                            "concrete optimizations with code examples, "
                            "and estimate the effort required for each fix."
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
                    name="agent-audit",
                    tier=ModelTier.CAPABLE,
                    description="Agent SDK performance audit",
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
