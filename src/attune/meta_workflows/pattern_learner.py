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
from attune.meta_workflows.workflow import list_execution_results, load_execution_result

if TYPE_CHECKING:
    from attune.memory.unified import UnifiedMemory
    from attune.meta_workflows.models import FormResponse
    from attune.meta_workflows.workflow import MetaWorkflowResult

logger = logging.getLogger(__name__)


class PatternLearner:
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
        self, template_id: str | None = None, min_confidence: float = 0.5
    ) -> list[PatternInsight]:
        """Analyze patterns from historical executions.

        Args:
            template_id: Optional template ID to filter by
            min_confidence: Minimum confidence threshold (0.0-1.0)

        Returns:
            List of pattern insights
        """
        # Load all execution results
        run_ids = list_execution_results(storage_dir=str(self.executions_dir))

        if not run_ids:
            logger.warning("No execution results found")
            return []

        # Filter by template if specified
        results = []
        for run_id in run_ids:
            try:
                result = load_execution_result(run_id, storage_dir=str(self.executions_dir))
                if template_id is None or result.template_id == template_id:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Failed to load result {run_id}: {e}")

        if not results:
            logger.warning(f"No results found for template: {template_id}")
            return []

        logger.info(f"Analyzing {len(results)} execution(s)")

        # Generate insights
        insights = []

        # 1. Agent count patterns
        insights.extend(self._analyze_agent_counts(results))

        # 2. Tier performance patterns
        insights.extend(self._analyze_tier_performance(results))

        # 3. Cost patterns
        insights.extend(self._analyze_costs(results))

        # 4. Common failures
        insights.extend(self._analyze_failures(results))

        # Filter by confidence
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

        # Calculate confidence based on sample size
        confidence = min(len(results) / 10.0, 1.0)

        insights.append(
            PatternInsight(
                insight_type="agent_count",
                description=f"Average {avg_count:.1f} agents per workflow (range: {min_count}-{max_count})",
                confidence=confidence,
                data={
                    "average": avg_count,
                    "min": min_count,
                    "max": max_count,
                    "counts": agent_counts,
                },
                sample_size=len(results),
            )
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

        # Track success rate by agent role and tier
        tier_stats = defaultdict(lambda: {"success": 0, "total": 0, "costs": []})

        for result in results:
            for agent_result in result.agent_results:
                key = f"{agent_result.role}:{agent_result.tier_used}"
                tier_stats[key]["total"] += 1
                if agent_result.success:
                    tier_stats[key]["success"] += 1
                tier_stats[key]["costs"].append(agent_result.cost)

        # Generate insights for agents with enough data
        for key, stats in tier_stats.items():
            if stats["total"] >= 3:  # Minimum 3 samples
                role, tier = key.split(":")
                success_rate = stats["success"] / stats["total"]
                avg_cost = sum(stats["costs"]) / len(stats["costs"])

                confidence = min(stats["total"] / 10.0, 1.0)

                insights.append(
                    PatternInsight(
                        insight_type="tier_performance",
                        description=f"{role} succeeds {success_rate:.0%} at {tier} tier (avg cost: ${avg_cost:.2f})",
                        confidence=confidence,
                        data={
                            "role": role,
                            "tier": tier,
                            "success_rate": success_rate,
                            "avg_cost": avg_cost,
                            "total_runs": stats["total"],
                        },
                        sample_size=stats["total"],
                    )
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

        # Calculate cost by tier
        tier_costs = defaultdict(list)
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
                description=f"Average workflow cost ${avg_cost:.2f} (range: ${min_cost:.2f}-${max_cost:.2f})",
                confidence=confidence,
                data={
                    "average": avg_cost,
                    "min": min_cost,
                    "max": max_cost,
                    "tier_breakdown": tier_breakdown,
                },
                sample_size=len(results),
            )
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

        failed_agents = defaultdict(int)
        total_agents = defaultdict(int)

        for result in results:
            for agent_result in result.agent_results:
                total_agents[agent_result.role] += 1
                if not agent_result.success:
                    failed_agents[agent_result.role] += 1

        # Find agents with failures
        for role, failure_count in failed_agents.items():
            if failure_count > 0:
                total = total_agents[role]
                failure_rate = failure_count / total

                confidence = min(total / 10.0, 1.0)

                insights.append(
                    PatternInsight(
                        insight_type="failure_analysis",
                        description=f"{role} fails {failure_rate:.0%} of the time ({failure_count}/{total})",
                        confidence=confidence,
                        data={
                            "role": role,
                            "failure_count": failure_count,
                            "total_runs": total,
                            "failure_rate": failure_rate,
                        },
                        sample_size=total,
                    )
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
                        f"✓ {role} works well at {tier} tier ({success_rate:.0%} success)"
                    )
                elif success_rate < 0.6:
                    recommendations.append(
                        f"⚠ {role} struggles at {tier} tier ({success_rate:.0%} success) - consider upgrading tier"
                    )

            elif insight.insight_type == "cost_analysis":
                avg_cost = insight.data["average"]
                recommendations.append(f"💰 Expected workflow cost: ${avg_cost:.2f}")

            elif insight.insight_type == "failure_analysis":
                role = insight.data["role"]
                failure_rate = insight.data["failure_rate"]
                if failure_rate > 0.3:
                    recommendations.append(
                        f"🔧 {role} needs attention ({failure_rate:.0%} failure rate)"
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

        # Group insights by type
        insights_by_type = defaultdict(list)
        for insight in insights:
            insights_by_type[insight.insight_type].append(insight)

        # Load all results for summary stats
        run_ids = list_execution_results(storage_dir=str(self.executions_dir))
        results = []
        for run_id in run_ids:
            try:
                result = load_execution_result(run_id, storage_dir=str(self.executions_dir))
                if template_id is None or result.template_id == template_id:
                    results.append(result)
            except Exception:
                continue

        # Calculate summary statistics
        total_runs = len(results)
        successful_runs = sum(1 for r in results if r.success)
        total_cost = sum(r.total_cost for r in results)
        total_agents = sum(len(r.agents_created) for r in results)

        report = {
            "summary": {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "success_rate": successful_runs / total_runs if total_runs > 0 else 0,
                "total_cost": total_cost,
                "avg_cost_per_run": total_cost / total_runs if total_runs > 0 else 0,
                "total_agents_created": total_agents,
                "avg_agents_per_run": total_agents / total_runs if total_runs > 0 else 0,
            },
            "insights": {
                insight_type: [i.to_dict() for i in insights_list]
                for insight_type, insights_list in insights_by_type.items()
            },
            "recommendations": self.get_recommendations(template_id) if template_id else [],
        }

        return report

    # =========================================================================
    # MEMORY INTEGRATION
    # =========================================================================

    def store_execution_in_memory(self, result: "MetaWorkflowResult") -> str | None:
        """Store execution result in memory for semantic querying.

        This stores execution insights in long-term memory IN ADDITION to
        file-based storage. Memory enables rich semantic queries like:
        - "Find workflows that succeeded with test coverage >80%"
        - "Show me all workflows that used progressive tier escalation"

        Args:
            result: MetaWorkflowResult to store

        Returns:
            Pattern ID if stored successfully, None otherwise
        """
        if not self.memory:
            logger.debug("Memory not available, skipping memory storage")
            return None

        try:
            # Calculate tier distribution
            tier_counts = defaultdict(int)
            for agent_result in result.agent_results:
                tier_counts[agent_result.tier_used] += 1

            # Create rich metadata for semantic querying
            metadata = {
                "run_id": result.run_id,
                "template_id": result.template_id,
                "success": result.success,
                "total_cost": result.total_cost,
                "total_duration": result.total_duration,
                "agents_created": len(result.agents_created),
                "agents_succeeded": sum(1 for a in result.agent_results if a.success),
                "tier_distribution": dict(tier_counts),
                "form_responses": result.form_responses.responses,
                "timestamp": result.timestamp,
                "error": result.error,
            }

            # Create searchable content
            content = f"""Meta-workflow execution: {result.template_id}
Run ID: {result.run_id}
Status: {"SUCCESS" if result.success else "FAILED"}
Agents created: {len(result.agents_created)}
Total cost: ${result.total_cost:.2f}
Duration: {result.total_duration:.1f}s

Agents:
{self._format_agents_for_content(result)}

Form Responses:
{self._format_responses_for_content(result.form_responses.responses)}
"""

            # Store in long-term memory
            storage_result = self.memory.persist_pattern(
                content=content,
                pattern_type="meta_workflow_execution",
                classification="INTERNAL",  # Workflow metadata is internal
                auto_classify=False,
                metadata=metadata,
            )

            if storage_result:
                pattern_id = storage_result.get("pattern_id")
                logger.info(
                    f"Execution stored in memory: {pattern_id}",
                    extra={
                        "run_id": result.run_id,
                        "template_id": result.template_id,
                    },
                )
                return pattern_id

            return None

        except Exception as e:
            logger.error(f"Failed to store execution in memory: {e}")
            return None

    def _format_agents_for_content(self, result: "MetaWorkflowResult") -> str:
        """Format agents for searchable content."""
        lines = []
        for agent_result in result.agent_results:
            status = "✅" if agent_result.success else "❌"
            lines.append(
                f"- {status} {agent_result.role} (tier: {agent_result.tier_used}, "
                f"cost: ${agent_result.cost:.2f})"
            )
        return "\n".join(lines)

    def _format_responses_for_content(self, responses: dict) -> str:
        """Format form responses for searchable content."""
        lines = []
        for key, value in responses.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def search_executions_by_context(
        self,
        query: str,
        template_id: str | None = None,
        limit: int = 10,
    ) -> list["MetaWorkflowResult"]:
        """Search executions using semantic memory queries.

        This provides richer querying than file-based search:
        - Natural language queries
        - Semantic similarity matching
        - Cross-template pattern recognition

        Args:
            query: Natural language search query
                  e.g., "workflows with high test coverage"
            template_id: Optional filter by template
            limit: Maximum results to return

        Returns:
            List of matching MetaWorkflowResult objects

        Example:
            >>> learner.search_executions_by_context(
            ...     "successful workflows with test coverage > 80%",
            ...     limit=5
            ... )
        """
        if not self.memory:
            logger.warning("Memory not available, falling back to file-based search")
            return self._search_executions_files(query, template_id, limit)

        try:
            # Search memory patterns
            patterns = self.memory.search_patterns(
                query=query,
                pattern_type="meta_workflow_execution",
                limit=limit,
            )

            # Convert to MetaWorkflowResult objects
            results = []
            for pattern in patterns:
                metadata = pattern.get("metadata", {})
                run_id = metadata.get("run_id")

                if run_id:
                    # Filter by template if specified
                    if template_id and metadata.get("template_id") != template_id:
                        continue

                    # Load full result from files
                    try:
                        result = load_execution_result(run_id, storage_dir=str(self.executions_dir))
                        results.append(result)
                    except FileNotFoundError:
                        logger.warning(f"Result file not found for run_id: {run_id}")
                        continue

            return results

        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return self._search_executions_files(query, template_id, limit)

    def _search_executions_files(
        self,
        query: str,
        template_id: str | None,
        limit: int,
    ) -> list["MetaWorkflowResult"]:
        """Fallback file-based search when memory is unavailable."""
        # Simple keyword search in file-based storage
        results = []
        run_ids = list_execution_results(storage_dir=str(self.executions_dir))

        for run_id in run_ids[:limit]:
            try:
                result = load_execution_result(run_id, storage_dir=str(self.executions_dir))

                # Filter by template
                if template_id and result.template_id != template_id:
                    continue

                # Simple keyword matching
                result_json = result.to_json().lower()
                if query.lower() in result_json:
                    results.append(result)

            except Exception as e:
                logger.warning(f"Failed to load result {run_id}: {e}")
                continue

        return results[:limit]

    def get_smart_recommendations(
        self,
        template_id: str,
        form_response: "FormResponse | None" = None,
        min_confidence: float = 0.7,
    ) -> list[str]:
        """Get context-aware recommendations enhanced by memory.

        Combines statistical pattern analysis with semantic memory queries
        to provide more intelligent recommendations.

        Args:
            template_id: Template ID to get recommendations for
            form_response: Optional form responses for context-aware suggestions
            min_confidence: Minimum confidence threshold

        Returns:
            List of recommendation strings

        Example:
            >>> recommendations = learner.get_smart_recommendations(
            ...     "python_package_publish",
            ...     form_response=response,
            ...     min_confidence=0.7
            ... )
        """
        # Get base recommendations from statistical analysis
        base_recs = self.get_recommendations(template_id, min_confidence)

        # If no memory, return base recommendations
        if not self.memory or not form_response:
            return base_recs

        # Enhance with memory-based context
        try:
            # Find similar past executions
            query = f"Successful workflows for {template_id}"
            if form_response:
                # Add context from form responses
                key_responses = []
                for key, value in form_response.responses.items():
                    key_responses.append(f"{key}={value}")
                query += f" with {', '.join(key_responses[:3])}"

            similar_executions = self.search_executions_by_context(
                query=query,
                template_id=template_id,
                limit=5,
            )

            # Generate memory-enhanced recommendations
            if similar_executions:
                success_rate = sum(1 for e in similar_executions if e.success) / len(
                    similar_executions
                )

                if success_rate >= 0.8:
                    base_recs.insert(
                        0,
                        f"📊 {len(similar_executions)} similar workflows found "
                        f"with {success_rate:.0%} success rate",
                    )

                # Add tier recommendations from similar executions
                tier_usage = defaultdict(int)
                for execution in similar_executions:
                    for agent_result in execution.agent_results:
                        tier_usage[agent_result.tier_used] += 1

                if tier_usage:
                    most_common_tier = max(tier_usage.items(), key=lambda x: x[1])[0]
                    base_recs.append(
                        f"💡 Similar workflows typically use '{most_common_tier}' tier"
                    )

        except Exception as e:
            logger.error(f"Failed to enhance recommendations with memory: {e}")

        return base_recs


# =============================================================================
# Helper functions
# =============================================================================


def print_analytics_report(report: dict[str, Any]) -> None:
    """Print analytics report in human-readable format.

    Args:
        report: Analytics report dictionary
    """
    print("\n" + "=" * 70)
    print("META-WORKFLOW ANALYTICS REPORT")
    print("=" * 70)

    # Summary
    summary = report["summary"]
    print("\n## Summary")
    print(f"\n  Total Runs: {summary['total_runs']}")
    print(f"  Successful: {summary['successful_runs']} ({summary['success_rate']:.0%})")
    print(f"  Total Cost: ${summary['total_cost']:.2f}")
    print(f"  Avg Cost/Run: ${summary['avg_cost_per_run']:.2f}")
    print(f"  Total Agents: {summary['total_agents_created']}")
    print(f"  Avg Agents/Run: {summary['avg_agents_per_run']:.1f}")

    # Recommendations
    if report.get("recommendations"):
        print("\n## Recommendations")
        print()
        for rec in report["recommendations"]:
            print(f"  {rec}")

    # Insights by type
    insights = report.get("insights", {})

    if insights.get("tier_performance"):
        print("\n## Tier Performance")
        print()
        for insight in insights["tier_performance"]:
            print(f"  • {insight['description']}")
            print(f"    Confidence: {insight['confidence']:.0%} (n={insight['sample_size']})")

    if insights.get("cost_analysis"):
        print("\n## Cost Analysis")
        print()
        for insight in insights["cost_analysis"]:
            print(f"  • {insight['description']}")

    if insights.get("failure_analysis"):
        print("\n## Failure Analysis")
        print()
        for insight in insights["failure_analysis"]:
            print(f"  • {insight['description']}")

    print("\n" + "=" * 70 + "\n")
