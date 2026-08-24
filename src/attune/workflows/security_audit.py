"""Security Audit Workflow — Agent SDK Native.

Delegates security auditing to four specialized Claude Agent SDK
subagents (vuln-scanner, secret-detector, auth-reviewer,
remediation-planner) and synthesizes their findings into a unified
WorkflowResult.

Prior to v4.2.0 this was a mixin-based multi-stage pipeline. The
SDK-native implementation replaces that with `claude_agent_sdk.query()`
and `AgentDefinition` subagents while preserving the same public
interface (`SecurityAuditWorkflow`, `security-audit` slug) and
re-exports used by downstream code.

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

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
from .validation import InputSchema

logger = logging.getLogger(__name__)

# Depth → max agent turns mapping
_DEPTH_MAX_TURNS: dict[str, int] = {
    "quick": 10,
    "standard": 20,
    "deep": 40,
}

_SUBAGENT_NAMES = [
    "vuln-scanner",
    "secret-detector",
    "auth-reviewer",
    "remediation-planner",
]

_SYSTEM_PROMPT = """\
You are a senior security audit orchestrator. You coordinate four \
specialized subagents to produce a unified security audit report. \
Be thorough but concise. Cite file paths and line numbers when possible.\
"""

_TASK_PROMPT_TEMPLATE = """\
Audit the codebase at {path} using the four specialized subagents \
below. Each subagent should focus on its domain and report findings \
as structured markdown.

After all subagents finish, synthesize their findings into a single \
report with these sections:

## Summary
Overall security score (0-100) and a 2-3 sentence executive summary \
of the security posture.

## Security
Consolidated findings from all subagents organized by severity \
(CRITICAL, HIGH, MEDIUM, LOW).

## Suggestions
Actionable remediation steps ordered by priority, with estimated \
effort for each fix.\
"""


class SecurityAuditWorkflow(BaseWorkflow):
    """SDK-native security audit with four specialized subagents.

    Delegates all analysis to Claude Agent SDK subagents:
    - **vuln-scanner** — injection flaws, eval/exec, XSS, path traversal
    - **secret-detector** — hardcoded credentials, API keys, tokens
    - **auth-reviewer** — authentication/authorization issues
    - **remediation-planner** — prioritized fix plan

    The orchestrator synthesizes findings into a unified report.

    Usage::

        workflow = SecurityAuditWorkflow()
        result = await workflow.execute(path="src/", depth="standard")
    """

    name = "security-audit"
    description = "Agent SDK-powered security audit with 4 specialized subagents"
    stages = ["agent-audit"]
    tier_map = {"agent-audit": ModelTier.CAPABLE}

    def __init__(self, *, system_prompt_suffix: str = "", **kwargs: Any) -> None:
        """Initialize workflow.

        Args:
            system_prompt_suffix: Optional string appended to the
                orchestrator's system prompt at call time. Lets a
                wrapping caller (e.g. discovery-sweep's
                ``SecurityAuditSource``) augment the prompt at the
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
        """Execute the Agent SDK security audit.

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
                resolved_path, max_turns, depth, max_budget_usd=max_budget_usd
            )
            self._track_sdk_run_telemetry(stage="agent", agent_run_result=run_result)
            completed_at = datetime.now()

            # Recover per-subagent findings from the session transcript
            # so the orchestrator's synthesis is no longer a single point
            # of data loss. See: 6.2.0 spec feature-agent-sdk-0163-uplift
            # task #1, and the "SDK adapter swallows subagent findings"
            # lesson in .claude/CLAUDE.md.
            transcripts = await collect_subagent_transcripts(run_result.session_id)
            rendered_transcripts = format_subagent_transcripts_markdown(transcripts)
            if rendered_transcripts:
                base_text = run_result.result_text or ""
                run_result.result_text = (
                    f"{base_text}\n\n## Subagent findings\n\n{rendered_transcripts}"
                    if base_text and base_text != "No results returned."
                    else f"## Subagent findings\n\n{rendered_transcripts}"
                )

            return AgentSDKResultAdapter.from_agent_output(
                report_title="Security audit",
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
            # crashing the CLI. Phase 4 of
            # docs/specs/sdk-error-message-fidelity/ — capture +
            # classify the real claude CLI stderr instead of
            # showing the legacy three-cause menu.
            logger.exception(
                "Agent SDK security audit failed: %s",
                type(exc).__name__,
            )
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

        Returns:
            AgentRunResult with findings and SDK metadata.
        """
        assistant_parts: list[str] = []
        result_parts: list[str] = []
        run_result = AgentRunResult(result_text="No results returned.")

        # Token-aware budget (SDK 0.1.51+): the model sees remaining
        # budget and paces itself instead of getting cut mid-exploration.
        # Deep runs additionally engage extended thinking for richer
        # architecture / remediation-planner output. See 6.2.0 spec
        # task #2.
        extra_opts: dict[str, Any] = {}
        if (task_budget := get_task_budget(depth)) is not None:
            extra_opts["task_budget"] = task_budget
        if (thinking := get_thinking_config(depth)) is not None:
            extra_opts["thinking"] = thinking
            extra_opts["effort"] = "high"

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
                    output_format=WORKFLOW_OUTPUT_SCHEMA,
                    **extra_opts,
                    agents={
                        "vuln-scanner": claude_agent_sdk.AgentDefinition(
                            description=("Vulnerability scanner that finds " "injection flaws."),
                            prompt=(
                                "You are a vulnerability scanner. Focus "
                                "on: eval/exec usage, SQL injection, "
                                "XSS, path traversal, command injection, "
                                "and insecure deserialization. Report "
                                "each finding with file path, line "
                                "number, severity (CRITICAL/HIGH/MEDIUM/"
                                "LOW), and remediation advice."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("vuln-scanner"),
                        ),
                        "secret-detector": claude_agent_sdk.AgentDefinition(
                            description=("Secret detector that finds hardcoded " "credentials."),
                            prompt=(
                                "You are a secret detector. Focus on: "
                                "hardcoded API keys, passwords, tokens, "
                                "private keys, database credentials, and "
                                "sensitive environment variables "
                                "committed to source. Report each "
                                "finding with file path, line number, "
                                "secret type, and how to externalize it "
                                "securely."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("secret-detector"),
                        ),
                        "auth-reviewer": claude_agent_sdk.AgentDefinition(
                            description=("Auth reviewer for authentication and " "authorization."),
                            prompt=(
                                "You are an authentication and "
                                "authorization reviewer. Focus on: "
                                "missing auth checks, broken access "
                                "control, insecure session management, "
                                "weak password policies, and privilege "
                                "escalation risks. Report each finding "
                                "with file path, severity, and "
                                "remediation advice."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("auth-reviewer"),
                        ),
                        "remediation-planner": claude_agent_sdk.AgentDefinition(
                            description=("Remediation planner that prioritizes " "findings."),
                            prompt=(
                                "You are a remediation planner. Review "
                                "all findings from other subagents and "
                                "create a prioritized remediation plan. "
                                "Group fixes by effort (quick wins, "
                                "medium effort, major refactors). "
                                "Estimate time for each fix and identify "
                                "dependencies between remediations."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("remediation-planner"),
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
