"""Code Simplification Workflow

Reduces unnecessary complexity in code. Inspired by Boris
Cherny's observation that Claude tends to over-engineer:
too many abstractions, unnecessary classes, premature
optimization, over-configurable interfaces.

Delegates all analysis to three Agent SDK subagents
(complexity-scanner, simplification-designer, safety-reviewer)
and synthesizes their findings into a unified WorkflowResult.

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

logger = logging.getLogger(__name__)

# Categories the crew should focus on for simplification
SIMPLIFY_FOCUS_AREAS = [
    "simplify",
    "consolidate_conditional",
    "inline",
    "dead_code",
]

# Simplify-related RefactoringCategory values to keep from crew results
SIMPLIFY_CATEGORIES = {
    "simplify",
    "consolidate_conditional",
    "inline",
    "dead_code",
}

_DEPTH_MAX_TURNS: dict[str, int] = {
    "quick": 10,
    "standard": 20,
    "deep": 40,
}

_SUBAGENT_NAMES = [
    "complexity-scanner",
    "simplification-designer",
    "safety-reviewer",
]

_SYSTEM_PROMPT = """\
You are a senior code simplification orchestrator. You coordinate three \
specialized subagents to produce a unified simplification report. \
Be thorough but concise. Cite file paths and line numbers when possible.\
"""

_TASK_PROMPT_TEMPLATE = """\
Analyze the codebase at {path} using the three specialized subagents \
below. Each subagent should focus on its domain and report findings \
as structured markdown.

After all subagents finish, synthesize their findings into a single \
report with these sections:

## Summary
Overall complexity score (0-100) and a 2-3 sentence executive summary \
of simplification opportunities.

## Complexity
Findings from the complexity scanner — deep nesting, long functions, \
unnecessary abstractions, dead code paths, and over-engineered patterns.

## Refactoring
Proposed simplifications from the simplification designer — flattened \
conditionals, inlined helpers, reduced class hierarchies, and removed \
dead code.

## Suggestions
Safety-reviewed actionable next steps ordered by impact. Each suggestion \
should note whether it is safe to apply automatically or requires manual \
review.\
"""


class SimplifyCodeWorkflow(BaseWorkflow):
    """Simplify over-engineered code with Agent SDK subagents.

    Delegates all analysis to three Agent SDK subagents rather
    than using the mixin stage system. Each subagent focuses on
    a specific simplification domain (complexity scanning,
    simplification design, safety review). The orchestrator
    synthesizes findings into a unified report.

    Boris's insight: Claude over-engineers. This workflow
    counteracts that by flattening nesting, inlining trivial
    helpers, removing dead code, and reducing abstractions.

    Usage::

        workflow = SimplifyCodeWorkflow()
        result = await workflow.execute(path="src/", depth="standard")
    """

    name = "simplify-code"
    description = "Simplify over-engineered code with Agent SDK subagents"
    stages = ["agent-simplify"]
    tier_map = {"agent-simplify": ModelTier.CAPABLE}

    input_schema = InputSchema(
        optional_fields={"path": str, "depth": str},
    )

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK code simplification.

        Args:
            **kwargs: Keyword arguments.
                path (str): Required. Directory or file to simplify.
                depth (str): Analysis depth — "quick", "standard",
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
            run_result = await self._run_agent_simplify(resolved_path, max_turns, depth)
            self._track_sdk_run_telemetry(stage="agent", agent_run_result=run_result)

            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                report_title="Code simplification",
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
            logger.exception("Agent SDK code simplification failed: %s", type(exc).__name__)
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

    async def _run_agent_simplify(
        self, resolved_path: str, max_turns: int, depth: str = "standard"
    ) -> AgentRunResult:
        """Run the Agent SDK simplification and return result text.

        Args:
            resolved_path: Absolute path to analyze.
            max_turns: Maximum agent turns.

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
                    allowed_tools=["Read", "Glob", "Grep", "Agent"],
                    permission_mode="default",
                    max_turns=max_turns,
                    agents={
                        "complexity-scanner": claude_agent_sdk.AgentDefinition(
                            description="Complexity scanner that finds overly complex code.",
                            prompt=(
                                "You are a complexity scanner. Focus on: "
                                "deep nesting (3+ levels), long functions "
                                "(50+ lines), unnecessary abstractions, "
                                "dead code paths, and over-engineered "
                                "patterns. Report each finding with file "
                                "path, line number, complexity metric, and "
                                "why it should be simplified."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("complexity-scanner"),
                        ),
                        "simplification-designer": claude_agent_sdk.AgentDefinition(
                            description=(
                                "Simplification designer that proposes refactoring approaches."
                            ),
                            prompt=(
                                "You are a simplification designer. For "
                                "each complexity finding, design a concrete "
                                "simplification approach: flatten nested "
                                "conditionals with early returns, inline "
                                "trivial helper functions used only once, "
                                "reduce class hierarchies when a function "
                                "suffices, and remove dead code. Show "
                                "before/after examples."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("simplification-designer"),
                        ),
                        "safety-reviewer": claude_agent_sdk.AgentDefinition(
                            description=(
                                "Safety reviewer that verifies simplifications"
                                " won't break behavior."
                            ),
                            prompt=(
                                "You are a safety reviewer. For each "
                                "proposed simplification, verify it does "
                                "not break existing behavior, public APIs, "
                                "or tests. Check for side effects, changed "
                                "return types, removed error handling, and "
                                "altered control flow. Flag any risky "
                                "changes that need manual review."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("safety-reviewer"),
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
