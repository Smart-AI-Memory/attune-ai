"""Code Review Workflow — Agent SDK Native.

Delegates code review to four specialized Claude Agent SDK subagents
(security, quality, performance, architecture) and synthesizes their
findings into a unified WorkflowResult.

Prior to v4.2.0 this was a mixin-based multi-stage pipeline that made
direct LLM calls. The SDK-native implementation replaces that with
`claude_agent_sdk.query()` and `AgentDefinition` subagents while
preserving the same public interface (`CodeReviewWorkflow`, `code-review`
slug) and re-exports used by downstream code.

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import claude_agent_sdk

from .agent_sdk_adapter import (
    AgentRunResult,
    AgentSDKResultAdapter,
    build_result_text,
    collect_agent_output,
    collect_subagent_transcripts,
    format_subagent_transcripts_markdown,
    get_max_budget_usd,
    get_subagent_model,
    get_task_budget,
    get_thinking_config,
    iter_agent_messages,
    resolve_cwd_for_path,
    sdk_error_from_exception,
    sdk_isolation_kwargs,
)
from .base import BaseWorkflow, ModelTier
from .data_classes import WorkflowResult
from .output_schemas import WORKFLOW_OUTPUT_SCHEMA
from .step_config import WorkflowStepConfig
from .validation import InputSchema

logger = logging.getLogger(__name__)

# Depth → max agent turns mapping
_DEPTH_MAX_TURNS: dict[str, int] = {
    "quick": 10,
    "standard": 20,
    "deep": 40,
}

_SUBAGENT_NAMES = [
    "security-reviewer",
    "quality-reviewer",
    "perf-reviewer",
    "architect-reviewer",
]

# Phase 5.4 — When the synthesized review mentions any of these terms,
# emit an ATTUNE_REC recommending a bug-predict run on the same scope.
# Picked as terms that signal "this finding is worth a deeper look,"
# not "any incidental security mention." The regex is case-insensitive
# and word-bounded to avoid matching code that just imports something
# named "injection" or "xss". A single hit on any term triggers one
# recommendation per run (the runner caps at 50 anyway).
_SECURITY_TRIGGERS = re.compile(
    r"\b(CWE-\d+|CVE-\d+|"
    r"sql\s*injection|command\s*injection|path\s*traversal|"
    r"xss|cross[- ]site\s*scripting|csrf|"
    r"hardcoded\s*(secret|credential|password|token|api\s*key)|"
    r"insecure\s*(deserializ|random)|"
    r"eval\(|exec\()",
    re.IGNORECASE,
)


def _emit_security_recommendation_if_warranted(
    result_text: str | None,
    scope_path: str,
    *,
    output_stream: Any = None,
) -> bool:
    """Print an ``ATTUNE_REC`` line to stdout when the review surfaces
    security-shaped findings.

    Suggests running ``bug-predict`` on the same scope — bug-predict's
    pattern scanner catches eval/exec/path-traversal that code-review
    might call out narratively without locating the exact line. The
    two workflows complement each other: code-review reads, bug-predict
    pinpoints. The runner parses ``ATTUNE_REC`` markers on the SSE
    channel and renders an action card on the run-view page (Phase 5
    infrastructure, PR #413).

    Args:
        result_text: The synthesized review output. ``None`` / empty
            skips emission.
        scope_path: The ``--path`` that code-review ran against; passed
            through to bug-predict so the recommendation lands on the
            same files.
        output_stream: Stream to print to. Defaults to ``sys.stdout``
            so the runner's stdout reader captures it. Override in
            tests to capture without monkeypatching.

    Returns:
        True iff a recommendation was emitted. Useful for tests + as
        a signal for upstream telemetry hooks.
    """
    if not result_text or not scope_path:
        return False
    if not _SECURITY_TRIGGERS.search(result_text):
        return False
    payload: dict[str, Any] = {
        "kind": "next-workflow",
        "name": "bug-predict",
        "args": {"path": scope_path},
        "label": "Run bug-predict to locate the specific lines",
        "severity": "high",
    }
    stream = output_stream if output_stream is not None else sys.stdout
    print("ATTUNE_REC " + json.dumps(payload), file=stream, flush=True)
    return True


_SYSTEM_PROMPT = """\
You are a senior code review orchestrator. You coordinate four \
specialized subagents to produce a unified code review report. \
Be thorough but concise. Cite file paths and line numbers when possible.\
"""

_TASK_PROMPT_TEMPLATE = """\
Review the codebase at {path} using the four specialized subagents \
below. Each subagent should focus on its domain and report findings \
as structured markdown.

After all subagents finish, synthesize their findings into a single \
report with these sections:

## Summary
Overall code health score (0-100) and a 2-3 sentence executive summary.

## Security
Findings from the security reviewer.

## Quality
Findings from the quality reviewer.

## Performance
Findings from the performance reviewer.

## Architecture
Findings from the architecture reviewer.

## Suggestions
Actionable next steps ordered by priority.\
"""

# Kept for backward compatibility — consumed by tests and step executor
CODE_REVIEW_STEPS = {
    "architect_review": WorkflowStepConfig(
        name="architect_review",
        task_type="architectural_decision",
        tier_hint="premium",
        description="Comprehensive architectural code review",
        max_tokens=3000,
    ),
}


class CodeReviewWorkflow(BaseWorkflow):
    """SDK-native code review with four specialized subagents.

    Delegates all analysis to Claude Agent SDK subagents:
    - **security-reviewer** — injection, path traversal, secrets
    - **quality-reviewer** — complexity, error handling, duplication
    - **perf-reviewer** — N+1, blocking I/O, unnecessary copies
    - **architect-reviewer** — coupling, SOLID, circular deps

    The orchestrator synthesizes findings into a unified report.

    Usage::

        workflow = CodeReviewWorkflow()
        result = await workflow.execute(path="src/", depth="standard")
    """

    name = "code-review"
    description = "Agent SDK-powered code review with 4 specialized subagents"
    stages = ["agent-review"]
    tier_map = {"agent-review": ModelTier.CAPABLE}

    def __init__(self, **kwargs: Any) -> None:
        """Initialize workflow.

        Args:
            **kwargs: Passed to BaseWorkflow.__init__().
        """
        super().__init__(**kwargs)

    input_schema = InputSchema(
        optional_fields={"path": str, "depth": str},
    )

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK code review.

        Args:
            **kwargs: Keyword arguments.
                path (str): Required. Directory or file to review.
                depth (str): Review depth — "quick", "standard",
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
            run_result = await self._run_agent_review(resolved_path, max_turns, depth)
            self._track_sdk_run_telemetry(stage="agent", agent_run_result=run_result)
            completed_at = datetime.now()

            # Recover per-subagent transcripts so reviewer findings
            # from each pass are preserved even when the orchestrator
            # synthesizes tersely or hits the budget cap. See 6.2.0
            # spec feature-agent-sdk-0163-uplift task #1.
            transcripts = await collect_subagent_transcripts(run_result.session_id)
            rendered_transcripts = format_subagent_transcripts_markdown(transcripts)
            if rendered_transcripts:
                base_text = run_result.result_text or ""
                run_result.result_text = (
                    f"{base_text}\n\n## Subagent findings\n\n{rendered_transcripts}"
                    if base_text and base_text != "No results returned."
                    else f"## Subagent findings\n\n{rendered_transcripts}"
                )

            # Phase 5.4 — emit an ATTUNE_REC marker when the synthesized
            # review surfaces security/CWE-shaped findings, suggesting
            # a bug-predict run on the same scope. The ops dashboard's
            # runner parses this and renders an action card.
            _emit_security_recommendation_if_warranted(run_result.result_text, resolved_path)

            return AgentSDKResultAdapter.from_agent_output(
                report_title="Code review",
                result_text=run_result.result_text,
                subagent_names=_SUBAGENT_NAMES,
                started_at=started_at,
                completed_at=completed_at,
                metadata={
                    "path": resolved_path,
                    "depth": depth,
                    "max_turns": max_turns,
                    "subagent_transcripts": transcripts,
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
            # INTENTIONAL: Catch-all for unknown SDK errors to
            # return a structured WorkflowResult rather than
            # crashing the CLI. Phase 2 of
            # docs/specs/sdk-error-message-fidelity/ — capture the
            # real claude CLI stderr via a second subprocess call,
            # classify it into a known kind, and thread the typed
            # fields onto WorkflowResult.metadata so the dashboard
            # can render the truth instead of regex-guessing.
            logger.exception(
                "Agent SDK code review failed: %s",
                type(exc).__name__,
            )
            sdk_err = sdk_error_from_exception(exc)
            return self._error_result(
                sdk_err.format_user_message(),
                sdk_stderr=sdk_err.stderr,
                sdk_error_kind=sdk_err.kind,
            )

    async def _run_agent_review(
        self, resolved_path: str, max_turns: int, depth: str = "standard"
    ) -> AgentRunResult:
        """Run the Agent SDK review and return result text.

        Args:
            resolved_path: Absolute path to review.
            max_turns: Maximum agent turns.

        Returns:
            AgentRunResult with findings and SDK metadata.
        """
        assistant_parts: list[str] = []
        result_parts: list[str] = []
        run_result = AgentRunResult(result_text="No results returned.")

        # See security_audit._run_agent_audit for rationale.
        extra_opts: dict[str, Any] = {}
        if (task_budget := get_task_budget(depth)) is not None:
            extra_opts["task_budget"] = task_budget
        if (thinking := get_thinking_config(depth)) is not None:
            extra_opts["thinking"] = thinking
            extra_opts["effort"] = "high"

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
                    output_format=WORKFLOW_OUTPUT_SCHEMA,
                    **extra_opts,
                    agents={
                        "security-reviewer": claude_agent_sdk.AgentDefinition(
                            description=("Security reviewer that finds " "vulnerabilities."),
                            prompt=(
                                "You are a security reviewer. Focus on: "
                                "eval/exec usage, injection "
                                "vulnerabilities, path traversal, "
                                "hardcoded secrets, and authentication "
                                "issues. Report each finding with file "
                                "path, line number, severity, and "
                                "remediation advice."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("security-reviewer"),
                        ),
                        "quality-reviewer": claude_agent_sdk.AgentDefinition(
                            description=("Code quality reviewer for standards " "and patterns."),
                            prompt=(
                                "You are a code quality reviewer. Focus "
                                "on: code complexity, error handling "
                                "patterns, naming conventions, "
                                "duplication, and test coverage gaps. "
                                "Report each finding with file path, "
                                "severity, and improvement advice."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("quality-reviewer"),
                        ),
                        "perf-reviewer": claude_agent_sdk.AgentDefinition(
                            description=(
                                "Performance reviewer for bottlenecks " "and inefficiencies."
                            ),
                            prompt=(
                                "You are a performance reviewer. Focus "
                                "on: N+1 patterns, unnecessary list "
                                "copies, blocking I/O in async code, "
                                "and missing caching opportunities. "
                                "Report each finding with file path, "
                                "estimated impact, and fix."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("perf-reviewer"),
                        ),
                        "architect-reviewer": claude_agent_sdk.AgentDefinition(
                            description=(
                                "Architecture reviewer for design and " "coupling issues."
                            ),
                            prompt=(
                                "You are an architecture reviewer. "
                                "Focus on: coupling between modules, "
                                "SOLID violations, circular "
                                "dependencies, API design issues, and "
                                "abstraction level mismatches. Report "
                                "each finding with affected modules "
                                "and refactoring suggestions."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("architect-reviewer"),
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
