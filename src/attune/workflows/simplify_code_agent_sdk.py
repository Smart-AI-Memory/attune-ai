"""Agent SDK Code Simplification Workflow.

Delegates code simplification to the Claude Agent SDK, using three
specialized subagents (complexity-scanner, simplification-designer,
safety-reviewer) and synthesizing their findings into a unified
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
    "complexity-scanner",
    "simplification-designer",
    "safety-reviewer",
]

_MAIN_PROMPT_TEMPLATE = """\
You are a senior code simplification orchestrator. Analyze the codebase at \
{path} using the three specialized subagents below. Each subagent should \
focus on its domain and report findings as structured markdown.

After all subagents finish, synthesize their findings into a single \
report with these sections:

## Summary
Overall complexity score (0-100) and a 2-3 sentence executive summary \
of simplification opportunities.

## Complexity
Findings from the complexity scanner — deep nesting, long functions, \
unnecessary abstractions, dead code paths, and over-engineered patterns.

## Refactoring
Proposed simplifications from the simplification designer — flattened \
conditionals, inlined helpers, reduced class hierarchies, and removed \
dead code.

## Suggestions
Safety-reviewed actionable next steps ordered by impact. Each suggestion \
should note whether it is safe to apply automatically or requires manual \
review.

Be thorough but concise. Cite file paths and line numbers when possible.\
"""


class SimplifyCodeAgentSDKWorkflow(BaseWorkflow):
    """Code simplification workflow powered by the Claude Agent SDK.

    Delegates all analysis to three Agent SDK subagents rather
    than using the mixin stage system. Each subagent focuses on
    a specific simplification domain (complexity scanning,
    simplification design, safety review). The orchestrator
    synthesizes findings into a unified report.

    Usage::

        workflow = SimplifyCodeAgentSDKWorkflow()
        result = await workflow.execute(path="src/", depth="standard")
    """

    name = "simplify-code-sdk"
    description = "Agent SDK-powered code simplification with 3 specialized subagents"
    stages = ["agent-simplify"]
    tier_map = {"agent-simplify": ModelTier.CAPABLE}

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK code simplification.

        Args:
            **kwargs: Keyword arguments.
                path (str): Required. Directory or file to simplify.
                depth (str): Analysis depth — "quick", "standard",
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
            result_text = await self._run_agent_simplify(resolved_path, max_turns)

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
            logger.exception("Agent SDK code simplification failed: %s", type(exc).__name__)
            return self._error_result(f"Agent SDK error: {type(exc).__name__}: {exc}")

    async def _run_agent_simplify(self, resolved_path: str, max_turns: int) -> str:
        """Run the Agent SDK simplification and return result text.

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
                    "complexity-scanner": claude_agent_sdk.AgentDefinition(
                        description="Complexity scanner that finds overly complex code.",
                        prompt=(
                            "You are a complexity scanner. Focus on: "
                            "deep nesting (3+ levels), long functions "
                            "(50+ lines), unnecessary abstractions, "
                            "dead code paths, and over-engineered "
                            "patterns. Report each finding with file "
                            "path, line number, complexity metric, and "
                            "why it should be simplified."
                        ),
                        tools=["Read", "Glob", "Grep"],
                    ),
                    "simplification-designer": claude_agent_sdk.AgentDefinition(
                        description="Simplification designer that proposes refactoring approaches.",
                        prompt=(
                            "You are a simplification designer. For "
                            "each complexity finding, design a concrete "
                            "simplification approach: flatten nested "
                            "conditionals with early returns, inline "
                            "trivial helper functions used only once, "
                            "reduce class hierarchies when a function "
                            "suffices, and remove dead code. Show "
                            "before/after examples."
                        ),
                        tools=["Read", "Glob", "Grep"],
                    ),
                    "safety-reviewer": claude_agent_sdk.AgentDefinition(
                        description="Safety reviewer that verifies simplifications won't break behavior.",
                        prompt=(
                            "You are a safety reviewer. For each "
                            "proposed simplification, verify it does "
                            "not break existing behavior, public APIs, "
                            "or tests. Check for side effects, changed "
                            "return types, removed error handling, and "
                            "altered control flow. Flag any risky "
                            "changes that need manual review."
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
                    name="agent-simplify",
                    tier=ModelTier.CAPABLE,
                    description="Agent SDK code simplification",
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
