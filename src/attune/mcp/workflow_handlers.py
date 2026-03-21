"""Workflow tool handlers for the MCP server.

Exposes 11 additional workflows as MCP tools. Each handler
lazily imports its workflow class, calls execute(), and
extracts relevant fields from the result.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


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
        result = await workflow.execute(project_root=self._validated_path(args))

        return {
            "success": result.success,
            "score": result.final_output.get("score"),
            "findings": result.final_output.get("checks", []),
            "cost": result.cost_report.total_cost,
        }

    # ------------------------------------------------------------------
    # Doc Generation
    # ------------------------------------------------------------------

    async def _run_doc_gen(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run documentation generation workflow.

        Args:
            args: ``source_path`` (required), optional ``doc_type``
                and ``audience``.

        Returns:
            Dict with success and generated document content.

        """
        from attune.workflows.document_gen import DocumentGenerationWorkflow

        source_code = ""
        raw_source_path = args.get("source_path", "")
        if raw_source_path:
            source_path = self._validated_path(args, key="source_path", default="")
            try:
                from pathlib import Path

                source_code = Path(source_path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                logger.warning("Could not read source file %s: %s", source_path, e)

        workflow = DocumentGenerationWorkflow()
        result = await workflow.execute(
            source_code=source_code,
            doc_type=args.get("doc_type", "api_reference"),
            audience=args.get("audience", "developers"),
        )

        return {
            "success": result.success,
            "document": result.final_output.get("document"),
            "sections": result.final_output.get("sections"),
            "cost": result.cost_report.total_cost,
        }

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
        result = await workflow.execute(
            context={"project_root": self._validated_path(args)},
        )

        return {
            "success": getattr(result, "phase", "") == "complete",
            "phase": getattr(result, "phase", "unknown"),
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
        result = await workflow.execute(src_path=self._validated_path(args, default="src/"))

        return {
            "success": result.success,
            "output": result.final_output,
            "cost": result.cost_report.total_cost,
        }

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

        return {
            "success": result.success,
            "total_modules": result.final_output.get("total_modules", 0),
            "completed": result.final_output.get("completed", 0),
            "errors": result.final_output.get("errors", 0),
            "generated_files": result.final_output.get("generated_files", []),
            "cost": result.cost_report.total_cost,
        }

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

        return {
            "success": result.success,
            "output": result.final_output,
            "cost": result.cost_report.total_cost,
        }

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

        return {
            "success": result.success,
            "output": result.final_output,
            "cost": result.cost_report.total_cost,
        }

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

        return {
            "success": result.success,
            "output": result.final_output,
            "cost": result.cost_report.total_cost,
        }

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

        return {
            "success": result.success,
            "output": result.final_output,
            "cost": result.cost_report.total_cost,
        }

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
        result = await workflow.execute(
            project_root=self._validated_path(args, key="project_root"),
        )

        return {
            "success": getattr(result, "success", False),
            "health_score": getattr(result, "overall_health_score", 0),
            "grade": getattr(result, "grade", "unknown"),
            "issues": getattr(result, "issues", []),
            "recommendations": getattr(result, "recommendations", []),
        }

    # ------------------------------------------------------------------
    # Research Synthesis
    # ------------------------------------------------------------------

    async def _run_research_synthesis(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run research synthesis workflow.

        Args:
            args: ``sources`` (list[str], required, min 2) and
                ``question`` (str, required).

        Returns:
            Dict with synthesized answer and key insights.

        """
        from attune.workflows.research_synthesis import (
            ResearchSynthesisWorkflow,
        )

        sources = args.get("sources", [])
        if len(sources) < 2:
            return {
                "success": False,
                "error": "At least 2 sources are required.",
            }

        workflow = ResearchSynthesisWorkflow()
        result = await workflow.execute(
            sources=sources,
            question=args.get("question", ""),
        )

        final = result.final_output if hasattr(result, "final_output") else result
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
                "analysis": response.get("content", str(response)),
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
