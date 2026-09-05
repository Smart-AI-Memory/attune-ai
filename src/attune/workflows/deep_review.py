"""Multi-Pass Deep Review Workflow (Agent SDK).

Runs three sequential review passes using Claude Agent SDK subagents:
1. Security pass — vulnerabilities, injection, path traversal, secrets
2. Quality pass — complexity, error handling, naming, duplication
3. Test gaps pass — untested paths, missing edge cases, coverage holes

Each pass is a dedicated subagent with read-only file access. Results
are parsed into a consolidated WorkflowResult with per-category
findings and prioritized suggestions.

Usage::

    workflow = DeepReviewAgentSDKWorkflow()
    result = await workflow.execute(path="src/", depth="deep")

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
    SdkSubprocessError,
    _last_subprocess_argv,
    build_result_text,
    capture_subprocess_failure,
    classify_subprocess_failure,
    collect_agent_output,
    get_max_budget_usd,
    get_subagent_model,
    iter_agent_messages,
    required_sections_from_prompt,
    resolve_cwd_for_path,
    sdk_isolation_kwargs,
)
from .base import BaseWorkflow, ModelTier
from .data_classes import WorkflowResult
from .validation import InputSchema

logger = logging.getLogger(__name__)


_DEPTH_MAX_TURNS: dict[str, int] = {
    "quick": 15,
    "standard": 30,
    "deep": 50,
}

_SUBAGENT_NAMES = [
    "security-reviewer",
    "quality-reviewer",
    "test-gap-reviewer",
]

_SUBAGENT_DEFS: dict[str, dict[str, str]] = {
    "security-reviewer": {
        "description": "Security specialist finding vulnerabilities and risks.",
        "prompt": (
            "You are a senior security reviewer. Thoroughly examine the "
            "code at {path} for:\n"
            "- eval()/exec() usage or code injection vectors\n"
            "- Path traversal and file system vulnerabilities\n"
            "- Hardcoded secrets, API keys, or credentials\n"
            "- SQL/command injection risks\n"
            "- Unsafe deserialization\n"
            "- Authentication and authorization flaws\n"
            "- OWASP Top 10 vulnerabilities\n\n"
            "For each finding, report:\n"
            "- **File path and line number**\n"
            "- **Severity** (CRITICAL/HIGH/MEDIUM/LOW)\n"
            "- **Description** of the vulnerability\n"
            "- **Remediation** with a concrete code fix\n\n"
            "Output your findings under a `## Security` heading."
        ),
    },
    "quality-reviewer": {
        "description": "Code quality reviewer for maintainability and standards.",
        "prompt": (
            "You are a senior code quality reviewer. Thoroughly examine "
            "the code at {path} for:\n"
            "- Excessive cyclomatic complexity (>10 per function)\n"
            "- Bare except: or overly broad exception handling\n"  # noqa: BLE001
            "- Dead code, unused imports, unreachable branches\n"
            "- Poor naming (single-letter vars, misleading names)\n"
            "- Code duplication (3+ similar blocks)\n"
            "- Missing type hints on public APIs\n"
            "- Missing or inadequate docstrings\n"
            "- Functions exceeding 50 lines\n\n"
            "For each finding, report:\n"
            "- **File path and line number**\n"
            "- **Severity** (HIGH/MEDIUM/LOW)\n"
            "- **Description** of the issue\n"
            "- **Suggestion** with a concrete improvement\n\n"
            "Output your findings under a `## Quality` heading."
        ),
    },
    "test-gap-reviewer": {
        "description": "Test coverage analyzer finding untested code paths.",
        "prompt": (
            "You are a senior test engineer. Thoroughly examine the "
            "code at {path} and its corresponding tests to find:\n"
            "- Public functions/methods with no test coverage\n"
            "- Error handling paths that are never tested\n"
            "- Edge cases not covered (empty input, None, boundaries)\n"
            "- Missing integration tests for key workflows\n"
            "- Mocked dependencies that hide real bugs\n"
            "- Test assertions that are too weak (assertTrue vs assertEqual)\n\n"
            "For each finding, report:\n"
            "- **Source file and function** that needs testing\n"
            "- **Gap type** (no test / missing edge case / weak assertion)\n"
            "- **Priority** (HIGH/MEDIUM/LOW)\n"
            "- **Suggested test** with a brief code sketch\n\n"
            "Output your findings under a `## Test Gaps` heading."
        ),
    },
}

_SYSTEM_PROMPT = """\
You are a senior code review orchestrator performing a multi-pass deep \
review. You coordinate three specialized subagents to produce a \
consolidated code review report. Be thorough but concise. Cite file \
paths and line numbers.\
"""

_TASK_PROMPT_TEMPLATE = """\
Review the codebase at {path} using the three specialized subagents \
below. Each subagent focuses on a specific domain and will report \
findings independently.

After all subagents finish, synthesize their findings into a single \
consolidated report with these sections:

