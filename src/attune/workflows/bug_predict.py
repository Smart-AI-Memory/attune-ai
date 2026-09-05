"""Bug Prediction Workflow — Agent SDK Native.

Delegates bug prediction to three specialized Claude Agent SDK
subagents (pattern-scanner, risk-correlator, prevention-advisor)
and synthesizes their findings into a unified WorkflowResult.

Prior to v4.2.0 this was a mixin-based multi-stage pipeline. The
SDK-native implementation replaces that with `claude_agent_sdk.query()`
and `AgentDefinition` subagents while preserving the same public
interface (`BugPredictionWorkflow`, `bug-predict` slug) and
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
from .bug_predict_patterns import (
    _has_problematic_exception_handlers,  # noqa: F401 — re-exported
    _is_acceptable_broad_exception,  # noqa: F401 — re-exported
    _is_dangerous_eval_usage,  # noqa: F401 — re-exported
    _is_security_policy_line,  # noqa: F401 — re-exported
    _load_bug_predict_config,  # noqa: F401 — re-exported
    _remove_docstrings,  # noqa: F401 — re-exported
    _should_exclude_file,  # noqa: F401 — re-exported
)
from .data_classes import WorkflowResult
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
    "pattern-scanner",
    "risk-correlator",
    "prevention-advisor",
]

# Preserved for backward compatibility (executor pattern)
BUG_PREDICT_STEPS = {
    "recommend": WorkflowStepConfig(
        name="recommend",
        task_type="final_review",
        tier_hint="premium",
        description="Generate bug prevention recommendations",
        max_tokens=2000,
    ),
}

_SYSTEM_PROMPT = """\
You are a bug prediction orchestrator. You coordinate three specialized \
subagents to produce a unified bug prediction report. Be thorough but \
concise. Cite file paths and line numbers when possible.\
"""

_TASK_PROMPT_TEMPLATE = """\
Analyze the codebase at {path} using the three specialized subagents \
below. Each subagent should focus on its domain and report findings \
as structured markdown.

After all subagents finish, synthesize their findings into a single \
report with these sections:

## Summary
Overall risk score (0-100) and a 2-3 sentence executive summary of \
predicted bug hotspots.

## Bugs
Predicted bugs organized by severity (HIGH, MEDIUM, LOW). Each entry \
should include file path, line number, pattern type, and description.

## Suggestions
Actionable prevention strategies ordered by priority. Include specific \
refactoring advice and testing recommendations.\
"""

# Derived from the prompt above, never restated — the prompt IS
# the output contract, and a run that omits one of these sections
# is a failure, not a quiet exit-0 (see _check_section_contract).
_REQUIRED_SECTIONS = required_sections_from_prompt(_TASK_PROMPT_TEMPLATE)


class BugPredictionWorkflow(BaseWorkflow):
    """SDK-native bug prediction with three specialized subagents.

    Delegates all analysis to Claude Agent SDK subagents:
    - **pattern-scanner** — null refs, type mismatches, eval/exec,
      broad exceptions, resource leaks
    - **risk-correlator** — correlates findings with complexity
      and change frequency
    - **prevention-advisor** — prioritized mitigation strategies

    The orchestrator synthesizes findings into a unified report.

    Usage::

        workflow = BugPredictionWorkflow()
        result = await workflow.execute(path="src/", depth="standard")
    """

    name = "bug-predict"
    description = "Agent SDK-powered bug prediction with 3 specialized subagents"
    stages = ["agent-predict"]
    tier_map = {"agent-predict": ModelTier.CAPABLE}

    def __init__(self, *, system_prompt_suffix: str = "", **kwargs: Any) -> None:
        """Initialize workflow.

        Args:
            system_prompt_suffix: Optional string appended to the
                orchestrator's system prompt at call time. Lets a
                wrapping caller (e.g. discovery-sweep's
                ``BugPredictSource``) augment the prompt at the
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
        """Execute the Agent SDK bug prediction.

        Args:
            **kwargs: Keyword arguments.
                path (str): Required. Directory or file to scan.
                depth (str): Prediction depth — "quick", "standard",
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
            run_result = await self._run_agent_predict(
                resolved_path, max_turns, depth, max_budget_usd=max_budget_usd
            )
            self._track_sdk_run_telemetry(stage="agent", agent_run_result=run_result)
            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                report_title="Bug prediction",
                required_sections=_REQUIRED_SECTIONS,
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
            # crashing the CLI. Phase 4 of
            # docs/specs/sdk-error-message-fidelity/ — capture the
            # real claude CLI stderr via a second subprocess call,
            # classify it into a known kind, and thread the typed
            # fields onto WorkflowResult.metadata so the dashboard
            # can render the truth instead of regex-guessing.
            logger.exception(
                "Agent SDK bug prediction failed: %s",
                type(exc).__name__,
            )
            stderr = capture_subprocess_failure(_last_subprocess_argv(exc))
            kind, summary = classify_subprocess_failure(stderr)
            sdk_err = SdkSubprocessError(
                message=summary,
                stderr=stderr,
                kind=kind,
                original_exc=exc,
            )
            return self._error_result(
                sdk_err.format_user_message(),
                sdk_stderr=stderr,
                sdk_error_kind=kind,
            )

    async def _run_agent_predict(
        self,
        resolved_path: str,
        max_turns: int,
        depth: str = "standard",
        max_budget_usd: float | None = None,
    ) -> AgentRunResult:
        """Run the Agent SDK prediction and return result text.

        Args:
            resolved_path: Absolute path to scan.
            max_turns: Maximum agent turns.

        Returns:
            AgentRunResult with findings and SDK metadata.
        """
        assistant_parts: list[str] = []
        result_parts: list[str] = []
        run_result = AgentRunResult(result_text="No results returned.")
        system_prompt = (
            f"{_SYSTEM_PROMPT}\n\n{self._system_prompt_suffix}"
            if self._system_prompt_suffix
            else _SYSTEM_PROMPT
        )
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
                        "pattern-scanner": claude_agent_sdk.AgentDefinition(
                            description=("Pattern scanner that finds common " "bug patterns."),
                            prompt=(
                                "You are a bug pattern scanner. Focus "
                                "on: null references, type mismatches, "
                                "race conditions, eval/exec usage, "
                                "broad exception handlers, resource "
                                "leaks, and off-by-one errors. Report "
                                "each finding with file path, line "
                                "number, pattern type, and severity."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("pattern-scanner"),
                        ),
                        "risk-correlator": claude_agent_sdk.AgentDefinition(
                            description=("Risk correlator that assesses bug " "likelihood."),
                            prompt=(
                                "You are a risk correlator. Analyze "
                                "findings from the pattern scanner and "
                                "correlate them with file complexity, "
                                "change frequency, and historical bug "
                                "density. Assign risk scores to each "
                                "file and identify the highest-risk "
                                "modules. Report with file path, risk "
                                "score, and contributing factors."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("risk-correlator"),
                        ),
                        "prevention-advisor": claude_agent_sdk.AgentDefinition(
                            description=(
                                "Prevention advisor that suggests " "mitigation strategies."
                            ),
                            prompt=(
                                "You are a prevention advisor. Review "
                                "the correlated risk findings and "
                                "prioritize them by impact. Suggest "
                                "specific prevention strategies: code "
                                "refactoring, additional tests, type "
                                "annotations, error handling "
                                "improvements, and architectural "
                                "changes. Report with priority, "
                                "affected files, and actionable steps."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("prevention-advisor"),
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
