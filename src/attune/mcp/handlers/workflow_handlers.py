"""Workflow handler functions for Attune AI MCP Server.

Handles execution of security audit, bug prediction, code review,
test generation, performance audit, and release preparation workflows.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from attune.mcp.server import EmpathyMCPServer

logger = logging.getLogger(__name__)


async def run_security_audit(server: EmpathyMCPServer, args: dict[str, Any]) -> dict[str, Any]:
    """Run security audit workflow."""
    from attune.workflows.security_audit import SecurityAuditWorkflow

    workflow = SecurityAuditWorkflow()
    result = await workflow.execute(path=args["path"])

    return {
        "success": result.success,
        "score": result.final_output.get("health_score"),
        "findings": result.final_output.get("findings", []),
        "cost": result.cost_report.total_cost,
        "provider": result.provider,
    }


async def run_bug_predict(server: EmpathyMCPServer, args: dict[str, Any]) -> dict[str, Any]:
    """Run bug prediction workflow."""
    from attune.workflows.bug_predict import BugPredictWorkflow

    workflow = BugPredictWorkflow()
    result = await workflow.execute(path=args["path"])

    return {
        "success": result.success,
        "predictions": result.final_output.get("predictions", []),
        "cost": result.cost_report.total_cost,
    }


async def run_code_review(server: EmpathyMCPServer, args: dict[str, Any]) -> dict[str, Any]:
    """Run code review workflow."""
    from attune.workflows.code_review import CodeReviewWorkflow

    workflow = CodeReviewWorkflow()
    result = await workflow.execute(target_path=args["path"])

    return {
        "success": result.success,
        "feedback": result.final_output.get("feedback"),
        "score": result.final_output.get("quality_score"),
        "cost": result.cost_report.total_cost,
    }


async def run_test_generation(server: EmpathyMCPServer, args: dict[str, Any]) -> dict[str, Any]:
    """Run test generation workflow."""
    from attune.workflows.test_gen import TestGenerationWorkflow

    workflow = TestGenerationWorkflow()
    result = await workflow.execute(module_path=args["module"])

    return {
        "success": result.success,
        "tests_generated": result.final_output.get("tests_generated", 0),
        "output_path": result.final_output.get("output_path"),
        "cost": result.cost_report.total_cost,
    }


async def run_performance_audit(server: EmpathyMCPServer, args: dict[str, Any]) -> dict[str, Any]:
    """Run performance audit workflow."""
    from attune.workflows.perf_audit import PerformanceAuditWorkflow

    workflow = PerformanceAuditWorkflow()
    result = await workflow.execute(path=args["path"])

    return {
        "success": result.success,
        "findings": result.final_output.get("findings", []),
        "score": result.final_output.get("score"),
        "cost": result.cost_report.total_cost,
    }


async def run_release_prep(server: EmpathyMCPServer, args: dict[str, Any]) -> dict[str, Any]:
    """Run release preparation workflow."""
    from attune.workflows.release_prep import ReleasePreparationWorkflow

    workflow = ReleasePreparationWorkflow(skip_approve_if_clean=True)
    result = await workflow.execute(path=args.get("path", "."))

    return {
        "success": result.success,
        "approved": result.final_output.get("approved"),
        "health_score": result.final_output.get("health_score"),
        "recommendation": result.final_output.get("recommendation"),
        "cost": result.cost_report.total_cost,
    }
