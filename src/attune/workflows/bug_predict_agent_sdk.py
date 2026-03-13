"""Agent SDK Bug Prediction Workflow.

Delegates bug prediction to the Claude Agent SDK, using three
specialized subagents (pattern-scanner, risk-correlator,
prevention-advisor) and synthesizing their findings into a
unified WorkflowResult.

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
    "pattern-scanner",
    "risk-correlator",
    "prevention-advisor",
]

_MAIN_PROMPT_TEMPLATE = """\
You are a bug prediction orchestrator. Analyze the codebase at {path} \
using the three specialized subagents below. Each subagent should focus \
on its domain and report findings as structured markdown.

After all subagents finish, synthesize their findings into a single \
report with these sections:

## Summary
Overall risk score (0-100) and a 2-3 sentence executive summary of \
predicted bug hotspots.

## Bugs
Predicted bugs organized by severity (HIGH, MEDIUM, LOW). Each entry \
should include file path, line number, pattern type, and description.

## Suggestions
Actionable prevention strategies ordered by priority. Include specific \
refactoring advice and testing recommendations.

Be thorough but concise. Cite file paths and line numbers when possible.\
"""


class BugPredictAgentSDKWorkflow(BaseWorkflow):
    """Bug prediction workflow powered by the Claude Agent SDK.

    Delegates all analysis to three Agent SDK subagents rather
    than using the mixin stage system. Each subagent focuses on
    a specific prediction domain (pattern scanning, risk
    correlation, prevention advice). The orchestrator synthesizes
    findings into a unified report.

    Usage::

        workflow = BugPredictAgentSDKWorkflow()
        result = await workflow.execute(path="src/", depth="standard")
    """

    name = "bug-predict-sdk"
    description = "Agent SDK-powered bug prediction with 3 specialized subagents"
    stages = ["agent-predict"]
    tier_map = {"agent-predict": ModelTier.CAPABLE}

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK bug prediction.

        Args:
            **kwargs: Keyword arguments.
                path (str): Required. Directory or file to scan.
                depth (str): Prediction depth — "quick", "standard",
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
            result_text = await self._run_agent_predict(resolved_path, max_turns)

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
            logger.exception("Agent SDK bug prediction failed: %s", type(exc).__name__)
            return self._error_result(f"Agent SDK error: {type(exc).__name__}: {exc}")

    async def _run_agent_predict(self, resolved_path: str, max_turns: int) -> str:
        """Run the Agent SDK prediction and return result text.

        Args:
            resolved_path: Absolute path to scan.
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
                    "pattern-scanner": claude_agent_sdk.AgentDefinition(
                        description="Pattern scanner that finds common bug patterns.",
                        prompt=(
                            "You are a bug pattern scanner. Focus on: "
                            "null references, type mismatches, race "
                            "conditions, eval/exec usage, broad "
                            "exception handlers, resource leaks, and "
                            "off-by-one errors. Report each finding "
                            "with file path, line number, pattern "
                            "type, and severity."
                        ),
                        tools=["Read", "Glob", "Grep"],
                    ),
                    "risk-correlator": claude_agent_sdk.AgentDefinition(
                        description="Risk correlator that assesses bug likelihood.",
                        prompt=(
                            "You are a risk correlator. Analyze "
                            "findings from the pattern scanner and "
                            "correlate them with file complexity, "
                            "change frequency, and historical bug "
                            "density. Assign risk scores to each "
                            "file and identify the highest-risk "
                            "modules. Report with file path, risk "
                            "score, and contributing factors."
                        ),
                        tools=["Read", "Glob", "Grep"],
                    ),
                    "prevention-advisor": claude_agent_sdk.AgentDefinition(
                        description="Prevention advisor that suggests mitigation strategies.",
                        prompt=(
                            "You are a prevention advisor. Review "
                            "the correlated risk findings and "
                            "prioritize them by impact. Suggest "
                            "specific prevention strategies: code "
                            "refactoring, additional tests, type "
                            "annotations, error handling improvements, "
                            "and architectural changes. Report with "
                            "priority, affected files, and actionable "
                            "steps."
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
                    name="agent-predict",
                    tier=ModelTier.CAPABLE,
                    description="Agent SDK bug prediction",
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
