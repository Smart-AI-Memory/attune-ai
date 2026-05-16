"""RAG-Grounded Code Generation Workflow.

Retrieves context from a RAG corpus (attune-help by default)
and feeds an augmented prompt to a single Claude Agent SDK
call, returning a ``WorkflowResult`` whose ``final_output``
carries both the generated code and markdown-formatted source
citations for provenance.

Unlike the security / code-review workflows, this workflow
uses a single agent (no subagents) — the SDK call does the
generation, and retrieval is handled synchronously before
the call by ``attune_rag.RagPipeline``.

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

import claude_agent_sdk

from .agent_sdk_adapter import (
    AgentRunResult,
    AgentSDKResultAdapter,
    build_result_text,
    collect_agent_output,
    get_max_budget_usd,
    get_task_budget,
    get_thinking_config,
    resolve_cwd_for_path,
    sdk_error_message,
)
from .base import BaseWorkflow, ModelTier
from .data_classes import WorkflowResult

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = (
    "You generate code and explanations grounded in the attune "
    "ecosystem. Use the provided context to cite real APIs, "
    "workflow names, and CLI commands. Never invent attune "
    "features. When referencing a pattern, note the source file "
    "it came from."
)


_DEPTH_MAX_TURNS: dict[str, int] = {
    "quick": 6,
    "standard": 12,
    "deep": 24,
}


class RagCodeGenWorkflow(BaseWorkflow):
    """SDK-native RAG-grounded code generation workflow.

    Retrieves grounding context from the configured RAG corpus,
    feeds the augmented prompt to a single Claude Agent SDK
    call, and returns a ``WorkflowResult`` with the generated
    output followed by a markdown ``## Sources`` block.

    Usage::

        workflow = RagCodeGenWorkflow()
        result = await workflow.execute(
            query="how do I run a security audit?",
        )

    Supported kwargs:
        query (str): Required. The user's coding request.
        k (int): Number of grounding docs to retrieve. Default 3.
        depth (str): "quick" | "standard" | "deep". Default
            "standard". Controls max_turns and budget.
        feedback (str): "good" | "bad". Optional. When set,
            records feedback on every cited template via
            ``record_template_feedback`` (Phase 4.1).
        model (str): Optional model override for generation.
        path (str): Working directory / scope for the Claude Agent
            SDK's ``Read``/``Glob``/``Grep`` tool calls.
            Defaults to ``os.getcwd()`` at execute time so the
            agent cannot escape the caller's invocation
            directory via a prompt-injected path. Matches the
            ``cwd=resolved_path`` pattern used in
            ``security_audit.py``.
        cwd (str): Deprecated alias for ``path``; emits
            ``DeprecationWarning``. Removed in v7.0.
    """

    name = "rag-code-gen"
    description = "RAG-grounded code generation with source citations"
    stages = ["retrieve", "generate"]
    tier_map = {
        "retrieve": ModelTier.CHEAP,  # retrieval is zero-LLM; CHEAP is a tag
        "generate": ModelTier.CAPABLE,
    }

    # Base URL used for clickable citation links. Points at the
    # attune-help repo so users can inspect the source template.
    _CITATION_BASE_URL = (
        "https://github.com/Smart-AI-Memory/attune-help/blob/main/src/attune_help/templates"
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._pipeline: Any = None  # lazy init on first execute

    def _get_pipeline(self) -> Any:
        if self._pipeline is None:
            try:
                from attune_rag import RagPipeline
            except ImportError as exc:
                raise RuntimeError(
                    "The rag-code-gen workflow requires the [rag] extra. "
                    "Install with: pip install 'attune-ai[rag]'"
                ) from exc
            self._pipeline = RagPipeline()
        return self._pipeline

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        import warnings as _warnings  # local to keep formatter from stripping

        query: str = kwargs.get("query", "")
        k: int = int(kwargs.get("k", 3))
        depth: str = kwargs.get("depth", "standard")
        feedback: str | None = kwargs.get("feedback")
        model: str | None = kwargs.get("model")
        # Default cwd to the caller's invocation directory so the
        # SDK's Read/Glob/Grep tools cannot climb outside via a
        # prompt-injected path; mirror security_audit.py's
        # resolved-path scoping. `path` is the new canonical kwarg
        # name (workflow-path-arg-unification PR-4, 2026-05-13);
        # `cwd` is preserved as a deprecated alias because they
        # are semantically identical for this workflow.
        legacy_cwd = kwargs.get("cwd")
        new_path = kwargs.get("path")
        if legacy_cwd and not new_path:
            _warnings.warn(
                "RagCodeGenWorkflow.execute(cwd=...) is deprecated; "
                "use execute(path=...) instead. The legacy kwarg "
                "will be removed in v7.0.",
                DeprecationWarning,
                stacklevel=2,
            )
        elif legacy_cwd and new_path:
            _warnings.warn(
                "RagCodeGenWorkflow.execute(): both `path=` and "
                "`cwd=` supplied; `path=` takes precedence and "
                "`cwd=` is deprecated.",
                DeprecationWarning,
                stacklevel=2,
            )
        cwd: str = new_path or legacy_cwd or os.getcwd()

        if not query or not query.strip():
            return self._error_result("query argument is required")

        max_turns = _DEPTH_MAX_TURNS.get(depth, 12)
        started_at = datetime.now()

        try:
            pipeline = self._get_pipeline()
            # Pin prompt_variant explicitly to insulate this workflow
            # from future default-variant changes in attune-rag.
            # citation = per-passage sentinel wrapping + forced
            # cite-per-claim, selected by the 2026-04-19 A/B sweep.
            rag_result = pipeline.run(query, k=k, prompt_variant="citation")
        except RuntimeError as exc:
            logger.error("RAG pipeline setup failed: %s", exc)
            return self._error_result(f"RAG setup error: {exc}")

        try:
            run_result = await self._run_agent_generate(
                augmented_prompt=rag_result.augmented_prompt,
                max_turns=max_turns,
                depth=depth,
                model=model,
                cwd=cwd,
            )
        except ImportError as exc:
            logger.error("Agent SDK import failed: %s", exc)
            return self._error_result(f"Agent SDK unavailable: {exc}")
        except (ConnectionError, TimeoutError) as exc:
            logger.error("Agent SDK network error: %s", exc)
            return self._error_result(f"Agent SDK connection failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            # INTENTIONAL: Catch-all for unknown SDK errors so we
            # return a structured WorkflowResult rather than
            # crashing the CLI.
            logger.exception(
                "RAG generation failed: %s",
                type(exc).__name__,
            )
            duration = (datetime.now() - started_at).total_seconds()
            return self._error_result(
                sdk_error_message(exc, duration_seconds=duration, depth=depth)
            )

        completed_at = datetime.now()

        # Append markdown citations to the generated output so the
        # user sees provenance in the same blob as the code.
        from attune_rag.provenance import format_citations_markdown

        citations_md = format_citations_markdown(
            rag_result.citation,
            base_url=self._CITATION_BASE_URL,
        )
        combined_text = (run_result.result_text or "") + "\n\n" + citations_md

        # Optional feedback integration (Phase 4.1 hook). Uses the
        # existing help/feedback.py machinery to record the user's
        # verdict against each cited template.
        if feedback in ("good", "bad"):
            self._record_feedback(rag_result, feedback)

        # Build citation dict for metadata (JSON-serializable).
        citation_dict = {
            "query": rag_result.citation.query,
            "retriever_name": rag_result.citation.retriever_name,
            "retrieved_at": rag_result.citation.retrieved_at.isoformat(),
            "hits": [
                {
                    "template_path": hit.template_path,
                    "category": hit.category,
                    "score": hit.score,
                }
                for hit in rag_result.citation.hits
            ],
        }

        wf_result = AgentSDKResultAdapter.from_agent_output(
            result_text=combined_text,
            subagent_names=["rag-generator"],
            started_at=started_at,
            completed_at=completed_at,
            metadata={
                "query": query,
                "depth": depth,
                "max_turns": max_turns,
                "citation": citation_dict,
                "fallback_used": rag_result.fallback_used,
                "confidence": rag_result.confidence,
                "retrieval_ms": rag_result.elapsed_ms,
                "feedback_recorded": feedback if feedback in ("good", "bad") else None,
            },
            agent_run_result=run_result,
        )
        return wf_result

    async def _run_agent_generate(
        self,
        augmented_prompt: str,
        max_turns: int,
        depth: str,
        model: str | None,
        cwd: str,
    ) -> AgentRunResult:
        """Run a single Claude Agent SDK generation call.

        Returns the raw ``AgentRunResult`` so the caller can
        fold metadata into a ``WorkflowResult``.
        """
        assistant_parts: list[str] = []
        result_parts: list[str] = []
        run_result = AgentRunResult(result_text="No results returned.")

        options_kwargs: dict[str, Any] = {
            "system_prompt": _SYSTEM_PROMPT,
            "max_budget_usd": get_max_budget_usd(depth),
            "allowed_tools": ["Read", "Glob", "Grep"],
            "permission_mode": "default",
            "max_turns": max_turns,
            "cwd": resolve_cwd_for_path(cwd),
        }
        if model:
            options_kwargs["model"] = model
        # Token-aware budget + optional extended thinking (deep runs only).
        # See agent_sdk_adapter.get_task_budget / get_thinking_config.
        if (task_budget := get_task_budget(depth)) is not None:
            options_kwargs["task_budget"] = task_budget
        if (thinking := get_thinking_config(depth)) is not None:
            options_kwargs["thinking"] = thinking
            options_kwargs["effort"] = "high"

        async for message in claude_agent_sdk.query(
            prompt=augmented_prompt,
            options=claude_agent_sdk.ClaudeAgentOptions(**options_kwargs),
        ):
            sdk_result = collect_agent_output(message, assistant_parts, result_parts)
            if sdk_result is not None:
                run_result = sdk_result
        run_result.result_text = build_result_text(assistant_parts, result_parts)
        return run_result

    def _record_feedback(self, rag_result: Any, verdict: str) -> None:
        """Record good/bad feedback against each cited template.

        Best-effort — never fails the workflow if the feedback
        backend is unavailable.
        """
        try:
            from attune.help.feedback import record_template_feedback
        except ImportError:
            logger.info("help.feedback unavailable; skipping feedback record")
            return

        for hit in rag_result.citation.hits:
            try:
                record_template_feedback(hit.template_path, verdict)
            except Exception:  # noqa: BLE001
                # INTENTIONAL: feedback recording is best-effort;
                # a single failed write should not fail the whole
                # workflow. Log and continue.
                logger.exception(
                    "Failed to record feedback for template: %s",
                    hit.template_path,
                )
