"""Release Preparation Workflow

Pre-release quality gate with Agent SDK subagents for health checks,
security scanning, changelog generation, and release assessment.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import claude_agent_sdk

from .agent_sdk_adapter import (
    AgentRunResult,
    AgentSDKResultAdapter,
    get_max_budget_usd,
    get_subagent_model,
)
from .base import BaseWorkflow, ModelTier
from .data_classes import CostReport, WorkflowResult, WorkflowStage
from .release_prep_approve import RELEASE_PREP_STEPS  # noqa: F401
from .release_prep_report import format_release_prep_report, main  # noqa: F401

__all__ = [
    "RELEASE_PREP_STEPS",
    "ReleasePreparationWorkflow",
    "format_release_prep_report",
    "main",
]

logger = logging.getLogger(__name__)

_DEPTH_MAX_TURNS: dict[str, int] = {
    "quick": 10,
    "standard": 20,
    "deep": 40,
}

_SUBAGENT_NAMES = [
    "health-checker",
    "security-scanner",
    "changelog-generator",
    "release-assessor",
]

_SYSTEM_PROMPT = """\
You are a release preparation orchestrator. Coordinate four specialized \
subagents to assess release readiness and synthesize their findings \
into a single structured report. Be thorough but concise. Cite file \
paths and line numbers when possible.\
"""

_TASK_PROMPT_TEMPLATE = """\
Assess release readiness for the codebase at {path} using the four \
specialized subagents below. Each subagent should focus on its domain \
and report findings as structured markdown.

After all subagents finish, synthesize their findings into a single \
report with these sections:

## Summary
Overall release readiness score (0-100) and a 2-3 sentence executive \
summary with a go/no-go recommendation.

## Health
Findings from the health checker — test results, dependency status, \
CI pipeline health.

## Security
Findings from the security scanner — vulnerabilities, outdated \
dependencies, secret leaks.

## Changelog
Generated changelog from the changelog generator — notable changes \
since last release.

## Suggestions
Actionable next steps ordered by priority, including any blockers \
that must be resolved before release.\
"""


class ReleasePreparationWorkflow(BaseWorkflow):
    """Pre-release quality gate workflow powered by Agent SDK subagents.

    Delegates all analysis to four Agent SDK subagents rather than
    using the mixin stage system. Each subagent focuses on a specific
    release-readiness domain (health, security, changelog, assessment).
    The orchestrator synthesizes findings into a unified report.

    Usage::

        workflow = ReleasePreparationWorkflow()
        result = await workflow.execute(path=".", depth="standard")
    """

    name = "release-prep"
    description = "Pre-release quality gate with Agent SDK subagents"
    stages = ["agent-prep"]
    tier_map = {"agent-prep": ModelTier.CAPABLE}

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK release preparation.

        Args:
            **kwargs: Keyword arguments.
                path (str): Required. Project root to assess.
                depth (str): Preparation depth — "quick", "standard",
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
            run_result = await self._run_agent_prep(resolved_path, max_turns, depth=depth)

            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
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
            # INTENTIONAL: Catch-all for unknown SDK errors to return
            # a structured WorkflowResult rather than crashing.
            logger.exception("Agent SDK release prep failed: %s", type(exc).__name__)
            return self._error_result(f"Agent SDK error: {type(exc).__name__}: {exc}")

    async def _run_agent_prep(
        self, resolved_path: str, max_turns: int, depth: str = "standard"
    ) -> AgentRunResult:
        """Run the Agent SDK release prep and return result text.

        Args:
            resolved_path: Absolute path to assess.
            max_turns: Maximum agent turns.
            depth: Agent depth for budget calculation.

        Returns:
            AgentRunResult with findings and SDK metadata.
        """
        result_parts: list[str] = []
        run_result = AgentRunResult(result_text="No results returned.")
        async for message in claude_agent_sdk.query(
            prompt=_TASK_PROMPT_TEMPLATE.format(path=resolved_path),
            options=claude_agent_sdk.ClaudeAgentOptions(
                system_prompt=_SYSTEM_PROMPT,
                cwd=resolved_path,
                max_budget_usd=get_max_budget_usd(depth),
                allowed_tools=["Read", "Glob", "Grep", "Bash", "Agent"],
                permission_mode="default",
                max_turns=max_turns,
                agents={
                    "health-checker": claude_agent_sdk.AgentDefinition(
                        description="Health checker that runs tests and verifies CI status.",
                        prompt=(
                            "You are a release health checker. Focus on: "
                            "running the test suite, checking dependency "
                            "versions and lock files, verifying CI pipeline "
                            "status, and confirming build artifacts are "
                            "reproducible. Report each finding with status "
                            "(pass/fail), details, and remediation if needed."
                        ),
                        tools=["Read", "Glob", "Grep", "Bash"],
                        model=get_subagent_model("health-checker"),
                    ),
                    "security-scanner": claude_agent_sdk.AgentDefinition(
                        description="Security scanner for vulnerabilities and secret leaks.",
                        prompt=(
                            "You are a security scanner for release prep. "
                            "Focus on: known vulnerabilities in dependencies, "
                            "outdated packages with CVEs, hardcoded secrets "
                            "or credentials, eval/exec usage, and path "
                            "traversal risks. Report each finding with "
                            "severity, file path, and remediation advice."
                        ),
                        tools=["Read", "Glob", "Grep"],
                        model=get_subagent_model("security-scanner"),
                    ),
                    "changelog-generator": claude_agent_sdk.AgentDefinition(
                        description="Changelog generator from git history.",
                        prompt=(
                            "You are a changelog generator. Use git log to "
                            "identify notable changes since the last release "
                            "tag. Categorize changes as: Features, Fixes, "
                            "Breaking Changes, Documentation, and Internal. "
                            "Output a draft CHANGELOG section in Keep a "
                            "Changelog format."
                        ),
                        tools=["Read", "Glob", "Grep", "Bash"],
                        model=get_subagent_model("changelog-generator"),
                    ),
                    "release-assessor": claude_agent_sdk.AgentDefinition(
                        description="Release assessor for overall readiness and go/no-go.",
                        prompt=(
                            "You are a release readiness assessor. Review "
                            "the overall state of the project including: "
                            "test coverage, documentation completeness, "
                            "version bumps, migration guides, and any "
                            "release blockers. Provide a clear go/no-go "
                            "recommendation with justification."
                        ),
                        tools=["Read", "Glob", "Grep"],
                        model=get_subagent_model("release-assessor"),
                    ),
                },
            ),
        ):
            if isinstance(message, claude_agent_sdk.ResultMessage):
                result_parts.append(message.result or "")
                run_result = AgentRunResult(
                    result_text="",
                    total_cost_usd=message.total_cost_usd,
                    usage=message.usage,
                    duration_ms=message.duration_ms,
                    duration_api_ms=message.duration_api_ms,
                    num_turns=message.num_turns,
                    session_id=message.session_id,
                    is_error=message.is_error,
                )
        run_result.result_text = "\n".join(result_parts) if result_parts else "No results returned."
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
                    name="agent-prep",
                    tier=ModelTier.CAPABLE,
                    description="Agent SDK release preparation",
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


if __name__ == "__main__":
    main()
