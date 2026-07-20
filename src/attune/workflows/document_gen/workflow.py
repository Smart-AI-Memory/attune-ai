"""Document Generation Workflow.

SDK-native documentation generation using three specialized subagents:
outline-planner, content-writer, and polish-reviewer.

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
from ..base import BaseWorkflow, ModelTier
from ..context import WorkflowContext
from ..data_classes import WorkflowResult
from ..services import ParsingService, PromptService
from .config import DOC_GEN_STEPS, TOKEN_COSTS  # noqa: F401  # re-export

logger = logging.getLogger(__name__)

_DEPTH_MAX_TURNS: dict[str, int] = {
    "quick": 10,
    "standard": 20,
    "deep": 40,
}

_SUBAGENT_NAMES = [
    "outline-planner",
    "content-writer",
    "polish-reviewer",
]

_SYSTEM_PROMPT = """\
You are a documentation generation orchestrator. Coordinate three \
specialized subagents to generate comprehensive documentation and \
synthesize their output into a single structured document. Be thorough \
but concise. Cite file paths when referencing source code.\
"""

_TASK_PROMPT_TEMPLATE = """\
Generate comprehensive documentation for the codebase at {path} using \
the three specialized subagents below. Each subagent should focus on \
its domain and produce structured markdown output.

After all subagents finish, synthesize their output into a single \
document with these sections:

## Summary
A 2-3 sentence overview of the documented codebase and its purpose.

## Outline
The documentation structure produced by the outline planner, listing \
modules, APIs, and example sections.

## Documentation
The full documentation content written by the content writer, with \
code examples and API references for each section.

## Suggestions
Recommendations for improving documentation coverage, clarity, or \
organization.\
"""


class DocumentGenerationWorkflow(BaseWorkflow):
    """Generate new documentation from source code (creation).

    Delegates all work to three Agent SDK subagents rather than using
    the mixin stage system. Each subagent focuses on a specific phase
    of documentation generation (outlining, writing, polishing). The
    orchestrator synthesizes their output into a unified document.

    Supports composition via ``WorkflowContext`` -- use ``default_context()``
    to get a pre-configured context with prompt and parsing services.

    Usage::

        workflow = DocumentGenerationWorkflow()
        result = await workflow.execute(path="src/", depth="standard")
    """

    name = "doc-gen"
    description = "Generate new documentation from source code (creation)"
    stages = ["agent-gen"]
    tier_map = {"agent-gen": ModelTier.CAPABLE}

    @classmethod
    def default_context(cls, xml_config: dict | None = None) -> WorkflowContext:
        """Create a WorkflowContext pre-configured for document generation.

        Args:
            xml_config: Optional XML prompt configuration dict.

        Returns:
            WorkflowContext with prompt and parsing services.

        """
        return WorkflowContext(
            prompt=PromptService("doc-gen", xml_config=xml_config),
            parsing=ParsingService(xml_config=xml_config),
        )

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the Agent SDK documentation generation.

        Args:
            **kwargs: Keyword arguments.
                path (str): Required. Directory or file to document.
                depth (str): Generation depth — "quick", "standard",
                    or "deep". Defaults to "standard".

        Returns:
            WorkflowResult with documentation, suggestions, and metadata.
        """
        path_arg: str = kwargs.get("path", "")
        depth: str = kwargs.get("depth", "standard")

        if not path_arg:
            return self._error_result("path argument is required")

        resolved_path = str(Path(path_arg).resolve())
        max_turns = _DEPTH_MAX_TURNS.get(depth, 20)

        started_at = datetime.now()

        try:
            run_result = await self._run_agent_gen(resolved_path, max_turns, depth=depth)
            self._track_sdk_run_telemetry(stage="agent", agent_run_result=run_result)

            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                report_title="Document generation",
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
            logger.exception("Agent SDK doc generation failed: %s", type(exc).__name__)
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

    async def _run_agent_gen(
        self, resolved_path: str, max_turns: int, depth: str = "standard"
    ) -> AgentRunResult:
        """Run the Agent SDK doc generation and return result text.

        Args:
            resolved_path: Absolute path to document.
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
                        "outline-planner": claude_agent_sdk.AgentDefinition(
                            description="Outline planner that analyzes codebase structure.",
                            prompt=(
                                "You are a documentation outline planner. "
                                "Analyze the codebase structure and plan a "
                                "comprehensive documentation outline. Focus "
                                "on: module organization, public APIs, key "
                                "classes and functions, configuration options, "
                                "and usage examples. Produce a structured "
                                "outline with sections and subsections."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("outline-planner"),
                        ),
                        "content-writer": claude_agent_sdk.AgentDefinition(
                            description="Content writer that produces documentation text.",
                            prompt=(
                                "You are a documentation content writer. "
                                "Write clear, accurate documentation for "
                                "each section of the outline. Include: "
                                "module descriptions, function signatures "
                                "with type hints, parameter explanations, "
                                "return value descriptions, code examples, "
                                "and usage patterns. Use Google-style "
                                "docstring format for API references."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("content-writer"),
                        ),
                        "polish-reviewer": claude_agent_sdk.AgentDefinition(
                            description="Polish reviewer that checks docs for quality.",
                            prompt=(
                                "You are a documentation polish reviewer. "
                                "Review the generated documentation for: "
                                "clarity and readability, technical accuracy, "
                                "completeness of API coverage, correct code "
                                "examples, consistent formatting, and missing "
                                "sections. Report issues and suggest specific "
                                "improvements."
                            ),
                            tools=["Read", "Glob", "Grep"],
                            model=get_subagent_model("polish-reviewer"),
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
