"""Performance Audit Workflow

Identifies performance bottlenecks and optimization opportunities
through static analysis.

Stages:
1. profile (CHEAP) - Static analysis for common perf anti-patterns
2. analyze (CAPABLE) - Deep analysis of algorithmic complexity
3. hotspots (CAPABLE) - Identify performance hotspots
4. optimize (PREMIUM) - Generate optimization recommendations (conditional)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from typing import Any

from .base import BaseWorkflow, ModelTier
from .context import WorkflowContext
from .output import get_console
from .perf_audit_optimize_mixin import PerfAuditOptimizeMixin
from .perf_audit_patterns import (
    OPTIMIZATION_ACTIONS,
    PERF_AUDIT_STEPS,
    PERF_PATTERNS,
)
from .perf_audit_report import (
    create_perf_audit_workflow_report,
    format_perf_audit_report,
)
from .perf_audit_stages_mixin import PerfAuditAnalysisMixin
from .services import ParsingService, PromptService
from .validation import InputSchema

# Re-export public API for backward compatibility
__all__ = [
    "PERF_AUDIT_STEPS",
    "PERF_PATTERNS",
    "PerformanceAuditWorkflow",
    "create_perf_audit_workflow_report",
    "format_perf_audit_report",
    "main",
]


class PerformanceAuditWorkflow(PerfAuditOptimizeMixin, PerfAuditAnalysisMixin, BaseWorkflow):
    """Identify performance bottlenecks and optimization opportunities.

    Uses static analysis to find common performance anti-patterns
    and algorithmic complexity issues.

    Supports composition via ``WorkflowContext`` -- use
    ``default_context()`` to get a pre-configured context with
    prompt and parsing services.
    """

    name = "perf-audit"
    description = "Identify performance bottlenecks and optimization opportunities"
    stages = ["profile", "analyze", "hotspots", "optimize"]
    tier_map = {
        "profile": ModelTier.CHEAP,
        "analyze": ModelTier.CAPABLE,
        "hotspots": ModelTier.CAPABLE,
        "optimize": ModelTier.PREMIUM,
    }
    input_schema = InputSchema(
        required_fields={"path": str},
    )

    def __init__(
        self,
        min_hotspots_for_premium: int = 3,
        enable_auth_strategy: bool = True,
        **kwargs: Any,
    ):
        """Initialize performance audit workflow.

        Args:
            min_hotspots_for_premium: Minimum hotspots to
                trigger premium optimization
            enable_auth_strategy: Enable intelligent auth
                routing (default: True)
            **kwargs: Additional arguments passed to
                BaseWorkflow

        """
        super().__init__(**kwargs)
        self.min_hotspots_for_premium = min_hotspots_for_premium
        self.enable_auth_strategy = enable_auth_strategy
        self._hotspot_count: int = 0
        self._auth_mode_used: str | None = None

    @classmethod
    def default_context(cls, xml_config: dict | None = None) -> WorkflowContext:
        """Create a WorkflowContext pre-configured for performance auditing.

        Args:
            xml_config: Optional XML prompt configuration dict.
                Defaults to XML disabled -- benchmarks on
                Claude 4.x show +30% cost overhead with no
                quality improvement for perf audit.

        Returns:
            WorkflowContext with prompt and parsing services.

        """
        if xml_config is None:
            xml_config = {"enabled": False}
        return WorkflowContext(
            prompt=PromptService("perf-audit", xml_config=xml_config),
            parsing=ParsingService(xml_config=xml_config),
        )

    def should_skip_stage(self, stage_name: str, input_data: Any) -> tuple[bool, str | None]:
        """Downgrade optimize stage if few hotspots.

        Args:
            stage_name: Name of the stage to check
            input_data: Current workflow data

        Returns:
            Tuple of (should_skip, reason)

        """
        if stage_name == "optimize":
            if self._hotspot_count < self.min_hotspots_for_premium:
                self.tier_map["optimize"] = ModelTier.CAPABLE
                return False, None
        return False, None

    def _get_optimization_action(self, concern: str) -> dict | None:
        """Generate specific optimization action for a concern type.

        Args:
            concern: The concern type identifier

        Returns:
            Action dict with action, description, and
            estimated_impact, or None if unknown concern.

        """
        return OPTIMIZATION_ACTIONS.get(concern)


def main() -> None:
    """CLI entry point for performance audit workflow."""
    import asyncio

    async def run() -> None:
        """Run the performance audit analysis stage."""
        workflow = PerformanceAuditWorkflow()
        result = await workflow.execute(path=".", file_types=[".py"])

        output = result.final_output

        # Try Rich output first
        console = get_console()
        workflow_report = output.get("workflow_report")

        if console and workflow_report:
            # Render with Rich
            workflow_report.render(console, use_rich=True)
            console.print()
            console.print(f"[dim]Provider: {result.provider}[/dim]")
            console.print("[dim]Cost: " f"${result.cost_report.total_cost:.4f}" "[/dim]")
            savings = result.cost_report.savings
            pct = result.cost_report.savings_percent
            console.print(f"[dim]Savings: ${savings:.4f} ({pct:.1f}%)[/dim]")
        else:
            # Fallback to plain text
            print("\nPerformance Audit Results")
            print("=" * 50)
            print(f"Provider: {result.provider}")
            print(f"Success: {result.success}")

            print("Performance Level: " f"{output.get('perf_level', 'N/A')}")
            print("Performance Score: " f"{output.get('perf_score', 0)}/100")
            print("Recommendations: " f"{output.get('recommendation_count', 0)}")

            if output.get("top_issues"):
                print("\nTop Issues:")
                for issue in output["top_issues"]:
                    print(f"  - {issue['type']}: {issue['count']} occurrences")

            print("\nCost Report:")
            print("  Total Cost: " f"${result.cost_report.total_cost:.4f}")
            savings = result.cost_report.savings
            pct = result.cost_report.savings_percent
            print(f"  Savings: ${savings:.4f} ({pct:.1f}%)")

    asyncio.run(run())


if __name__ == "__main__":
    main()
