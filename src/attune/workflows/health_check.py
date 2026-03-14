"""Agent SDK Health Check Workflow.

Delegates project health checks to the Claude Agent SDK, using
dynamically selected subagents based on mode (quick, standard, full).
Each subagent focuses on a specific health domain and reports findings
as structured markdown.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
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

logger = logging.getLogger(__name__)


_DEPTH_MAX_TURNS: dict[str, int] = {
    "quick": 10,
    "standard": 20,
    "deep": 40,
}

_ALL_SUBAGENT_DEFS: dict[str, dict[str, str]] = {
    "test-checker": {
        "description": "Verifies test suite health and coverage.",
        "prompt": (
            "You are a test health checker. Run pytest if possible, "
            "check test counts, coverage reports, and identify flaky "
            "tests. Report findings with file paths and severity."
        ),
    },
    "dep-checker": {
        "description": "Checks dependency health and security.",
        "prompt": (
            "You are a dependency health checker. Check pyproject.toml "
            "and requirements for outdated, vulnerable, or unused "
            "dependencies. Report findings with package names and "
            "recommended actions."
        ),
    },
    "lint-checker": {
        "description": "Verifies code quality and linting status.",
        "prompt": (
            "You are a lint checker. Check for ruff/flake8 violations, "
            "type hint coverage, and code style consistency. Report "
            "findings with file paths and fix suggestions."
        ),
    },
    "ci-checker": {
        "description": "Checks CI/CD pipeline health.",
        "prompt": (
            "You are a CI/CD health checker. Review GitHub Actions "
            "workflows, check for failures, slow jobs, and missing "
            "checks. Report findings with workflow names and "
            "recommendations."
        ),
    },
    "doc-checker": {
        "description": "Checks documentation health.",
        "prompt": (
            "You are a documentation health checker. Check for stale "
            "docs, missing API docs, broken links, and outdated "
            "examples. Report findings with file paths."
        ),
    },
    "security-checker": {
        "description": "Checks security posture.",
        "prompt": (
            "You are a security health checker. Check for known "
            "vulnerabilities, missing security headers, exposed "
            "secrets, and unsafe patterns. Report findings with "
            "severity levels."
        ),
    },
}

_MODE_SUBAGENTS: dict[str, list[str]] = {
    "quick": ["test-checker", "dep-checker", "lint-checker"],
    "standard": [
        "test-checker",
        "dep-checker",
        "lint-checker",
        "ci-checker",
        "doc-checker",
    ],
    "full": list(_ALL_SUBAGENT_DEFS.keys()),
}

_SYSTEM_PROMPT = """\
You are a project health check orchestrator. Coordinate specialized \
subagents to assess project health and synthesize their findings into \
a single structured report. Be thorough but concise. Cite file paths \
and line numbers when possible.\
"""

_TASK_PROMPT_TEMPLATE = """\
Assess the health of the project at {project_root} using the \
specialized subagents below. Each subagent should focus on its domain \
and report findings as structured markdown.

After all subagents finish, synthesize their findings into a single \
report with these sections:

## Summary
Overall project health score (0-100) and a 2-3 sentence executive summary.

## Test Health
Findings from the test checker.

## Dependencies
Findings from the dependency checker.

## Code Quality
Findings from the lint checker.

## CI/CD
Findings from the CI checker (if included).

## Documentation
Findings from the doc checker (if included).

## Security
Findings from the security checker (if included).

## Recommendations
Actionable next steps ordered by priority.\
"""


class HealthCheckAgentSDKWorkflow(BaseWorkflow):
    """Health check workflow powered by the Claude Agent SDK.

    Delegates all analysis to dynamically selected Agent SDK subagents
    based on mode (quick, standard, full). Each subagent focuses on a
    specific health domain. The orchestrator synthesizes findings into
    a unified report.

    Usage::

        workflow = HealthCheckAgentSDKWorkflow()
        result = await workflow.execute(project_root=".", mode="standard")
    """

    name = "health-check"
    description = "Agent SDK-powered health check with dynamic subagents based on mode"
    stages = ["agent-check"]
    tier_map = {"agent-check": ModelTier.CAPABLE}

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK health check.

        Args:
            **kwargs: Keyword arguments.
                project_root (str): Required. Project root directory.
                mode (str): Check mode — "quick", "standard", or
                    "full". Defaults to "standard".
                depth (str): Agent depth — "quick", "standard",
                    or "deep". Defaults to "standard".

        Returns:
            WorkflowResult with findings, recommendations, and metadata.
        """
        project_root: str = kwargs.get("project_root", "")
        mode: str = kwargs.get("mode", "standard")
        depth: str = kwargs.get("depth", "standard")

        if not project_root:
            return self._error_result("project_root argument is required")

        resolved_root = str(Path(project_root).resolve())
        max_turns = _DEPTH_MAX_TURNS.get(depth, 20)

        # Select subagents based on mode
        subagent_names = _MODE_SUBAGENTS.get(mode, _MODE_SUBAGENTS["standard"])
        active_defs = {name: _ALL_SUBAGENT_DEFS[name] for name in subagent_names}

        started_at = datetime.now()

        try:
            run_result = await self._run_agent_check(
                resolved_root, max_turns, subagent_names, active_defs, depth=depth
            )

            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                result_text=run_result.result_text,
                subagent_names=subagent_names,
                started_at=started_at,
                completed_at=completed_at,
                metadata={
                    "project_root": resolved_root,
                    "mode": mode,
                    "depth": depth,
                    "max_turns": max_turns,
                    "subagents": subagent_names,
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
            logger.exception("Agent SDK health check failed: %s", type(exc).__name__)
            return self._error_result(f"Agent SDK error: {type(exc).__name__}: {exc}")

    async def _run_agent_check(
        self,
        resolved_root: str,
        max_turns: int,
        subagent_names: list[str],
        active_defs: dict[str, dict[str, str]],
        depth: str = "standard",
    ) -> AgentRunResult:
        """Run the Agent SDK health check and return result text.

        Args:
            resolved_root: Absolute path to project root.
            max_turns: Maximum agent turns.
            subagent_names: List of subagent names to activate.
            active_defs: Subagent definitions for active agents.
            depth: Agent depth for budget calculation.

        Returns:
            AgentRunResult with findings and SDK metadata.
        """
        agents = {}
        for agent_name in subagent_names:
            defn = active_defs[agent_name]
            agents[agent_name] = claude_agent_sdk.AgentDefinition(
                description=defn["description"],
                prompt=defn["prompt"],
                tools=["Read", "Glob", "Grep", "Bash"],
                model=get_subagent_model(agent_name),
            )

        result_parts: list[str] = []
        run_result = AgentRunResult(result_text="No results returned.")
        async for message in claude_agent_sdk.query(
            prompt=_TASK_PROMPT_TEMPLATE.format(project_root=resolved_root),
            options=claude_agent_sdk.ClaudeAgentOptions(
                system_prompt=_SYSTEM_PROMPT,
                cwd=resolved_root,
                max_budget_usd=get_max_budget_usd(depth),
                allowed_tools=["Read", "Glob", "Grep", "Bash", "Agent"],
                permission_mode="default",
                max_turns=max_turns,
                agents=agents,
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
                    name="agent-check",
                    tier=ModelTier.CAPABLE,
                    description="Agent SDK health check",
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
