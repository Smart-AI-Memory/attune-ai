"""Telemetry analytics and reporting.

Analytics functions for telemetry data analysis.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

import heapq
from datetime import datetime
from typing import Any

from .storage import TelemetryStore


class TelemetryAnalytics:
    """Analytics helpers for telemetry data.

    Provides insights into cost optimization, provider usage, and performance.
    """

    def __init__(self, store: TelemetryStore | None = None):
        """Initialize analytics.

        Args:
            store: TelemetryStore to analyze (creates default if None)

        """
        self.store = store or TelemetryStore()

    def top_expensive_workflows(
        self,
        n: int = 10,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get the most expensive workflows.

        Args:
            n: Number of workflows to return
            since: Only consider workflows after this time

        Returns:
            List of dicts with workflow_name, total_cost, run_count

        """
        workflows = self.store.get_workflows(since=since, limit=10000)

        # Aggregate by workflow name
        costs: dict[str, dict[str, Any]] = {}
        for wf in workflows:
            if wf.workflow_name not in costs:
                costs[wf.workflow_name] = {
                    "workflow_name": wf.workflow_name,
                    "total_cost": 0.0,
                    "run_count": 0,
                    "total_savings": 0.0,
                    "avg_duration_ms": 0,
                }
            costs[wf.workflow_name]["total_cost"] += wf.total_cost
            costs[wf.workflow_name]["run_count"] += 1
            costs[wf.workflow_name]["total_savings"] += wf.savings

        # Calculate averages and sort
        result = list(costs.values())
        for item in result:
            if item["run_count"] > 0:
                item["avg_cost"] = item["total_cost"] / item["run_count"]

        result.sort(key=lambda x: x["total_cost"], reverse=True)
        return result[:n]

    def provider_usage_summary(
        self,
        since: datetime | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Get usage summary by provider.

        Args:
            since: Only consider calls after this time

        Returns:
            Dict mapping provider to usage stats

        """
        calls = self.store.get_calls(since=since, limit=100000)

        summary: dict[str, dict[str, Any]] = {}
        for call in calls:
            if call.provider not in summary:
                summary[call.provider] = {
                    "call_count": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "error_count": 0,
                    "avg_latency_ms": 0,
                    "by_tier": {"cheap": 0, "capable": 0, "premium": 0},
                }

            s = summary[call.provider]
            s["call_count"] += 1
            s["total_tokens"] += call.input_tokens + call.output_tokens
            s["total_cost"] += call.estimated_cost
            if not call.success:
                s["error_count"] += 1
            if call.tier in s["by_tier"]:
                s["by_tier"][call.tier] += 1

        # Calculate averages
        for _provider, stats in summary.items():
            if stats["call_count"] > 0:
                stats["avg_cost"] = stats["total_cost"] / stats["call_count"]

        return summary

    def tier_distribution(
        self,
        since: datetime | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Get call distribution by tier.

        Args:
            since: Only consider calls after this time

        Returns:
            Dict mapping tier to stats

        """
        calls = self.store.get_calls(since=since, limit=100000)

        dist: dict[str, dict[str, Any]] = {
            "cheap": {"count": 0, "cost": 0.0, "tokens": 0},
            "capable": {"count": 0, "cost": 0.0, "tokens": 0},
            "premium": {"count": 0, "cost": 0.0, "tokens": 0},
        }

        for call in calls:
            if call.tier in dist:
                dist[call.tier]["count"] += 1
                dist[call.tier]["cost"] += call.estimated_cost
                dist[call.tier]["tokens"] += call.input_tokens + call.output_tokens

        total_calls = sum(d["count"] for d in dist.values())
        for _tier, stats in dist.items():
            stats["percent"] = (stats["count"] / total_calls * 100) if total_calls > 0 else 0

        return dist

    def fallback_stats(
        self,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Get fallback usage statistics.

        Args:
            since: Only consider calls after this time

        Returns:
            Dict with fallback stats

        """
        calls = self.store.get_calls(since=since, limit=100000)

        total = len(calls)
        fallback_count = sum(1 for c in calls if c.fallback_used)
        error_count = sum(1 for c in calls if not c.success)

        # Count by original provider
        by_provider: dict[str, int] = {}
        for call in calls:
            if call.fallback_used and call.original_provider:
                by_provider[call.original_provider] = by_provider.get(call.original_provider, 0) + 1

        return {
            "total_calls": total,
            "fallback_count": fallback_count,
            "fallback_percent": (fallback_count / total * 100) if total > 0 else 0,
            "error_count": error_count,
            "error_rate": (error_count / total * 100) if total > 0 else 0,
            "by_original_provider": by_provider,
        }

    def sonnet_opus_fallback_analysis(
        self,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Analyze Sonnet 4.5 → Opus 4.5 fallback performance and cost savings.

        Tracks:
        - How often Sonnet 4.5 succeeds vs needs Opus fallback
        - Cost savings from using Sonnet instead of always using Opus
        - Success rates by model

        Args:
            since: Only consider calls after this time

        Returns:
            Dict with fallback analysis and cost savings
        """
        calls = self.store.get_calls(since=since, limit=100000)

        # Filter for Anthropic calls (Sonnet/Opus)
        anthropic_calls = [
            c
            for c in calls
            if c.provider == "anthropic"
            and c.model_id in ["claude-sonnet-4-5-20250929", "claude-opus-4-6"]
        ]

        if not anthropic_calls:
            return {
                "total_calls": 0,
                "sonnet_attempts": 0,
                "sonnet_successes": 0,
                "opus_fallbacks": 0,
                "success_rate_sonnet": 0.0,
                "fallback_rate": 0.0,
                "actual_cost": 0.0,
                "always_opus_cost": 0.0,
                "savings": 0.0,
                "savings_percent": 0.0,
            }

        total = len(anthropic_calls)

        # Count Sonnet attempts and successes
        sonnet_calls = [c for c in anthropic_calls if c.model_id == "claude-sonnet-4-5-20250929"]
        sonnet_successes = sum(1 for c in sonnet_calls if c.success)

        # Count Opus fallbacks (calls with fallback_used and ended up on Opus)
        opus_fallbacks = sum(
            1 for c in anthropic_calls if c.model_id == "claude-opus-4-6" and c.fallback_used
        )

        # Calculate costs
        actual_cost = sum(c.estimated_cost for c in anthropic_calls)

        # Calculate what it would cost if everything used Opus
        opus_input_cost = 15.00 / 1_000_000  # per token
        opus_output_cost = 75.00 / 1_000_000  # per token
        always_opus_cost = sum(
            (c.input_tokens * opus_input_cost) + (c.output_tokens * opus_output_cost)
            for c in anthropic_calls
        )

        savings = always_opus_cost - actual_cost
        savings_percent = (savings / always_opus_cost * 100) if always_opus_cost > 0 else 0

        return {
            "total_calls": total,
            "sonnet_attempts": len(sonnet_calls),
            "sonnet_successes": sonnet_successes,
            "opus_fallbacks": opus_fallbacks,
            "success_rate_sonnet": (
                (sonnet_successes / len(sonnet_calls) * 100) if sonnet_calls else 0.0
            ),
            "fallback_rate": (opus_fallbacks / total * 100) if total > 0 else 0.0,
            "actual_cost": actual_cost,
            "always_opus_cost": always_opus_cost,
            "savings": savings,
            "savings_percent": savings_percent,
            "avg_cost_per_call": actual_cost / total if total > 0 else 0.0,
            "avg_opus_cost_per_call": always_opus_cost / total if total > 0 else 0.0,
        }

    def cost_savings_report(
        self,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Generate cost savings report.

        Args:
            since: Only consider workflows after this time

        Returns:
            Dict with savings analysis

        """
        workflows = self.store.get_workflows(since=since, limit=10000)

        total_cost = sum(wf.total_cost for wf in workflows)
        total_baseline = sum(wf.baseline_cost for wf in workflows)
        total_savings = sum(wf.savings for wf in workflows)

        return {
            "workflow_count": len(workflows),
            "total_actual_cost": total_cost,
            "total_baseline_cost": total_baseline,
            "total_savings": total_savings,
            "savings_percent": (
                (total_savings / total_baseline * 100) if total_baseline > 0 else 0
            ),
            "avg_cost_per_workflow": total_cost / len(workflows) if workflows else 0,
        }

    # Tier 1 automation monitoring analytics

    def task_routing_accuracy(
        self,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Analyze task routing accuracy.

        Args:
            since: Only consider routings after this time

        Returns:
            Dict with routing accuracy metrics by task type and strategy

        """
        routings = self.store.get_task_routings(since=since, limit=10000)

        if not routings:
            return {
                "total_tasks": 0,
                "successful_routing": 0,
                "accuracy_rate": 0.0,
                "avg_confidence": 0.0,
                "by_task_type": {},
                "by_strategy": {},
            }

        total = len(routings)
        successful = sum(1 for r in routings if r.success)
        total_confidence = sum(r.confidence_score for r in routings)

        # Aggregate by task type
        by_type: dict[str, dict[str, int | float]] = {}
        for r in routings:
            if r.task_type not in by_type:
                by_type[r.task_type] = {"total": 0, "success": 0}
            by_type[r.task_type]["total"] += 1
            if r.success:
                by_type[r.task_type]["success"] += 1

        # Calculate rates
        for _task_type, stats in by_type.items():
            stats["rate"] = stats["success"] / stats["total"] if stats["total"] > 0 else 0.0

        # Aggregate by strategy
        by_strategy: dict[str, dict[str, int]] = {}
        for r in routings:
            if r.routing_strategy not in by_strategy:
                by_strategy[r.routing_strategy] = {"total": 0, "success": 0}
            by_strategy[r.routing_strategy]["total"] += 1
            if r.success:
                by_strategy[r.routing_strategy]["success"] += 1

        return {
            "total_tasks": total,
            "successful_routing": successful,
            "accuracy_rate": successful / total if total > 0 else 0.0,
            "avg_confidence": total_confidence / total if total > 0 else 0.0,
            "by_task_type": by_type,
            "by_strategy": by_strategy,
        }

    def test_execution_trends(
        self,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Analyze test execution trends.

        Args:
            since: Only consider executions after this time

        Returns:
            Dict with test execution metrics and trends

        """
        executions = self.store.get_test_executions(since=since, limit=1000)

        if not executions:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration_seconds": 0.0,
                "total_tests_run": 0,
                "total_failures": 0,
                "coverage_trend": "stable",
                "most_failing_tests": [],
            }

        total_execs = len(executions)
        successful_execs = sum(1 for e in executions if e.success)
        total_duration = sum(e.duration_seconds for e in executions)
        total_tests = sum(e.total_tests for e in executions)
        total_failures = sum(e.failed for e in executions)

        # Find most failing tests
        failure_counts: dict[str, int] = {}
        for exec_rec in executions:
            for test in exec_rec.failed_tests:
                test_name = test.get("name", "unknown")
                failure_counts[test_name] = failure_counts.get(test_name, 0) + 1

        most_failing = [
            {"name": name, "failures": count}
            for name, count in heapq.nlargest(10, failure_counts.items(), key=lambda x: x[1])
        ]

        return {
            "total_executions": total_execs,
            "success_rate": successful_execs / total_execs if total_execs > 0 else 0.0,
            "avg_duration_seconds": total_duration / total_execs if total_execs > 0 else 0.0,
            "total_tests_run": total_tests,
            "total_failures": total_failures,
            "coverage_trend": "stable",  # Will be computed from coverage_progress
            "most_failing_tests": most_failing,
        }

    def coverage_progress(
        self,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Track coverage progress over time.

        Args:
            since: Only consider coverage records after this time

        Returns:
            Dict with coverage metrics and trends

        """
        records = self.store.get_coverage_history(since=since, limit=1000)

        if not records:
            return {
                "current_coverage": 0.0,
                "previous_coverage": 0.0,
                "change": 0.0,
                "trend": "no_data",
                "coverage_history": [],
                "files_improved": 0,
                "files_declined": 0,
                "critical_gaps_count": 0,
            }

        # Latest and first records
        latest = records[-1]
        first = records[0]
        current_coverage = latest.overall_percentage

        # Calculate trend by comparing first to last
        if len(records) == 1:
            # Single record - no trend analysis possible
            prev_coverage = 0.0
            change = 0.0
            trend = "stable"
        else:
            # Multiple records - compare first to last
            prev_coverage = first.overall_percentage
            change = current_coverage - prev_coverage

            # Determine trend based on change
            if change > 1.0:
                trend = "improving"
            elif change < -1.0:
                trend = "declining"
            else:
                trend = "stable"

        # Build coverage history from records
        coverage_history = [
            {
                "timestamp": r.timestamp,
                "coverage": r.overall_percentage,
                "trend": r.trend,
            }
            for r in records
        ]

        return {
            "current_coverage": current_coverage,
            "previous_coverage": prev_coverage,
            "change": change,
            "trend": trend,
            "coverage_history": coverage_history,
            "files_improved": 0,  # Would need file-level history
            "files_declined": 0,  # Would need file-level history
            "critical_gaps_count": len(latest.critical_gaps),
        }

    def agent_performance(
        self,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Analyze agent/workflow performance.

        Args:
            since: Only consider assignments after this time

        Returns:
            Dict with agent performance metrics

        """
        assignments = self.store.get_agent_assignments(
            since=since, automated_only=False, limit=10000
        )

        if not assignments:
            return {
                "total_assignments": 0,
                "by_agent": {},
                "automation_rate": 0.0,
                "human_review_rate": 0.0,
            }

        # Aggregate by agent
        by_agent: dict[str, dict[str, Any]] = {}
        total_assignments = len(assignments)
        total_automated = 0
        total_human_review = 0

        for assignment in assignments:
            agent = assignment.assigned_agent
            if agent not in by_agent:
                by_agent[agent] = {
                    "assignments": 0,
                    "completed": 0,
                    "successful": 0,
                    "success_rate": 0.0,
                    "avg_duration_hours": 0.0,
                    "quality_score_avg": 0.0,
                    "total_duration": 0.0,
                    "quality_scores": [],
                }

            stats = by_agent[agent]
            stats["assignments"] += 1
            if assignment.status == "completed":
                stats["completed"] += 1
                if assignment.actual_duration_hours is not None:
                    stats["total_duration"] += assignment.actual_duration_hours

            # Track successful assignments (not just completed)
            if assignment.success:
                stats["successful"] += 1

            if assignment.automated_eligible:
                total_automated += 1
            if assignment.human_review_required:
                total_human_review += 1

        # Calculate averages
        for _agent, stats in by_agent.items():
            if stats["assignments"] > 0:
                stats["success_rate"] = stats["successful"] / stats["assignments"]
            if stats["completed"] > 0:
                stats["avg_duration_hours"] = stats["total_duration"] / stats["completed"]

            # Remove helper fields
            del stats["total_duration"]
            del stats["quality_scores"]
            del stats["successful"]  # Remove helper field, keep success_rate

        return {
            "total_assignments": total_assignments,
            "by_agent": by_agent,
            "automation_rate": (
                total_automated / total_assignments if total_assignments > 0 else 0.0
            ),
            "human_review_rate": (
                total_human_review / total_assignments if total_assignments > 0 else 0.0
            ),
        }

    def tier1_summary(
        self,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Comprehensive Tier 1 automation summary.

        Args:
            since: Only consider records after this time

        Returns:
            Dict combining all Tier 1 metrics

        """
        return {
            "task_routing": self.task_routing_accuracy(since),
            "test_execution": self.test_execution_trends(since),
            "coverage": self.coverage_progress(since),
            "agent_performance": self.agent_performance(since),
            "cost_savings": self.cost_savings_report(since),
        }


# Singleton for global telemetry
_telemetry_store: TelemetryStore | None = None
