"""Workflow tool handlers for the MCP server.

Exposes 11 additional workflows as MCP tools. Each handler
lazily imports its workflow class, calls execute(), and
extracts relevant fields from the result.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: pick names that mean "the workflow's findings" across handlers
_FINDINGS_KEYS = frozenset({"findings", "predictions", "checks"})


def _is_score_key(name: str) -> bool:
    """True for pick names that mean "the workflow's score"."""
    return name == "score" or name.endswith("_score")


def _metadata_findings(result: Any) -> list[Any]:
    """Findings from ``result.metadata`` when the report carries none.

    The SDK adapter stores parsed findings as a category→items dict on
    ``metadata["findings"]``; string-bullet findings become a ListSection
    (not a FindingsSection), so the report's ``.findings`` property can
    be empty while metadata still has the items. Flatten to one list.
    """
    metadata = getattr(result, "metadata", None)
    if not isinstance(metadata, dict):
        return []
    raw = metadata.get("findings")
    if isinstance(raw, dict):
        flat: list[Any] = []
        for items in raw.values():
            if isinstance(items, list):
                flat.extend(items)
        return flat
    if isinstance(raw, list):
        return raw
    return []


def _pick_source(source: Any) -> tuple[Any, Any]:
    """Unpack a field-pick ``source`` into ``(src_key, default)``."""
    return source if isinstance(source, tuple) else (source, None)


def _report_fields(result: Any, fo: Any, raw_output: bool, field_picks: dict) -> dict[str, Any]:
    """Response fields for a serialized-WorkflowReport final_output.

    Carries the rendered summary markdown verbatim (``summary_markdown``),
    the report JSON (``report``), and the back-compat ``score`` /
    ``findings`` fields restored from the report (metadata findings as
    fallback). Findings-like picks (``findings``/``predictions``/
    ``checks``) resolve to the report findings; score-like picks
    (``score``, ``*_score`` — either side of the mapping) to the report
    score; everything else to its default.
    """
    from attune.config import resolve_show_cost
    from attune.voice.report_renderer import render_safe
    from attune.workflows.output import WorkflowReport

    # Universal rich panel for mcp__visualize__show_widget — renders
    # the report's sections (findings / category-bullets / next-steps)
    # for EVERY SDK-native workflow at once (spec
    # analysis-workflow-output-widgets D4). Display-only, injection-safe.
    from attune.workflows.report_panel import report_to_panel_html

    report = WorkflowReport.from_dict(fo)
    findings = [f.to_dict() for f in report.findings] or _metadata_findings(result)
    fields: dict[str, Any] = {
        "summary_markdown": render_safe(
            report,
            disclosure="summary",
            show_cost=resolve_show_cost(),
        ),
        "report": fo,
        "score": report.score,
        "findings": findings,
        "panel_html": report_to_panel_html(fo, succeeded=bool(getattr(result, "success", True))),
    }
    if raw_output:
        fields["output"] = fields["summary_markdown"]
    for key, source in field_picks.items():
        src_key, default = _pick_source(source)
        if key in _FINDINGS_KEYS or src_key in _FINDINGS_KEYS:
            fields[key] = findings
        elif _is_score_key(key) or _is_score_key(src_key):
            fields[key] = report.score
        else:
            fields[key] = default
    return fields


def _legacy_fields(fo: Any, raw_output: bool, field_picks: dict) -> dict[str, Any]:
    """Response fields for a legacy flat-dict final_output — each pick
    is ``final_output.get(source)``, exactly the field-picking the
    handlers did before the report path existed."""
    fo_dict = fo if isinstance(fo, dict) else {}
    fields: dict[str, Any] = {}
    for key, source in field_picks.items():
        src_key, default = _pick_source(source)
        fields[key] = fo_dict.get(src_key, default)
    if raw_output:
        fields["output"] = fo
    return fields


def _error_fields(result: Any) -> dict[str, Any]:
    """Surface the real failure reason of an errored run.

    Without this, an errored run is indistinguishable from a clean
    empty result (success=false, findings=[], cost=0) — the
    swallowed-error trap (see removing-dead-code.md "fake-success
    signature"). The canonical signal is result.error; SDK-native runs
    leave that None and carry the message in metadata instead
    (is_error + raw_result_text), e.g. an auth failure surfacing as
    "Invalid API key". Only str messages are accepted so a mocked
    result never injects a spurious key.
    """
    meta = getattr(result, "metadata", None) or {}
    if not (result.success is False or meta.get("is_error")):
        return {}
    candidates = (
        getattr(result, "error", None),
        meta.get("raw_result_text") if meta.get("is_error") else None,
        meta.get("errors"),
    )
    error_msg = next((c for c in candidates if isinstance(c, str) and c.strip()), None)
    if error_msg is None:
        return {}
    fields: dict[str, Any] = {"error": error_msg}
    error_type = getattr(result, "error_type", None)
    if isinstance(error_type, str):
        fields["error_type"] = error_type
    return fields


def _workflow_response(
    result: Any,
    *,
    include_provider: bool = False,
    raw_output: bool = False,
    **field_picks: Any,
) -> dict[str, Any]:
    """Build an MCP response dict from a WorkflowResult.

    Two shapes, decided by what ``result.final_output`` carries
    (workflow-result-formatting spec, T5): a serialized WorkflowReport
    (:func:`_report_fields`) or a legacy flat dict
    (:func:`_legacy_fields`). Errored runs additionally carry the real
    failure reason (:func:`_error_fields`).

    Args:
        result: WorkflowResult returned by a workflow ``execute()``.
        include_provider: Include ``result.provider`` in the response.
        raw_output: Include an ``output`` field — the legacy
            ``final_output`` passthrough; on the report path it carries
            the summary markdown instead of the raw report dict.
        **field_picks: ``response_key=source`` mappings where ``source``
            is a final_output key or a ``(key, default)`` tuple.

    Returns:
        JSON-safe response dict with ``success`` and ``cost`` always set.
    """
    from attune.workflows.output import WorkflowReport

    response: dict[str, Any] = {"success": result.success}
    fo = result.final_output

    if WorkflowReport.is_report_dict(fo):
        response.update(_report_fields(result, fo, raw_output, field_picks))
    else:
        response.update(_legacy_fields(fo, raw_output, field_picks))
        # Family-B: a prose-only run (no parseable findings) leaves
        # final_output as the raw markdown string. Give it a styled panel
        # too, so prose workflows (deep-review, test-audit, refactor-plan,
        # dependency-check, code-review) aren't stuck with raw markdown.
        if isinstance(fo, str) and fo.strip():
            from attune.workflows.report_panel import markdown_to_panel_html

            response["panel_html"] = markdown_to_panel_html(fo, succeeded=result.success)

    cost_report = getattr(result, "cost_report", None)
    response["cost"] = cost_report.total_cost if cost_report is not None else 0.0
    if include_provider:
        response["provider"] = result.provider

    response.update(_error_fields(result))
    return response


class WorkflowHandlersMixin:
    """Mixin providing workflow tool handlers for EmpathyMCPServer.

    Covers workflows not already exposed in the base server:
    doc-audit, doc-gen, doc-orchestrator, test-audit,
    test-gen-parallel, refactor-plan, dependency-check,
    simplify-code, deep-review, secure-release, health-check,
    and research-synthesis.
    """

    def _validated_path(self, args: dict[str, Any], key: str = "path", default: str = ".") -> str:
        """Validate a user-supplied path argument.

        Args:
            args: Tool arguments dict.
            key: The key to extract from args.
            default: Fallback if key is absent.

        Returns:
            Validated path as a string.

        Raises:
            ValueError: If path is invalid or outside workspace.
        """
        from attune.security.path_validation import _validate_file_path

        raw = args.get(key, default)
        return str(_validate_file_path(raw, allowed_dir=self._workspace_root))

    # ------------------------------------------------------------------
    # Doc Audit
    # ------------------------------------------------------------------

    async def _run_doc_audit(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run documentation audit workflow.

        Args:
            args: Optional ``path`` key for project root.

        Returns:
            Dict with success, score, and findings.

        """
        from attune.workflows.doc_audit import DocAuditWorkflow

        workflow = DocAuditWorkflow()
        # execute reads `path` (not the legacy `project_root`); passing the
        # stale kwarg left `path` empty → "path argument is required".
        result = await workflow.execute(path=self._validated_path(args))

        return _workflow_response(result, score="score", findings=("checks", []))

    # ------------------------------------------------------------------
    # Doc Generation
    # ------------------------------------------------------------------

    async def _run_doc_gen(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run documentation generation workflow.

        Args:
            args: ``source_path`` (required). (``doc_type``/``audience``
                were dropped in the v4.2.0 SDK migration — see below — so
                they are no longer accepted.)

        Returns:
            Dict with success and generated document content.

        """
        from attune.workflows.document_gen import DocumentGenerationWorkflow

        # execute reads `path` (and `depth`); the SDK subagents read the
        # source themselves. The legacy `source_code`/`doc_type`/`audience`
        # kwargs were dropped in the v4.2.0 SDK migration, so passing them
        # left `path` empty → "path argument is required".
        workflow = DocumentGenerationWorkflow()
        result = await workflow.execute(path=self._validated_path(args, key="source_path"))

        return _workflow_response(result, document="document", sections="sections")

    # ------------------------------------------------------------------
    # Doc Orchestrator
    # ------------------------------------------------------------------

    async def _run_doc_orchestrator(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run end-to-end documentation orchestration workflow.

        Args:
            args: Optional ``path`` for project root.

        Returns:
            Dict with phase, items processed, and generated docs.

        """
        from attune.workflows.documentation_orchestrator import (
            DocumentationOrchestrator,
        )

        workflow = DocumentationOrchestrator()
        # execute scopes off the `path` kwarg; the project root was
        # previously buried inside the `context` dict, where execute never
        # read it — so the ops scope-picker could not re-scope the run.
        result = await workflow.execute(path=self._validated_path(args))

        return {
            "success": getattr(result, "phase", "") == "complete",
            "phase": getattr(result, "phase", "unknown"),
            "degraded": getattr(result, "degraded", False),
            "items_found": getattr(result, "items_found", 0),
            "docs_generated": getattr(result, "docs_generated", []),
            "docs_updated": getattr(result, "docs_updated", []),
            "total_cost": getattr(result, "total_cost", 0.0),
        }

    # ------------------------------------------------------------------
    # Test Audit
    # ------------------------------------------------------------------

    async def _run_test_audit(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run deep test coverage audit workflow.

        Args:
            args: Optional ``path`` for source root.

        Returns:
            Dict with success and coverage delta.

        """
        from attune.workflows.test_audit import TestAuditWorkflow

        workflow = TestAuditWorkflow()
        # Use the canonical `path` kwarg; `src_path` still works but is a
        # deprecated alias that emits a DeprecationWarning.
        result = await workflow.execute(path=self._validated_path(args, default="src/"))

        return _workflow_response(result, raw_output=True)

    # ------------------------------------------------------------------
    # Parallel Test Generation
    # ------------------------------------------------------------------

    async def _run_test_gen_parallel(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run parallel test generation workflow.

        Args:
            args: Optional ``top`` (int), ``batch_size`` (int).

        Returns:
            Dict with completed count and generated file paths.

        """
        from attune.workflows.test_gen_parallel import (
            ParallelTestGenerationWorkflow,
        )

        workflow = ParallelTestGenerationWorkflow()
        result = await workflow.execute(
            top=args.get("top", 200),
            batch_size=args.get("batch_size", 10),
        )

        return _workflow_response(
            result,
            total_modules=("total_modules", 0),
            completed=("completed", 0),
            errors=("errors", 0),
            generated_files=("generated_files", []),
        )

    # ------------------------------------------------------------------
    # Refactor Plan
    # ------------------------------------------------------------------

    async def _run_refactor_plan(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run refactoring plan workflow.

        Args:
            args: ``path`` (required) for target directory.

        Returns:
            Dict with success, plan summary, and debt items.

        """
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        workflow = RefactorPlanWorkflow()
        result = await workflow.execute(path=self._validated_path(args))

        return _workflow_response(result, raw_output=True)

    # ------------------------------------------------------------------
    # Dependency Check
    # ------------------------------------------------------------------

    async def _run_dependency_check(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run dependency check workflow.

        Args:
            args: ``path`` (required) for project root.

        Returns:
            Dict with risk score, vulnerabilities, and recommendations.

        """
        from attune.workflows.dependency_check import DependencyCheckWorkflow

        workflow = DependencyCheckWorkflow()
        result = await workflow.execute(path=self._validated_path(args))

        return _workflow_response(result, raw_output=True)

    # ------------------------------------------------------------------
    # Deep Review
    # ------------------------------------------------------------------

    async def _run_deep_review(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run multi-pass deep code review.

        Args:
            args: ``path`` (required) for target directory or file.

        Returns:
            Dict with success, findings, and review output.

        """
        from attune.workflows.deep_review import DeepReviewAgentSDKWorkflow

        workflow = DeepReviewAgentSDKWorkflow()
        result = await workflow.execute(path=self._validated_path(args))

        return _workflow_response(result, raw_output=True)

    # ------------------------------------------------------------------
    # Simplify Code
    # ------------------------------------------------------------------

    async def _run_simplify_code(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run code simplification workflow.

        Args:
            args: ``path`` (required) for target directory.

        Returns:
            Dict with success, hotspots found, and simplifications.

        """
        from attune.workflows.simplify_code import SimplifyCodeWorkflow

        workflow = SimplifyCodeWorkflow()
        result = await workflow.execute(path=self._validated_path(args))

        return _workflow_response(result, raw_output=True)

    # ------------------------------------------------------------------
    # Secure Release
    # ------------------------------------------------------------------

    async def _run_secure_release(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run secure release pipeline.

        Args:
            args: Optional ``path`` for project root.

        Returns:
            Dict with go/no-go decision, risk score, and blockers.

        """
        from attune.workflows.secure_release import SecureReleasePipeline

        workflow = SecureReleasePipeline()
        result = await workflow.execute(path=self._validated_path(args))

        return {
            "success": getattr(result, "success", False),
            "go_no_go": getattr(result, "go_no_go", "unknown"),
            "combined_risk_score": getattr(result, "combined_risk_score", 0),
            "blockers": getattr(result, "blockers", []),
            "warnings": getattr(result, "warnings", []),
            "total_cost": getattr(result, "total_cost", 0.0),
        }

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    async def _run_health_check(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run orchestrated health check workflow.

        Args:
            args: Optional ``project_root`` for target project.

        Returns:
            Dict with health score, grade, and recommendations.

        """
        from attune.workflows.orchestrated_health_check import (
            OrchestratedHealthCheckWorkflow,
        )

        workflow = OrchestratedHealthCheckWorkflow()
        # Use the canonical `path` kwarg; `project_root` still works but is a
        # deprecated alias that emits a DeprecationWarning.
        result = await workflow.execute(
            path=self._validated_path(args, key="project_root"),
        )

        return {
            "success": getattr(result, "success", False),
            "health_score": getattr(result, "overall_health_score", 0),
            "grade": getattr(result, "grade", "unknown"),
            "degraded": getattr(result, "degraded", False),
            "issues": getattr(result, "issues", []),
            "recommendations": getattr(result, "recommendations", []),
        }

    # ------------------------------------------------------------------
    # Research Synthesis
    # ------------------------------------------------------------------

    async def _run_research_synthesis(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run the research-synthesis workflow over local documents.

        Args:
            args: ``path`` (str, optional, default ".") — directory or
                file of source documents to analyze; ``depth`` (str,
                optional) — "quick", "standard" (default), or "deep".

        Returns:
            Dict with the synthesized answer and key insights.

        """
        from attune.workflows.research_synthesis import (
            ResearchSynthesisWorkflow,
        )

        # The workflow is a path-driven 3-agent pipeline (it reads source
        # documents at ``path``); passing the legacy ``sources``/``question``
        # kwargs left ``path`` empty → "path argument is required".
        workflow = ResearchSynthesisWorkflow()
        result = await workflow.execute(
            path=self._validated_path(args),
            depth=args.get("depth", "standard"),
        )

        final = result.final_output if hasattr(result, "final_output") else result

        from attune.workflows.output import WorkflowReport

        if WorkflowReport.is_report_dict(final):
            response = _workflow_response(
                result,
                key_insights="key_insights",
                confidence="confidence",
            )
            # "answer" is this tool's primary consumer field — the
            # rendered summary IS the synthesized answer.
            response["answer"] = response["summary_markdown"]
            return response

        if isinstance(final, dict):
            return {
                "success": True,
                "answer": final.get("answer"),
                "key_insights": final.get("key_insights"),
                "confidence": final.get("confidence"),
                "cost": getattr(getattr(result, "cost_report", None), "total_cost", 0.0),
            }
        return {
            "success": True,
            "output": str(final),
        }

    async def _run_analyze_batch(self, args: dict[str, Any]) -> dict[str, Any]:
        """Submit tasks to the Anthropic Batch API (50% cost savings).

        Args:
            args: ``requests`` (list of task dicts with task_id,
                task_type, input_data, and optional model_tier).

        Returns:
            Dict with batch_id and submission status.

        """
        from attune.workflows.batch_processing import (
            BatchProcessingWorkflow,
            BatchRequest,
        )

        raw_requests = args.get("requests", [])
        if not raw_requests:
            return {"success": False, "error": "requests array is required and cannot be empty"}

        requests = [
            BatchRequest(
                task_id=r["task_id"],
                task_type=r["task_type"],
                input_data=r["input_data"],
                model_tier=r.get("model_tier", "capable"),
            )
            for r in raw_requests
        ]

        workflow = BatchProcessingWorkflow()
        results = await workflow.execute_batch(requests)

        return {
            "success": True,
            "total": len(results),
            "succeeded": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "results": [
                {
                    "task_id": r.task_id,
                    "success": r.success,
                    "output": r.output,
                    "error": r.error,
                }
                for r in results
            ],
        }

    async def _run_analyze_image(self, args: dict[str, Any]) -> dict[str, Any]:
        """Analyze an image using Claude's vision capabilities.

        Args:
            args: ``image_path`` (str, required) and ``prompt``
                (str, optional).

        Returns:
            Dict with analysis text.

        """
        import base64
        import os

        from attune.security.path_validation import _validate_file_path

        image_path = args.get("image_path", "")
        if not image_path:
            return {"success": False, "error": "image_path is required"}

        # Validate path
        validated_path = _validate_file_path(image_path, allowed_dir=self._workspace_root)

        # Check file exists
        if not validated_path.exists():
            return {"success": False, "error": f"File not found: {image_path}"}

        # Check file size (max 10MB)
        file_size = validated_path.stat().st_size
        max_size = 10 * 1024 * 1024
        if file_size > max_size:
            return {"success": False, "error": f"File too large ({file_size} bytes). Max: 10MB"}

        # Detect MIME type
        suffix = validated_path.suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = mime_map.get(suffix)
        if not media_type:
            return {
                "success": False,
                "error": f"Unsupported image format: {suffix}. Supported: png, jpg, gif, webp",
            }

        # Check for API key
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return {"success": False, "error": "ANTHROPIC_API_KEY not set"}

        # Read and encode image
        image_data = base64.b64encode(validated_path.read_bytes()).decode("utf-8")

        prompt = args.get(
            "prompt",
            "Analyze this image and describe what you see, focusing on any errors, issues, or notable elements.",
        )

        # Call Anthropic API with vision
        try:
            from attune.llm.providers.anthropic import AnthropicProvider

            provider = AnthropicProvider(api_key=api_key)
            response = await provider.generate(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    },
                ],
            )

            return {
                "success": True,
                "analysis": response.content if hasattr(response, "content") else str(response),
                "image_path": str(validated_path),
                "media_type": media_type,
                "file_size_bytes": file_size,
            }

        except ImportError as e:
            return {"success": False, "error": f"Anthropic provider unavailable: {e}"}
        except (ConnectionError, TimeoutError) as e:
            return {"success": False, "error": f"API connection failed: {e}"}
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Vision analysis is best-effort
            logger.exception("Image analysis failed")
            return {"success": False, "error": "Image analysis failed"}

    async def _run_rag_knowledge_query(self, args: dict[str, Any]) -> dict[str, Any]:
        """Query the RAG corpus and return hits + augmented prompt.

        Does NOT call an LLM. Callers feed the augmented prompt
        to whatever LLM they want (or use the rag-code-gen
        workflow for end-to-end generation).

        Args:
            args: ``query`` (str, required) and ``k`` (int,
                optional, default 3, 1-10).

        Returns:
            Dict with ``fallback_used``, ``confidence``,
            ``elapsed_ms``, ``corpus``, ``retriever``,
            ``augmented_prompt``, and ``hits`` (list of
            path/category/score/excerpt).
        """
        query = args.get("query", "")
        if not query or not isinstance(query, str) or not query.strip():
            return {"success": False, "error": "query is required"}

        try:
            k = int(args.get("k", 3))
        except (TypeError, ValueError):
            return {"success": False, "error": "k must be an integer"}
        if k < 1 or k > 10:
            return {"success": False, "error": "k must be between 1 and 10"}

        try:
            from attune_rag import RagPipeline
        except ImportError as exc:
            # attune-rag is a CORE dependency (the legacy [rag] extra
            # is an empty back-compat placeholder — pointing users at
            # it would install nothing).
            return {
                "success": False,
                "error": (
                    "rag_knowledge_query needs the attune-rag package, "
                    "a core dependency this environment is missing. "
                    "Reinstall with: pip install attune-rag"
                ),
                "cause": str(exc),
            }

        try:
            pipeline = RagPipeline()
            result = pipeline.run(query, k=k)
        except RuntimeError as exc:
            # Typical cause: AttuneHelpCorpus can't find attune-help.
            # Name the package directly so the fix is one command (the
            # [author] extra that used to ship it was retired in T4).
            hint = ""
            if "attune-help" in str(exc) or "attune_help" in str(exc):
                hint = " (install it with: pip install attune-help)"
            return {"success": False, "error": f"RAG setup error: {exc}{hint}"}
        except Exception:  # noqa: BLE001
            # INTENTIONAL: best-effort — return structured error
            logger.exception("RAG knowledge query failed")
            return {"success": False, "error": "RAG query failed"}

        return {
            "success": True,
            "query": query,
            "fallback_used": result.fallback_used,
            "confidence": result.confidence,
            "elapsed_ms": result.elapsed_ms,
            "corpus": pipeline.corpus.name,
            "retriever": type(pipeline.retriever).__name__,
            "augmented_prompt": result.augmented_prompt,
            "hits": [
                {
                    "template_path": hit.template_path,
                    "category": hit.category,
                    "score": hit.score,
                    "excerpt": hit.excerpt,
                }
                for hit in result.citation.hits
            ],
        }
