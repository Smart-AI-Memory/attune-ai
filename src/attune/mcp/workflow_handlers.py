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
    simplify-code, secure-release, health-check, and
    research-synthesis.
    """

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
        result = await workflow.execute(project_root=args.get("path", "."))

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
        source_path = args.get("source_path", "")
        if source_path:
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
            context={"project_root": args.get("path", ".")},
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
        result = await workflow.execute(src_path=args.get("path", "src/"))

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
        result = await workflow.execute(path=args.get("path", "."))

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
        result = await workflow.execute(path=args.get("path", "."))

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
        result = await workflow.execute(path=args.get("path", "."))

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
        result = await workflow.execute(path=args.get("path", "."))

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
            project_root=args.get("project_root", "."),
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
