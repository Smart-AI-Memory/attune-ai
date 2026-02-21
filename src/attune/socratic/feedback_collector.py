"""Feedback Collector

Collects, stores, and queries feedback from workflow executions
to track agent performance and identify successful patterns.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from attune.security.path_validation import _validate_file_path

from .blueprint import WorkflowBlueprint
from .feedback_models import AgentPerformance, WorkflowPattern
from .success import SuccessEvaluation

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """Collects and stores feedback from workflow executions.

    Example:
        >>> collector = FeedbackCollector()
        >>> collector.record_execution(blueprint, evaluation)
        >>> performance = collector.get_agent_performance("security_reviewer")
    """

    def __init__(self, storage_path: str = ".attune/socratic/feedback"):
        """Initialize the collector.

        Args:
            storage_path: Path for feedback data storage
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._agent_performance: dict[str, AgentPerformance] = {}
        self._workflow_patterns: dict[str, WorkflowPattern] = {}

        self._load_data()

    def _load_data(self) -> None:
        """Load existing feedback data."""
        # Load agent performance
        perf_file = self.storage_path / "agent_performance.json"
        if perf_file.exists():
            try:
                with perf_file.open() as f:
                    data = json.load(f)
                for template_id, perf_data in data.items():
                    self._agent_performance[template_id] = AgentPerformance.from_dict(perf_data)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load agent performance: {e}")

        # Load workflow patterns
        patterns_file = self.storage_path / "workflow_patterns.json"
        if patterns_file.exists():
            try:
                with patterns_file.open() as f:
                    data = json.load(f)
                for pattern_id, pattern_data in data.items():
                    self._workflow_patterns[pattern_id] = WorkflowPattern(**pattern_data)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load workflow patterns: {e}")

    def _save_data(self) -> None:
        """Save feedback data to disk."""
        # Save agent performance
        perf_file = self.storage_path / "agent_performance.json"
        perf_data = {k: v.to_dict() for k, v in self._agent_performance.items()}
        validated_perf = _validate_file_path(str(perf_file))
        with validated_perf.open("w") as f:
            json.dump(perf_data, f, indent=2)

        # Save workflow patterns
        patterns_file = self.storage_path / "workflow_patterns.json"
        patterns_data = {k: v.to_dict() for k, v in self._workflow_patterns.items()}
        validated_patterns = _validate_file_path(str(patterns_file))
        with validated_patterns.open("w") as f:
            json.dump(patterns_data, f, indent=2)

    def record_execution(
        self,
        blueprint: WorkflowBlueprint,
        evaluation: SuccessEvaluation,
    ) -> None:
        """Record feedback from a workflow execution.

        Args:
            blueprint: The executed workflow blueprint
            evaluation: The success evaluation results
        """
        success = evaluation.overall_success
        score = evaluation.overall_score

        # Record for each agent
        for agent in blueprint.agents:
            template_id = agent.template_id or agent.spec.id

            if template_id not in self._agent_performance:
                self._agent_performance[template_id] = AgentPerformance(template_id=template_id)

            self._agent_performance[template_id].record_use(
                success=success,
                score=score,
                domain=blueprint.domain,
                languages=blueprint.supported_languages,
                quality_focus=blueprint.quality_focus,
            )

        # Record workflow pattern
        pattern_id = self._generate_pattern_id(blueprint)
        if pattern_id not in self._workflow_patterns:
            self._workflow_patterns[pattern_id] = WorkflowPattern(
                pattern_id=pattern_id,
                domain=blueprint.domain,
                agent_combination=[a.template_id or a.spec.id for a in blueprint.agents],
                stage_configuration=[s.to_dict() for s in blueprint.stages],
            )

        pattern = self._workflow_patterns[pattern_id]
        pattern.uses += 1
        if success:
            pattern.successes += 1
        # Rolling average
        pattern.average_score = (pattern.average_score * (pattern.uses - 1) + score) / pattern.uses

        self._save_data()
        logger.info(
            f"Recorded feedback for blueprint {blueprint.id[:8]}: success={success}, score={score:.2f}"
        )

    def _generate_pattern_id(self, blueprint: WorkflowBlueprint) -> str:
        """Generate a unique ID for a workflow pattern."""
        agents = sorted(a.template_id or a.spec.id for a in blueprint.agents)
        return f"{blueprint.domain}:{':'.join(agents)}"

    def get_agent_performance(self, template_id: str) -> AgentPerformance | None:
        """Get performance data for an agent template."""
        return self._agent_performance.get(template_id)

    def get_all_performance(self) -> dict[str, AgentPerformance]:
        """Get all agent performance data."""
        return self._agent_performance.copy()

    def get_best_agents_for_context(
        self,
        domain: str,
        languages: list[str] | None = None,
        quality_focus: list[str] | None = None,
        limit: int = 5,
    ) -> list[tuple[str, float]]:
        """Get the best performing agents for a context.

        Args:
            domain: Target domain
            languages: Target languages
            quality_focus: Quality attributes
            limit: Maximum number of results

        Returns:
            List of (template_id, score) tuples sorted by score
        """
        scored_agents = []

        for template_id, perf in self._agent_performance.items():
            score = perf.get_score_for_context(domain, languages, quality_focus)
            # Apply confidence penalty for low sample sizes
            confidence = min(perf.total_uses / 10, 1.0)  # Full confidence at 10+ uses
            adjusted_score = score * confidence + 0.5 * (1 - confidence)  # Blend with neutral
            scored_agents.append((template_id, adjusted_score))

        # Sort by score descending
        scored_agents.sort(key=lambda x: x[1], reverse=True)

        return scored_agents[:limit]

    def get_successful_patterns(
        self,
        domain: str | None = None,
        min_success_rate: float = 0.7,
        min_uses: int = 3,
    ) -> list[WorkflowPattern]:
        """Get successful workflow patterns.

        Args:
            domain: Filter by domain
            min_success_rate: Minimum success rate threshold
            min_uses: Minimum number of uses to be considered

        Returns:
            List of successful patterns
        """
        patterns = []

        for pattern in self._workflow_patterns.values():
            if domain and pattern.domain != domain:
                continue
            if pattern.uses < min_uses:
                continue
            if pattern.success_rate < min_success_rate:
                continue
            patterns.append(pattern)

        # Sort by success rate then by uses
        patterns.sort(key=lambda p: (p.success_rate, p.uses), reverse=True)

        return patterns

    def get_insights(self) -> dict[str, Any]:
        """Get aggregated insights from feedback data.

        Returns:
            Dictionary with various insights
        """
        insights: dict[str, Any] = {
            "total_agents_tracked": len(self._agent_performance),
            "total_patterns_tracked": len(self._workflow_patterns),
            "top_performing_agents": [],
            "declining_agents": [],
            "domain_insights": {},
            "recommendations": [],
        }

        # Top performing agents
        all_agents = [
            (tid, perf) for tid, perf in self._agent_performance.items() if perf.total_uses >= 5
        ]
        all_agents.sort(key=lambda x: x[1].average_score, reverse=True)
        insights["top_performing_agents"] = [
            {"template_id": tid, "score": perf.average_score, "uses": perf.total_uses}
            for tid, perf in all_agents[:5]
        ]

        # Declining agents
        for tid, perf in self._agent_performance.items():
            if perf.trend == "declining" and perf.total_uses >= 5:
                insights["declining_agents"].append(
                    {
                        "template_id": tid,
                        "current_score": perf.average_score,
                        "uses": perf.total_uses,
                    }
                )

        # Domain insights
        domains: dict[str, dict[str, Any]] = {}
        for perf in self._agent_performance.values():
            for domain, stats in perf.by_domain.items():
                if domain not in domains:
                    domains[domain] = {"total_uses": 0, "total_score": 0, "agents": set()}
                domains[domain]["total_uses"] += stats["uses"]
                domains[domain]["total_score"] += stats["total_score"]
                domains[domain]["agents"].add(perf.template_id)

        for domain, stats in domains.items():
            if stats["total_uses"] > 0:
                insights["domain_insights"][domain] = {
                    "average_score": stats["total_score"] / stats["total_uses"],
                    "total_uses": stats["total_uses"],
                    "agents_used": len(stats["agents"]),
                }

        # Generate recommendations
        insights["recommendations"] = self._generate_recommendations()

        return insights

    def _generate_recommendations(self) -> list[str]:
        """Generate improvement recommendations based on feedback."""
        recommendations = []

        # Check for underperforming agents
        for tid, perf in self._agent_performance.items():
            if perf.total_uses >= 10 and perf.success_rate < 0.5:
                recommendations.append(
                    f"Consider reviewing '{tid}' configuration - success rate is {perf.success_rate:.0%}"
                )

        # Check for agents that work well together
        successful_patterns = self.get_successful_patterns(min_success_rate=0.8, min_uses=5)
        for pattern in successful_patterns[:3]:
            agents = ", ".join(pattern.agent_combination)
            recommendations.append(
                f"Successful pattern for '{pattern.domain}': [{agents}] - {pattern.success_rate:.0%} success rate"
            )

        # Check for domains needing more data
        for domain, stats in self.get_insights().get("domain_insights", {}).items():
            if stats["total_uses"] < 5:
                recommendations.append(
                    f"More data needed for '{domain}' domain - only {stats['total_uses']} executions recorded"
                )

        return recommendations
