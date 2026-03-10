"""Agent SDK Research Synthesis Workflow.

Delegates research synthesis to the Claude Agent SDK, using three
specialized subagents (source-summarizer, pattern-analyst,
synthesis-writer) and producing a cohesive synthesis report.

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
    "source-summarizer",
    "pattern-analyst",
    "synthesis-writer",
]

_MAIN_PROMPT_TEMPLATE = """\
You are a research synthesis orchestrator. Analyze the source \
documents at {path} using the three specialized subagents below. \
Each subagent should focus on its domain and report findings as \
structured markdown.

After all subagents finish, combine their outputs into a single \
cohesive report with these sections:

## Summary
A 2-3 sentence executive summary of the key findings and their \
significance.

## Research
Detailed findings organized by theme, with citations to specific \
source documents and data points.

## Suggestions
Actionable recommendations and areas for further investigation, \
ordered by priority.

Be thorough but concise. Cite source documents and specific \
passages when possible.\
"""


class ResearchSynthesisAgentSDKWorkflow(BaseWorkflow):
    """Research synthesis workflow powered by the Claude Agent SDK.

    Delegates all analysis to three Agent SDK subagents rather
    than using the mixin stage system. Each subagent focuses on
    a specific synthesis task (summarization, pattern analysis,
    report writing). The orchestrator produces a cohesive
    synthesis report.

    Usage::

        workflow = ResearchSynthesisAgentSDKWorkflow()
        result = await workflow.execute(path="docs/research/", depth="standard")
    """

    name = "research-synthesis-sdk"
    description = "Agent SDK-powered research synthesis with 3 specialized subagents"
    stages = ["agent-synthesis"]
    tier_map = {"agent-synthesis": ModelTier.CAPABLE}

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK research synthesis.

        Args:
            **kwargs: Keyword arguments.
                path (str): Required. Directory or file to analyze.
                depth (str): Synthesis depth — "quick", "standard",
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
            result_text = await self._run_agent_synthesis(resolved_path, max_turns)

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
            logger.exception("Agent SDK research synthesis failed: %s", type(exc).__name__)
            return self._error_result(f"Agent SDK error: {type(exc).__name__}: {exc}")

    async def _run_agent_synthesis(self, resolved_path: str, max_turns: int) -> str:
        """Run the Agent SDK synthesis and return result text.

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
                    "source-summarizer": claude_agent_sdk.AgentDefinition(
                        description="Source summarizer that reads and extracts key findings.",
                        prompt=(
                            "You are a source summarizer. Read and "
                            "summarize source documents, extracting "
                            "key findings and data points. For each "
                            "source, report the document title, main "
                            "arguments, supporting evidence, and "
                            "notable data points. Organize by source."
                        ),
                        tools=["Read", "Glob", "Grep"],
                    ),
                    "pattern-analyst": claude_agent_sdk.AgentDefinition(
                        description="Pattern analyst that identifies themes and connections.",
                        prompt=(
                            "You are a pattern analyst. Identify "
                            "patterns, themes, and connections across "
                            "summarized sources. Look for recurring "
                            "arguments, contradictions, complementary "
                            "findings, and emerging trends. Report "
                            "each pattern with supporting citations "
                            "from multiple sources."
                        ),
                        tools=["Read", "Glob", "Grep"],
                    ),
                    "synthesis-writer": claude_agent_sdk.AgentDefinition(
                        description="Synthesis writer that produces a cohesive report.",
                        prompt=(
                            "You are a synthesis writer. Write a "
                            "cohesive synthesis report combining all "
                            "findings with citations. Integrate "
                            "source summaries and identified patterns "
                            "into a narrative that highlights key "
                            "insights, resolves contradictions, and "
                            "suggests areas for further investigation."
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
                    name="agent-synthesis",
                    tier=ModelTier.CAPABLE,
                    description="Agent SDK research synthesis",
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
