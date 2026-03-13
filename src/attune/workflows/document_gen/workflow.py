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

from ..agent_sdk_adapter import AgentSDKResultAdapter
from ..base import BaseWorkflow, ModelTier
from ..context import WorkflowContext
from ..data_classes import CostReport, WorkflowResult, WorkflowStage
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

_MAIN_PROMPT_TEMPLATE = """\
You are a documentation generation orchestrator. Generate comprehensive \
documentation for the codebase at {path} using the three specialized \
subagents below. Each subagent should focus on its domain and produce \
structured markdown output.

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
organization.

Be thorough but concise. Cite file paths when referencing source code.\
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
            result_text = await self._run_agent_gen(resolved_path, max_turns)

            completed_at = datetime.now()

            return AgentSDKResultAdapter.from_agent_output(
                result_text=result_text,
                subagent_names=_SUBAGENT_NAMES,
                started_at=started_at,
                completed_at=completed_at,
                metadata={
                    "path": resolved_path,
                    "depth": depth,
                    "max_turns": max_turns,
                },
            )

        except ImportError as exc:
            logger.error("Agent SDK import failed: %s", exc)
            return self._error_result(f"Agent SDK unavailable: {exc}")
        except (ConnectionError, TimeoutError) as exc:
            logger.error("Agent SDK network error: %s", exc)
            return self._error_result(f"Agent SDK connection failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            # INTENTIONAL: Catch-all for unknown SDK errors to return
            # a structured WorkflowResult rather than crashing.
            logger.exception("Agent SDK doc generation failed: %s", type(exc).__name__)
            return self._error_result(f"Agent SDK error: {type(exc).__name__}: {exc}")

    async def _run_agent_gen(self, resolved_path: str, max_turns: int) -> str:
        """Run the Agent SDK doc generation and return result text.

        Args:
            resolved_path: Absolute path to document.
            max_turns: Maximum agent turns.

        Returns:
            The agent's final result text.
        """
        result_parts: list[str] = []
        async for message in claude_agent_sdk.query(
            prompt=_MAIN_PROMPT_TEMPLATE.format(path=resolved_path),
            options=claude_agent_sdk.ClaudeAgentOptions(
                cwd=resolved_path,
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
                    ),
                },
            ),
        ):
            if isinstance(message, claude_agent_sdk.ResultMessage):
                result_parts.append(message.result)

        return "\n".join(result_parts) if result_parts else "No results returned."

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
                    name="agent-gen",
                    tier=ModelTier.CAPABLE,
                    description="Agent SDK documentation generation",
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
