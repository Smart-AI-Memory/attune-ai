"""Fix workflow — minimal in-place source edit within scope.

Phase 2 of docs/specs/outcome-first-fix/ (decisions.md D5): the ONE
fix-capable workflow, registered in the existing registry and
executed by the existing Agent SDK adapter. The agent may Edit only
inside the contract's scope paths — enforced at tool-call time by a
PreToolUse guard (prevention) and re-checked by the CLI's receipt
against a pre-run baseline (detection).

The workflow's own exit/result NEVER proves the fix worked: the CLI
evaluates the contract's verification probes independently and
computes the receipt (spec H2).
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
    iter_agent_messages,
    make_edit_scope_guard,
    resolve_cwd_for_path,
    sdk_isolation_kwargs,
)
from .base import BaseWorkflow, ModelTier
from .data_classes import WorkflowResult
from .validation import InputSchema

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a surgical bug fixer. Make the SMALLEST in-place edit "
    "that satisfies the stated done conditions. Never edit test "
    "files, never add files, never refactor beyond the fix. If the "
    "fix is ambiguous, stop and report the ambiguity instead of "
    "guessing."
)

_TASK_PROMPT_TEMPLATE = """Fix request: {goal}

Scope — you may ONLY edit these paths (edits elsewhere are denied):
{scope_lines}

Done conditions (verified independently after you finish — do NOT
run tests yourself):
{done_lines}

Read the scoped files, make the minimal in-place edit, then reply
with a short summary listing exactly which files you changed and
what remains uncertain."""


class FixWorkflow(BaseWorkflow):
    """Apply a minimal in-place fix within scope (outcome-first-fix).

    Usage::

        workflow = FixWorkflow()
        result = await workflow.execute(
            goal="make the boundary order bulk",
            scope_paths=["src/pricing.py"],
            done_conditions=["probe passes: pytest ..."],
        )
    """

    name = "fix"
    description = "Apply a minimal in-place fix within the contract's scope"
    stages = ["agent-fix"]
    tier_map = {"agent-fix": ModelTier.CAPABLE}

    input_schema = InputSchema(
        required_fields={"goal": str, "scope_paths": list},
        optional_fields={"done_conditions": list},
    )

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Run the scoped fix agent.

        Args:
            **kwargs: goal (str, required); scope_paths (list[str],
                required, non-empty); done_conditions (list[str]);
                depth (str, default "standard").

        Returns:
            WorkflowResult; ``metadata["agent_reported_changes"]`` is
            advisory — the CLI receipt trusts the baseline diff, not
            the agent's claim.
        """
        goal: str = kwargs.get("goal", "")
        scope_raw = kwargs.get("scope_paths", []) or []
        # The ops runner rewrites `--path` into this kwarg as a bare
        # string (PATH_ARG_REGISTRY); iterating a str would yield one
        # Path per CHARACTER, so normalize before use.
        if isinstance(scope_raw, str):
            scope_raw = [scope_raw]
        done_conditions: list[str] = kwargs.get("done_conditions", []) or []
        depth: str = kwargs.get("depth", "standard")

        if not goal:
            return self._error_result("goal argument is required")
        if not scope_raw:
            return self._error_result("scope_paths is required — an unscoped fix is not runnable")

        scope_paths = [Path(p) for p in scope_raw]
        started_at = datetime.now()

        try:
            run_result = await self._run_agent_fix(goal, scope_paths, done_conditions, depth)
            self._track_sdk_run_telemetry(stage="agent", agent_run_result=run_result)
            return AgentSDKResultAdapter.from_agent_output(
                report_title="Scoped fix",
                result_text=run_result.result_text,
                subagent_names=[],
                started_at=started_at,
                completed_at=datetime.now(),
                metadata={
                    "goal": goal,
                    "scope_paths": [str(p) for p in scope_paths],
                    "agent_reported_changes": run_result.result_text,
                },
                agent_run_result=run_result,
            )
        except ImportError as exc:
            logger.error("Agent SDK import failed: %s", exc)
            return self._error_result(f"Agent SDK unavailable: {exc}")
        except (ConnectionError, TimeoutError) as exc:
            logger.error("Agent SDK network error: %s", exc)
            return self._error_result(f"Agent SDK connection failed: {exc}")

    async def _run_agent_fix(
        self,
        goal: str,
        scope_paths: list[Path],
        done_conditions: list[str],
        depth: str,
    ) -> AgentRunResult:
        """Run the scoped single-agent fix session."""
        iso = sdk_isolation_kwargs()
        iso["hooks"]["PreToolUse"] = [
            *iso["hooks"]["PreToolUse"],
            claude_agent_sdk.HookMatcher(
                matcher="Edit", hooks=[make_edit_scope_guard(scope_paths)]
            ),
            claude_agent_sdk.HookMatcher(
                matcher="Write", hooks=[make_edit_scope_guard(scope_paths)]
            ),
        ]
        scope_lines = "\n".join(f"- {p}" for p in scope_paths)
        done_lines = "\n".join(f"- {c}" for c in done_conditions) or "- (none stated)"

        assistant_parts: list[str] = []
        result_parts: list[str] = []
        run_result = AgentRunResult(result_text="No results returned.")
        async for message in iter_agent_messages(
            claude_agent_sdk.query(
                prompt=_TASK_PROMPT_TEMPLATE.format(
                    goal=goal, scope_lines=scope_lines, done_lines=done_lines
                ),
                options=claude_agent_sdk.ClaudeAgentOptions(
                    **iso,
                    system_prompt=_SYSTEM_PROMPT,
                    cwd=resolve_cwd_for_path(scope_paths[0]),
                    max_budget_usd=get_max_budget_usd(depth),
                    allowed_tools=["Read", "Glob", "Grep", "Edit"],
                    permission_mode="acceptEdits",
                    max_turns=20,
                ),
            )
        ):
            sdk_result = collect_agent_output(message, assistant_parts, result_parts)
            if sdk_result is not None:
                run_result = sdk_result
        run_result.result_text = build_result_text(assistant_parts, result_parts)
        return run_result
