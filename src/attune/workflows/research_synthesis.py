"""Research Synthesis Workflow

Multi-source research synthesis using Agent SDK subagents:
1. source-summarizer: Reads and extracts key findings from each source
2. pattern-analyst: Identifies themes and connections across sources
3. synthesis-writer: Produces a cohesive synthesis report

Module-level step configs (SUMMARIZE_STEP, ANALYZE_STEP, SYNTHESIZE_STEP,
SYNTHESIZE_STEP_CAPABLE) are preserved for backward compatibility with
any importers that reference them directly.

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
from .step_config import WorkflowStepConfig
from .validation import InputSchema

# Step configurations preserved for backward compatibility
SUMMARIZE_STEP = WorkflowStepConfig(
    name="summarize",
    task_type="summarize",  # Routes to cheap tier
    description="Summarize each source document",
    max_tokens=2048,
)

ANALYZE_STEP = WorkflowStepConfig(
    name="analyze",
    task_type="analyze_patterns",  # Routes to capable tier
    description="Identify patterns across summaries",
    max_tokens=2048,
)

SYNTHESIZE_STEP = WorkflowStepConfig(
    name="synthesize",
    task_type="complex_reasoning",  # Routes to premium tier
    description="Synthesize final insights",
    max_tokens=4096,
)

SYNTHESIZE_STEP_CAPABLE = WorkflowStepConfig(
    name="synthesize",
    task_type="generate_content",  # Routes to capable tier
    tier_hint="capable",  # Force capable tier
    description="Synthesize final insights (lower complexity)",
    max_tokens=4096,
)

logger = logging.getLogger(__name__)

_DEPTH_MAX_TURNS: dict[str, int] = {
    "quick": 10,
    "standard": 20,
    "deep": 40,
}

_SUBAGENT_NAMES = [
    "source-summarizer",
    "pattern-analyst",
    "synthesis-writer",
]

_SYSTEM_PROMPT = """\
You are a research synthesis orchestrator. Coordinate three specialized \
subagents to analyze source documents and combine their outputs into a \
single cohesive report. Be thorough but concise. Cite source documents \
and specific passages when possible.\
"""

_TASK_PROMPT_TEMPLATE = """\
Analyze the source documents at {path} using the three specialized \
subagents below. Each subagent should focus on its domain and report \
findings as structured markdown.

After all subagents finish, combine their outputs into a single \
cohesive report with these sections:

## Summary
A 2-3 sentence executive summary of the key findings and their \
significance.

## Research
Detailed findings organized by theme, with citations to specific \
source documents and data points.

## Suggestions
Actionable recommendations and areas for further investigation, \
ordered by priority.\
"""


class ResearchSynthesisWorkflow(BaseWorkflow):
    """Multi-source research synthesis with Agent SDK subagents.

    Delegates all analysis to three Agent SDK subagents rather than
    using the mixin stage system. Each subagent focuses on a specific
    synthesis task (summarization, pattern analysis, report writing).
    The orchestrator produces a cohesive synthesis report.

    Usage::

        workflow = ResearchSynthesisWorkflow()
        result = await workflow.execute(path="docs/research/", depth="standard")
    """

    name = "research-synthesis"
    description = "Multi-source research synthesis with Agent SDK subagents"
    stages = ["agent-synthesis"]
    tier_map = {"agent-synthesis": ModelTier.CAPABLE}

    input_schema = InputSchema(
        optional_fields={"path": str, "depth": str},
    )

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK research synthesis.

        Args:
            **kwargs: Keyword arguments.
                path (str): Required. Directory or file to analyze.
                depth (str): Synthesis depth — "quick", "standard",
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
            run_result = await self._run_agent_synthesis(resolved_path, max_turns, depth=depth)
            self._track_sdk_run_telemetry(stage="agent", agent_run_result=run_result)

            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                report_title="Research synthesis",
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
            logger.exception("Agent SDK research synthesis failed: %s", type(exc).__name__)
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

    async def _run_agent_synthesis(
        self, resolved_path: str, max_turns: int, depth: str = "standard"
    ) -> AgentRunResult:
        """Run the Agent SDK synthesis and return result text.

        Args:
            resolved_path: Absolute path to analyze.
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
                    allowed_tools=["Read", "Glob", "Grep", "Agent"],
                    permission_mode="default",
                    max_turns=max_turns,
                    agents={
                        "source-summarizer": claude_agent_sdk.AgentDefinition(
                            description="Source summarizer that reads and extracts key findings.",
                            prompt=(
                                "You are a source summarizer. Read and "
                                "summarize source documents, extracting "
                                "key findings and data points. For each "
                                "source, report the document title, main "
                                "arguments, supporting evidence, and "
                                "notable data points. Organize by source."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("source-summarizer"),
                        ),
                        "pattern-analyst": claude_agent_sdk.AgentDefinition(
                            description="Pattern analyst that identifies themes and connections.",
                            prompt=(
                                "You are a pattern analyst. Identify "
                                "patterns, themes, and connections across "
                                "summarized sources. Look for recurring "
                                "arguments, contradictions, complementary "
                                "findings, and emerging trends. Report "
                                "each pattern with supporting citations "
                                "from multiple sources."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("pattern-analyst"),
                        ),
                        "synthesis-writer": claude_agent_sdk.AgentDefinition(
                            description="Synthesis writer that produces a cohesive report.",
                            prompt=(
                                "You are a synthesis writer. Write a "
                                "cohesive synthesis report combining all "
                                "findings with citations. Integrate "
                                "source summaries and identified patterns "
                                "into a narrative that highlights key "
                                "insights, resolves contradictions, and "
                                "suggests areas for further investigation."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("synthesis-writer"),
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
