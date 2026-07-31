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

__all__ = [
    "ReleasePreparationWorkflow",
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
    """Release-notes draft + readiness advisory, powered by Agent SDK subagents.

    Delegates all analysis to four Agent SDK subagents rather than
    using the mixin stage system. Each subagent focuses on a specific
    release-readiness domain (health, security, changelog, assessment),
    and the orchestrator synthesizes a draft changelog plus an LLM
    go/no-go recommendation.

    This is the *advisory* release workflow — it predicts and drafts; it
    does not enforce hard quality gates. The deterministic gate (real
    bandit/ruff/pytest with pass/fail thresholds) is the separate
    ``release-prep`` agent team (``ReleasePrepTeamWorkflow``).

    Usage::

        workflow = ReleasePreparationWorkflow()
        result = await workflow.execute(path=".", depth="standard")
    """

    name = "release-notes"
    description = "Draft release notes + LLM readiness advice (Agent SDK subagents)"
    stages = ["agent-prep"]
    tier_map = {"agent-prep": ModelTier.CAPABLE}

    input_schema = InputSchema(
        optional_fields={"path": str, "depth": str},
    )

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
        self.validate_input(kwargs)
        path_arg: str = kwargs.get("path", "")
        depth: str = kwargs.get("depth", "standard")

        if not path_arg:
            return self._error_result("path argument is required")

        resolved_path = str(Path(path_arg).resolve())
        max_turns = _DEPTH_MAX_TURNS.get(depth, 20)

        started_at = datetime.now()

        try:
            run_result = await self._run_agent_prep(resolved_path, max_turns, depth=depth)
            self._track_sdk_run_telemetry(stage="agent", agent_run_result=run_result)

            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                report_title="Release preparation",
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
            # a structured WorkflowResult rather than crashing. Phase 5
            # of docs/specs/sdk-error-message-fidelity/.
            logger.exception("Agent SDK release prep failed: %s", type(exc).__name__)
            stderr = capture_subprocess_failure(_last_subprocess_argv(exc))
            kind, summary = classify_subprocess_failure(stderr)
            sdk_err = SdkSubprocessError(
                message=summary, stderr=stderr, kind=kind, original_exc=exc
            )
            return self._error_result(
                sdk_err.format_user_message(),
                sdk_stderr=stderr,
                sdk_error_kind=kind,
            )

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
        assistant_parts: list[str] = []
        result_parts: list[str] = []
        run_result = AgentRunResult(result_text="No results returned.")
        async for message in iter_agent_messages(
            claude_agent_sdk.query(
                prompt=_TASK_PROMPT_TEMPLATE.format(path=resolved_path),
                options=claude_agent_sdk.ClaudeAgentOptions(
                    **sdk_isolation_kwargs(),
                    system_prompt=_SYSTEM_PROMPT,
                    cwd=resolve_cwd_for_path(resolved_path),
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
            )
        ):
            sdk_result = collect_agent_output(message, assistant_parts, result_parts)
            if sdk_result is not None:
                run_result = sdk_result
        run_result.result_text = build_result_text(assistant_parts, result_parts)
        return run_result
