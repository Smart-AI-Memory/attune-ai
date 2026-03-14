"""Dependency Check Workflow

Audits dependencies for vulnerabilities, updates, and licensing issues.
Delegates analysis to Agent SDK subagents (inventory-assessor,
update-advisor) and synthesizes their findings into a unified report.

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
from .dependency_check_audit import (  # noqa: F401
    CACHE_DIR,
    _get_cache_path,
    _load_cached_advisories,
    _run_npm_audit,
    _run_pip_audit,
    _save_advisory_cache,
)
from .dependency_check_report import (  # noqa: F401
    format_dependency_check_report,
    main,
)
from .step_config import WorkflowStepConfig

logger = logging.getLogger(__name__)

# Define step configurations for executor-based execution
DEPENDENCY_CHECK_STEPS = {
    "report": WorkflowStepConfig(
        name="report",
        task_type="analyze",  # Capable tier task
        tier_hint="capable",
        description="Generate dependency security report with remediation steps",
        max_tokens=3000,
    ),
}

_DEPTH_MAX_TURNS: dict[str, int] = {
    "quick": 10,
    "standard": 20,
    "deep": 40,
}

_SUBAGENT_NAMES = [
    "inventory-assessor",
    "update-advisor",
]

_SYSTEM_PROMPT = """\
You are a dependency check orchestrator. You coordinate two specialized \
subagents to produce a unified dependency audit report. Be thorough but \
concise. Cite package names and version numbers.\
"""

_TASK_PROMPT_TEMPLATE = """\
Analyze the project at {path} using the two specialized subagents \
below. Each subagent should focus on its domain and report findings \
as structured markdown.

After all subagents finish, synthesize their findings into a single \
report with these sections:

## Summary
Overall dependency health score (0-100) and a 2-3 sentence executive summary.

## Dependencies
Full inventory of direct and transitive dependencies with current versions, \
latest available versions, and vulnerability status.

## Suggestions
Prioritized update plan ordered by urgency — security patches first, then \
breaking-change-free updates, then major upgrades with migration notes.\
"""


class DependencyCheckWorkflow(BaseWorkflow):
    """Audit dependencies with Agent SDK subagents.

    Delegates all analysis to two Agent SDK subagents rather than using
    the mixin stage system. The inventory-assessor inventories all
    dependencies and checks for outdated or vulnerable packages. The
    update-advisor assesses update urgency and creates a prioritized
    update plan.

    Usage::

        workflow = DependencyCheckWorkflow()
        result = await workflow.execute(path=".", depth="standard")
    """

    name = "dependency-check"
    description = "Audit dependencies with Agent SDK subagents"
    stages = ["agent-check"]
    tier_map = {"agent-check": ModelTier.CAPABLE}

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK dependency check.

        Args:
            **kwargs: Keyword arguments.
                path (str): Required. Project directory to check.
                depth (str): Check depth — "quick", "standard",
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
            run_result = await self._run_agent_check(resolved_path, max_turns, depth)

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
            logger.exception("Agent SDK dependency check failed: %s", type(exc).__name__)
            return self._error_result(f"Agent SDK error: {type(exc).__name__}: {exc}")

    async def _run_agent_check(
        self, resolved_path: str, max_turns: int, depth: str = "standard"
    ) -> AgentRunResult:
        """Run the Agent SDK dependency check and return result text.

        Args:
            resolved_path: Absolute path to the project.
            max_turns: Maximum agent turns.

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
                    "inventory-assessor": claude_agent_sdk.AgentDefinition(
                        description=("Dependency inventory assessor that catalogs all packages."),
                        prompt=(
                            "You are a dependency inventory assessor. "
                            "Inventory all dependencies from pyproject.toml, "
                            "requirements.txt, setup.cfg, and lock files. "
                            "Use Bash to run pip list, pip show, and "
                            "pip-audit (if available) to check for outdated "
                            "or vulnerable packages. Report each dependency "
                            "with name, installed version, latest version, "
                            "and any known CVEs."
                        ),
                        tools=["Read", "Glob", "Grep", "Bash"],
                        model=get_subagent_model("inventory-assessor"),
                    ),
                    "update-advisor": claude_agent_sdk.AgentDefinition(
                        description=("Update advisor that prioritizes dependency updates."),
                        prompt=(
                            "You are a dependency update advisor. "
                            "Assess update urgency for each outdated "
                            "dependency. Evaluate breaking change risk "
                            "by reading changelogs and migration guides. "
                            "Create a prioritized update plan: security "
                            "patches first, then compatible updates, then "
                            "major version upgrades with migration notes."
                        ),
                        tools=["Read", "Glob", "Grep"],
                        model=get_subagent_model("update-advisor"),
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
                    name="agent-check",
                    tier=ModelTier.CAPABLE,
                    description="Agent SDK dependency check",
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
