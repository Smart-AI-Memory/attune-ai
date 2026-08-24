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
    build_result_text,
    collect_agent_output,
    get_max_budget_usd,
    get_subagent_model,
    iter_agent_messages,
    resolve_cwd_for_path,
    sdk_error_from_exception,
    sdk_isolation_kwargs,
)
from .base import BaseWorkflow, ModelTier
from .data_classes import WorkflowResult
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
from .validation import InputSchema

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

    def __init__(self, *, system_prompt_suffix: str = "", **kwargs: Any) -> None:
        """Initialize workflow.

        Args:
            system_prompt_suffix: Optional string appended to the
                orchestrator's system prompt at call time. Lets a
                wrapping caller (e.g. discovery-sweep's
                ``DependencyCheckSource``) augment the prompt at
                the workflow-INSTANCE level without mutating the
                class template. Empty string (default) preserves
                prior behavior for every other caller.
            **kwargs: Passed to BaseWorkflow.__init__().
        """
        super().__init__(**kwargs)
        self._system_prompt_suffix = system_prompt_suffix

    input_schema = InputSchema(
        optional_fields={"path": str, "depth": str, "max_budget_usd": (int, float)},
    )

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
            run_result = await self._run_agent_check(
                resolved_path, max_turns, depth, max_budget_usd=max_budget_usd
            )
            self._track_sdk_run_telemetry(stage="agent", agent_run_result=run_result)

            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                report_title="Dependency check",
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
            # INTENTIONAL: Catch-all for unknown SDK errors. Phase 2 of
            # docs/specs/sdk-error-message-fidelity/ — capture the real
            # claude CLI stderr via a second subprocess call, classify
            # it, and thread the typed fields onto
            # WorkflowResult.metadata for the dashboard to render the
            # truth instead of regex-guessing.
            logger.exception("Agent SDK dependency check failed: %s", type(exc).__name__)
            sdk_err = sdk_error_from_exception(exc)
            return self._error_result(
                sdk_err.format_user_message(),
                sdk_stderr=sdk_err.stderr,
                sdk_error_kind=sdk_err.kind,
            )

    async def _run_agent_check(
        self,
        resolved_path: str,
        max_turns: int,
        depth: str = "standard",
        max_budget_usd: float | None = None,
    ) -> AgentRunResult:
        """Run the Agent SDK dependency check and return result text.

        Args:
            resolved_path: Absolute path to the project.
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
                    allowed_tools=["Read", "Glob", "Grep", "Bash", "Agent"],
                    permission_mode="default",
                    max_turns=max_turns,
                    agents={
                        "inventory-assessor": claude_agent_sdk.AgentDefinition(
                            description=(
                                "Dependency inventory assessor that catalogs all packages."
                            ),
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
            )
        ):
            sdk_result = collect_agent_output(message, assistant_parts, result_parts)
            if sdk_result is not None:
                run_result = sdk_result
        run_result.result_text = build_result_text(assistant_parts, result_parts)
        return run_result


if __name__ == "__main__":
    main()
