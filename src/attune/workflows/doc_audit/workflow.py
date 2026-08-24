"""DocAuditWorkflow — Documentation accuracy audit and gap filling.

Delegates a full documentation audit to the Claude Agent SDK, using three
specialized subagents (staleness-checker, accuracy-reviewer, gap-finder)
and synthesizing their findings into a unified WorkflowResult.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import claude_agent_sdk

from ..agent_sdk_adapter import (
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
from ..base import BaseWorkflow, ModelTier
from ..data_classes import WorkflowResult
from ..validation import InputSchema
from .checks import CheckResult, run_all_checks  # noqa: F401  # re-export

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

_SYSTEM_PROMPT = """\
You are a senior documentation audit orchestrator. Coordinate three \
specialized subagents to audit documentation and synthesize their \
findings into a single structured report. Be thorough but concise. \
Cite file paths and line numbers when possible.\
"""

_TASK_PROMPT_TEMPLATE = """\
Audit the documentation at {path} using the three specialized \
subagents below. Each subagent should focus on its domain and report \
findings as structured markdown.

After all subagents finish, synthesize their findings into a single \
report with these sections:

## Summary
Overall documentation health score (0-100) and a 2-3 sentence executive summary.

## Documentation
Consolidated findings from all three reviewers organized by severity.

## Suggestions
Actionable next steps ordered by priority.\
"""


class DocAuditWorkflow(BaseWorkflow):
    """Documentation accuracy audit and gap filling workflow.

    Delegates all analysis to three Agent SDK subagents rather
    than using the mixin stage system. Each subagent focuses on
    a specific audit domain (staleness, accuracy, gaps). The
    orchestrator synthesizes findings into a unified report.

    Usage::

        workflow = DocAuditWorkflow()
        result = await workflow.execute(path="docs/", depth="standard")

    """

    name = "doc-audit"
    description = "Audit existing docs for staleness, broken links, and drift (validation)"
    stages = ["agent-audit"]
    tier_map = {"agent-audit": ModelTier.CAPABLE}

    def __init__(self, *, system_prompt_suffix: str = "", **kwargs: Any) -> None:
        """Initialize workflow.

        Args:
            system_prompt_suffix: Optional string appended to the
                orchestrator's system prompt at call time. Lets a
                wrapping caller (e.g. discovery-sweep's
                ``DocAuditSource``) augment the prompt at the
                workflow-INSTANCE level without mutating the class
                template. Empty string (default) preserves prior
                behavior for every other caller.
            **kwargs: Passed to BaseWorkflow.__init__().
        """
        super().__init__(**kwargs)
        self._system_prompt_suffix = system_prompt_suffix

    input_schema = InputSchema(
        optional_fields={"path": str, "depth": str, "max_budget_usd": (int, float)},
    )

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
            run_result = await self._run_agent_audit(
                resolved_path, max_turns, depth=depth, max_budget_usd=max_budget_usd
            )
            self._track_sdk_run_telemetry(stage="agent", agent_run_result=run_result)

            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                report_title="Documentation audit",
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
            # a structured WorkflowResult rather than crashing. Phase 6
            # of docs/specs/sdk-error-message-fidelity/.
            logger.exception("Agent SDK doc audit failed: %s", type(exc).__name__)
            sdk_err = sdk_error_from_exception(exc)
            return self._error_result(
                sdk_err.format_user_message(),
                sdk_stderr=sdk_err.stderr,
                sdk_error_kind=sdk_err.kind,
            )

    async def _run_agent_audit(
        self,
        resolved_path: str,
        max_turns: int,
        depth: str = "standard",
        max_budget_usd: float | None = None,
    ) -> AgentRunResult:
        """Run the Agent SDK audit and return result text.

        Args:
            resolved_path: Absolute path to audit.
            max_turns: Maximum agent turns.
            depth: Agent depth for budget calculation.

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
                            model=get_subagent_model("staleness-checker"),
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
                            model=get_subagent_model("accuracy-reviewer"),
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
                            model=get_subagent_model("gap-finder"),
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
