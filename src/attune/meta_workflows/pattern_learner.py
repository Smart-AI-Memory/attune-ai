"""Pattern learning from historical meta-workflow executions.

Analyzes saved execution results to generate insights and recommendations
for optimizing future workflows.

Hybrid Storage:
- File-based storage: Persistent, human-readable execution results
- Memory-based storage: Rich semantic queries, relationship modeling

Created: 2026-01-17
Purpose: Self-optimizing meta-workflows through pattern analysis
"""

import logging
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from attune.meta_workflows.models import PatternInsight
from attune.meta_workflows.pattern_memory import PatternMemoryMixin
from attune.meta_workflows.pattern_reporting import print_analytics_report  # noqa: F401
from attune.meta_workflows.workflow import list_execution_results, load_execution_result

if TYPE_CHECKING:
    from attune.memory.unified import UnifiedMemory

logger = logging.getLogger(__name__)


class PatternLearner(PatternMemoryMixin):
    """Analyzes historical workflow executions to generate insights.

    Learns patterns from past executions to recommend optimizations
    for future workflows.

    Hybrid Architecture:
    - Files: Persistent storage of execution results
    - Memory: Rich semantic queries and relationship modeling

    Attributes:
        executions_dir: Directory where execution results are stored
        memory: Optional UnifiedMemory instance for enhanced querying

    """

    def __init__(
        self,
        executions_dir: str | None = None,
        memory: "UnifiedMemory | None" = None,
    ):
        """Initialize pattern learner with hybrid storage.

        Args:
            executions_dir: Directory for execution results
                           (default: .attune/meta_workflows/executions/)
            memory: Optional UnifiedMemory instance for enhanced querying
                   If provided, insights will be stored in both files and memory

        """
        if executions_dir is None:
            executions_dir = str(Path.home() / ".attune" / "meta_workflows" / "executions")
        self.executions_dir = Path(executions_dir)
        self.memory = memory

        logger.info(
            f"Pattern learner initialized: {self.executions_dir}",
            extra={"memory_enabled": memory is not None},
        )

    def analyze_patterns(
        self,
        template_id: str | None = None,
        min_confidence: float = 0.5,
    ) -> list[PatternInsight]:
        """Analyze patterns from historical executions.

        Args:
            template_id: Optional template ID to filter by
            min_confidence: Minimum confidence threshold (0.0-1.0)

        Returns:
            List of pattern insights

        """
        run_ids = list_execution_results(storage_dir=str(self.executions_dir))

        if not run_ids:
            logger.warning("No execution results found")
            return []

        results = []
        for run_id in run_ids:
            try:
                result = load_execution_result(run_id, storage_dir=str(self.executions_dir))
                if template_id is None or result.template_id == template_id:
                    results.append(result)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to load result {run_id}: {e}")

        if not results:
            logger.warning(f"No results found for template: {template_id}")
            return []

        logger.info(f"Analyzing {len(results)} execution(s)")

        insights = []
        insights.extend(self._analyze_agent_counts(results))
        insights.extend(self._analyze_tier_performance(results))
        insights.extend(self._analyze_costs(results))
        insights.extend(self._analyze_failures(results))

        insights = [i for i in insights if i.confidence >= min_confidence]

        logger.info(f"Generated {len(insights)} insights")
        return insights

    def _analyze_agent_counts(self, results: list) -> list[PatternInsight]:
        """Analyze patterns in agent counts.

        Args:
            results: List of workflow results

        Returns:
            List of insights about agent counts

        """
        insights = []
        agent_counts = [len(r.agents_created) for r in results]

        if not agent_counts:
            return insights

        avg_count = sum(agent_counts) / len(agent_counts)
        min_count = min(agent_counts)
        max_count = max(agent_counts)
        confidence = min(len(results) / 10.0, 1.0)

        insights.append(
            PatternInsight(
                insight_type="agent_count",
                description=(
                    f"Average {avg_count:.1f} agents per workflow "
                    f"(range: {min_count}-{max_count})"
                ),
                confidence=confidence,
                data={
                    "average": avg_count,
                    "min": min_count,
                    "max": max_count,
                    "counts": agent_counts,
                },
                sample_size=len(results),
            ),
        )

        return insights

    def _analyze_tier_performance(self, results: list) -> list[PatternInsight]:
        """Analyze tier performance patterns.

        Args:
            results: List of workflow results

        Returns:
            List of insights about tier performance

        """
        insights = []
        tier_stats = defaultdict(lambda: {"success": 0, "total": 0, "costs": []})

        for result in results:
            for agent_result in result.agent_results:
                key = f"{agent_result.role}:{agent_result.tier_used}"
                tier_stats[key]["total"] += 1
                if agent_result.success:
                    tier_stats[key]["success"] += 1
                tier_stats[key]["costs"].append(agent_result.cost)

        for key, stats in tier_stats.items():
            if stats["total"] >= 3:
                role, tier = key.split(":")
                success_rate = stats["success"] / stats["total"]
                avg_cost = sum(stats["costs"]) / len(stats["costs"])
                confidence = min(stats["total"] / 10.0, 1.0)

                insights.append(
                    PatternInsight(
                        insight_type="tier_performance",
                        description=(
                            f"{role} succeeds {success_rate:.0%} at {tier} tier "
                            f"(avg cost: ${avg_cost:.2f})"
                        ),
                        confidence=confidence,
                        data={
                            "role": role,
                            "tier": tier,
                            "success_rate": success_rate,
                            "avg_cost": avg_cost,
                            "total_runs": stats["total"],
                        },
                        sample_size=stats["total"],
                    ),
                )

        return insights

    def _analyze_costs(self, results: list) -> list[PatternInsight]:
        """Analyze cost patterns.

        Args:
            results: List of workflow results

        Returns:
            List of insights about costs

        """
        insights = []

        if not results:
            return insights

        total_costs = [r.total_cost for r in results]
        avg_cost = sum(total_costs) / len(total_costs)
        min_cost = min(total_costs)
        max_cost = max(total_costs)

        tier_costs: dict[str, list[float]] = defaultdict(list)
        for result in results:
            for agent_result in result.agent_results:
                tier_costs[agent_result.tier_used].append(agent_result.cost)

        tier_breakdown = {}
        for tier, costs in tier_costs.items():
            tier_breakdown[tier] = {
                "avg": sum(costs) / len(costs),
                "total": sum(costs),
                "count": len(costs),
            }

        confidence = min(len(results) / 10.0, 1.0)

        insights.append(
            PatternInsight(
                insight_type="cost_analysis",
                description=(
                    f"Average workflow cost ${avg_cost:.2f} "
                    f"(range: ${min_cost:.2f}-${max_cost:.2f})"
                ),
                confidence=confidence,
                data={
                    "average": avg_cost,
                    "min": min_cost,
                    "max": max_cost,
                    "tier_breakdown": tier_breakdown,
                },
                sample_size=len(results),
            ),
        )

        return insights

    def _analyze_failures(self, results: list) -> list[PatternInsight]:
        """Analyze failure patterns.

        Args:
            results: List of workflow results

        Returns:
            List of insights about failures

        """
        insights = []
        failed_agents: dict[str, int] = defaultdict(int)
        total_agents: dict[str, int] = defaultdict(int)

        for result in results:
            for agent_result in result.agent_results:
                total_agents[agent_result.role] += 1
                if not agent_result.success:
                    failed_agents[agent_result.role] += 1

        for role, failure_count in failed_agents.items():
            total = total_agents[role]
            failure_rate = failure_count / total
            confidence = min(total / 10.0, 1.0)

            insights.append(
                PatternInsight(
                    insight_type="failure_analysis",
                    description=(
                        f"{role} fails {failure_rate:.0%} of the time " f"({failure_count}/{total})"
                    ),
                    confidence=confidence,
                    data={
                        "role": role,
                        "failure_count": failure_count,
                        "total_runs": total,
                        "failure_rate": failure_rate,
                    },
                    sample_size=total,
                ),
            )

        return insights

    def get_recommendations(self, template_id: str, min_confidence: float = 0.7) -> list[str]:
        """Get actionable recommendations for a template.

        Args:
            template_id: Template ID to get recommendations for
            min_confidence: Minimum confidence for recommendations

        Returns:
            List of recommendation strings

        """
        insights = self.analyze_patterns(template_id=template_id, min_confidence=min_confidence)

        recommendations = []

        for insight in insights:
            if insight.insight_type == "tier_performance":
                role = insight.data["role"]
                tier = insight.data["tier"]
                success_rate = insight.data["success_rate"]

                if success_rate >= 0.9:
                    recommendations.append(
                        f"{role} works well at {tier} tier ({success_rate:.0%} success)",
                    )
                elif success_rate < 0.6:
                    recommendations.append(
                        f"{role} struggles at {tier} tier "
                        f"({success_rate:.0%} success) - consider upgrading tier",
                    )

            elif insight.insight_type == "cost_analysis":
                avg_cost = insight.data["average"]
                recommendations.append(f"Expected workflow cost: ${avg_cost:.2f}")

            elif insight.insight_type == "failure_analysis":
                role = insight.data["role"]
                failure_rate = insight.data["failure_rate"]
                if failure_rate > 0.3:
                    recommendations.append(
                        f"{role} needs attention ({failure_rate:.0%} failure rate)",
                    )

        return recommendations

    def generate_analytics_report(self, template_id: str | None = None) -> dict[str, Any]:
        """Generate comprehensive analytics report.

        Args:
            template_id: Optional template ID to filter by

        Returns:
            Dictionary with analytics data

        """
        insights = self.analyze_patterns(template_id=template_id, min_confidence=0.0)

        insights_by_type: dict[str, list[PatternInsight]] = defaultdict(list)
        for insight in insights:
            insights_by_type[insight.insight_type].append(insight)

        run_ids = list_execution_results(storage_dir=str(self.executions_dir))
        results = []
        for run_id in run_ids:
            try:
                result = load_execution_result(run_id, storage_dir=str(self.executions_dir))
                if template_id is None or result.template_id == template_id:
                    results.append(result)
            except Exception:  # noqa: BLE001
                continue

        total_runs = len(results)
        successful_runs = sum(1 for r in results if r.success)
        total_cost = sum(r.total_cost for r in results)
        total_agents_count = sum(len(r.agents_created) for r in results)

        report = {
            "summary": {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "success_rate": successful_runs / total_runs if total_runs > 0 else 0,
                "total_cost": total_cost,
                "avg_cost_per_run": total_cost / total_runs if total_runs > 0 else 0,
                "total_agents_created": total_agents_count,
                "avg_agents_per_run": total_agents_count / total_runs if total_runs > 0 else 0,
            },
            "insights": {
                insight_type: [i.to_dict() for i in insights_list]
                for insight_type, insights_list in insights_by_type.items()
            },
            "recommendations": self.get_recommendations(template_id) if template_id else [],
        }

        return report
