"""Agent SDK Documentation Audit Workflow.

Delegates a full documentation audit to the Claude Agent SDK, using three
specialized subagents (staleness-checker, accuracy-reviewer, gap-finder)
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
    "staleness-checker",
    "accuracy-reviewer",
    "gap-finder",
]

_MAIN_PROMPT_TEMPLATE = """\
You are a senior documentation audit orchestrator. Audit the documentation \
at {path} using the three specialized subagents below. Each subagent should \
focus on its domain and report findings as structured markdown.

After all subagents finish, synthesize their findings into a single \
report with these sections:

## Summary
Overall documentation health score (0-100) and a 2-3 sentence executive summary.

## Documentation
Consolidated findings from all three reviewers organized by severity.

## Suggestions
Actionable next steps ordered by priority.

Be thorough but concise. Cite file paths and line numbers when possible.\
"""


class DocAuditAgentSDKWorkflow(BaseWorkflow):
    """Documentation audit workflow powered by the Claude Agent SDK.

    Delegates all analysis to three Agent SDK subagents rather
    than using the mixin stage system. Each subagent focuses on
    a specific audit domain (staleness, accuracy, gaps). The
    orchestrator synthesizes findings into a unified report.

    Usage::

        workflow = DocAuditAgentSDKWorkflow()
        result = await workflow.execute(path="docs/", depth="standard")
    """

    name = "doc-audit-sdk"
    description = "Agent SDK-powered documentation audit with 3 specialized subagents"
    stages = ["agent-audit"]
    tier_map = {"agent-audit": ModelTier.CAPABLE}

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK documentation audit.

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
            logger.exception("Agent SDK doc audit failed: %s", type(exc).__name__)
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
                    "staleness-checker": claude_agent_sdk.AgentDefinition(
                        description="Staleness checker that finds outdated documentation.",
                        prompt=(
                            "You are a documentation staleness checker. "
                            "Focus on: outdated docs, stale version "
                            "references, dead links, and obsolete "
                            "examples. Report each finding with file "
                            "path, line number, severity, and "
                            "remediation advice."
                        ),
                        tools=["Read", "Glob", "Grep"],
                    ),
                    "accuracy-reviewer": claude_agent_sdk.AgentDefinition(
                        description="Accuracy reviewer that verifies docs match code.",
                        prompt=(
                            "You are a documentation accuracy reviewer. "
                            "Focus on: verifying docs match current code "
                            "behavior, API signatures, and config "
                            "options. Report each finding with file "
                            "path, severity, and correction advice."
                        ),
                        tools=["Read", "Glob", "Grep"],
                    ),
                    "gap-finder": claude_agent_sdk.AgentDefinition(
                        description="Gap finder that identifies missing documentation.",
                        prompt=(
                            "You are a documentation gap finder. Focus "
                            "on: identifying missing docs for public "
                            "APIs, undocumented features, and missing "
                            "examples. Report each finding with the "
                            "affected module, severity, and what "
                            "documentation should be added."
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
                    description="Agent SDK doc audit",
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