## Summary
Overall code health score (0-100) and a 2-3 sentence executive summary. \
Include counts of findings by severity.

## Security
Findings from the security reviewer, ordered by severity.

## Quality
Findings from the quality reviewer, ordered by severity.

## Test Gaps
Findings from the test gap reviewer, ordered by priority.

## Suggestions
Top 5-10 actionable next steps ordered by impact. Each suggestion \
should reference the specific finding it addresses.\
"""

# Derived from the prompt above, never restated — the prompt IS
# the output contract, and a run that omits one of these sections
# is a failure, not a quiet exit-0 (see _check_section_contract).
_REQUIRED_SECTIONS = required_sections_from_prompt(_TASK_PROMPT_TEMPLATE)


class DeepReviewAgentSDKWorkflow(BaseWorkflow):
    """Multi-pass deep code review using Claude Agent SDK subagents.

    Runs three review passes (security, quality, test gaps) as
    independent subagents, each with read-only file access. The
    orchestrator synthesizes findings into a consolidated report
    with severity-ordered findings and prioritized suggestions.

    Usage::

        workflow = DeepReviewAgentSDKWorkflow()
        result = await workflow.execute(path="src/", depth="standard")
    """

    name = "deep-review"
    description = (
        "Multi-pass deep review with 3 specialized subagents (security, quality, test gaps)"
    )
    stages = ["deep-review"]
    tier_map = {"deep-review": ModelTier.CAPABLE}

    input_schema = InputSchema(
        optional_fields={"path": str, "depth": str, "focus": list},
    )

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the multi-pass deep review.

        Args:
            **kwargs: Keyword arguments.
                path (str): Required. Directory or file to review.
                depth (str): Review depth — "quick", "standard",
                    or "deep". Defaults to "standard".
                focus (list[str]): Optional. Subset of passes to run.
                    Valid values: "security", "quality", "test-gaps".
                    Defaults to all three.

        Returns:
            WorkflowResult with findings, suggestions, and metadata.
        """
        self.validate_input(kwargs)
        path_arg: str = kwargs.get("path", "")
        depth: str = kwargs.get("depth", "standard")
        focus: list[str] | None = kwargs.get("focus")

        if not path_arg:
            return self._error_result("path argument is required")

        resolved_path = str(Path(path_arg).resolve())
        max_turns = _DEPTH_MAX_TURNS.get(depth, 30)

        # Filter subagents by focus if specified
        active_agents = _SUBAGENT_NAMES
        if focus:
            valid_focus = {"security", "quality", "test-gaps"}
            focus_map = {
                "security": "security-reviewer",
                "quality": "quality-reviewer",
                "test-gaps": "test-gap-reviewer",
            }
            active_agents = [focus_map[f] for f in focus if f in valid_focus]
            if not active_agents:
                return self._error_result(f"Invalid focus values. Valid: {', '.join(valid_focus)}")

        started_at = datetime.now()

        try:
            run_result = await self._run_deep_review(resolved_path, max_turns, active_agents, depth)
            self._track_sdk_run_telemetry(stage="agent", agent_run_result=run_result)

            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                report_title="Deep review",
                required_sections=_REQUIRED_SECTIONS,
                result_text=run_result.result_text,
                subagent_names=active_agents,
                started_at=started_at,
                completed_at=completed_at,
                metadata={
                    "path": resolved_path,
                    "depth": depth,
                    "max_turns": max_turns,
                    "focus": focus or ["security", "quality", "test-gaps"],
                    "workflow": "deep-review",
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
            # of docs/specs/sdk-error-message-fidelity/ — the exact
            # workflow Patrick hit 2026-06-01 with a 401 auth failure
            # that the legacy three-cause menu mis-attributed.
            logger.exception("Deep review failed: %s", type(exc).__name__)
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

    async def _run_deep_review(
        self,
        resolved_path: str,
        max_turns: int,
        active_agents: list[str],
        depth: str = "standard",
    ) -> AgentRunResult:
        """Run the Agent SDK deep review and return result text.

        Args:
            resolved_path: Absolute path to review.
            max_turns: Maximum agent turns.
            active_agents: List of subagent names to activate.

        Returns:
            AgentRunResult with findings and SDK metadata.
        """
        agents = {}
        for agent_name in active_agents:
            defn = _SUBAGENT_DEFS[agent_name]
            agents[agent_name] = claude_agent_sdk.AgentDefinition(
                description=defn["description"],
                prompt=defn["prompt"].format(path=resolved_path),
                tools=["Read", "Glob", "Grep"],
                model=get_subagent_model(agent_name),
            )

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
                    allowed_tools=["Read", "Glob", "Grep", "Agent"],
                    permission_mode="default",
                    max_turns=max_turns,
                    agents=agents,
                ),
            )
        ):
            sdk_result = collect_agent_output(message, assistant_parts, result_parts)
            if sdk_result is not None:
                run_result = sdk_result
        run_result.result_text = build_result_text(assistant_parts, result_parts)
        return run_result
