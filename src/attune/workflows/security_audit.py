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
    get_max_budget_usd,
    get_subagent_model,
)
from .base import BaseWorkflow, ModelTier
from .data_classes import CostReport, WorkflowResult, WorkflowStage
from .output_schemas import WORKFLOW_OUTPUT_SCHEMA
from .security_audit_patterns import (
    DETECTION_PATTERNS,  # noqa: F401 — re-exported
    FAKE_CREDENTIAL_PATTERNS,  # noqa: F401 — re-exported
    SECURITY_EXAMPLE_PATHS,  # noqa: F401 — re-exported
    SECURITY_PATTERNS,  # noqa: F401 — re-exported
    SKIP_DIRECTORIES,  # noqa: F401 — re-exported
    TEST_FILE_PATTERNS,  # noqa: F401 — re-exported
    TEST_FIXTURE_PATTERNS,  # noqa: F401 — re-exported
)
from .security_audit_report import (
    format_security_report,  # noqa: F401 — re-exported
    main,  # noqa: F401 — re-exported
)
from .security_audit_stages import (
    SECURITY_STEPS,  # noqa: F401 — re-exported
)

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

    def __init__(self, **kwargs: Any) -> None:
        """Initialize workflow.

        Args:
            **kwargs: Passed to BaseWorkflow.__init__().
        """
        super().__init__(**kwargs)

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
        path_arg: str = kwargs.get("path", "")
        depth: str = kwargs.get("depth", "standard")

        if not path_arg:
            return self._error_result("path argument is required")

        resolved_path = str(Path(path_arg).resolve())
        max_turns = _DEPTH_MAX_TURNS.get(depth, 20)

        started_at = datetime.now()

        try:
            run_result = await self._run_agent_audit(resolved_path, max_turns, depth)
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
            # INTENTIONAL: Catch-all for unknown SDK errors to
            # return a structured WorkflowResult rather than
            # crashing the CLI.
            logger.exception(
                "Agent SDK security audit failed: %s",
                type(exc).__name__,
            )
            return self._error_result(f"Agent SDK error: {type(exc).__name__}: {exc}")

    async def _run_agent_audit(
        self, resolved_path: str, max_turns: int, depth: str = "standard"
    ) -> AgentRunResult:
        """Run the Agent SDK audit and return result text.

        Args:
            resolved_path: Absolute path to audit.
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
                allowed_tools=["Read", "Glob", "Grep", "Agent"],
                permission_mode="default",
                max_turns=max_turns,
                output_format=WORKFLOW_OUTPUT_SCHEMA,
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
        ):
            if isinstance(message, claude_agent_sdk.ResultMessage):
                result_parts.append(message.result or "")
                run_result = AgentRunResult(
                    result_text="",
                    structured_output=message.structured_output,
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
                    name="agent-audit",
                    tier=ModelTier.CAPABLE,
                    description="Agent SDK security audit",
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
