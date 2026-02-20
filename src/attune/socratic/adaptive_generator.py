"""Adaptive Agent Generator and Feedback Loop

Provides feedback-driven agent generation and a high-level
integration facade for the feedback loop system.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import Any

from .blueprint import AgentBlueprint, WorkflowBlueprint
from .feedback_collector import FeedbackCollector
from .success import SuccessEvaluation

logger = logging.getLogger(__name__)


class AdaptiveAgentGenerator:
    """Agent generator that uses feedback to improve recommendations.

    Wraps the standard AgentGenerator and adjusts recommendations
    based on historical performance data.

    Example:
        >>> generator = AdaptiveAgentGenerator()
        >>> agents = generator.generate_agents_for_requirements(requirements)
        >>> # Returns agents weighted by historical success
    """

    def __init__(self, feedback_collector: FeedbackCollector | None = None):
        """Initialize the adaptive generator.

        Args:
            feedback_collector: Feedback collector instance
        """
        from .generator import AgentGenerator

        self.base_generator = AgentGenerator()
        self.feedback = feedback_collector or FeedbackCollector()

    def generate_agents_for_requirements(
        self,
        requirements: dict[str, Any],
        use_feedback: bool = True,
    ) -> list[AgentBlueprint]:
        """Generate agents using feedback-informed recommendations.

        Args:
            requirements: Requirements from Socratic session
            use_feedback: Whether to use feedback data

        Returns:
            List of AgentBlueprints optimized based on feedback
        """
        # Get base recommendations
        base_agents = self.base_generator.generate_agents_for_requirements(requirements)

        if not use_feedback:
            return base_agents

        # Get context
        domain = requirements.get("domain", "general")
        languages = requirements.get("languages", [])
        quality_focus = requirements.get("quality_focus", [])

        # Get best agents for this context
        best_agents = self.feedback.get_best_agents_for_context(
            domain=domain,
            languages=languages,
            quality_focus=quality_focus,
            limit=10,
        )

        if not best_agents:
            return base_agents

        # Reorder and potentially add agents based on feedback
        agent_scores = dict(best_agents)

        # Score base agents
        scored_base = []
        for agent in base_agents:
            tid = agent.template_id or agent.spec.id
            feedback_score = agent_scores.get(tid, 0.5)
            scored_base.append((agent, feedback_score))

        # Sort by feedback score
        scored_base.sort(key=lambda x: x[1], reverse=True)

        # Check if any high-performing agents are missing
        base_ids = {a.template_id or a.spec.id for a in base_agents}
        for tid, score in best_agents:
            if tid not in base_ids and score > 0.7:
                # Add this high-performing agent
                try:
                    new_agent = self.base_generator.generate_agent_from_template(
                        tid,
                        customizations={
                            "languages": languages,
                            "quality_focus": quality_focus,
                        },
                    )
                    scored_base.append((new_agent, score))
                    logger.info(f"Added high-performing agent '{tid}' based on feedback")
                except ValueError:
                    pass  # Template not found

        # Return sorted agents
        return [agent for agent, _ in scored_base]

    def get_recommendation_explanation(
        self,
        requirements: dict[str, Any],
    ) -> dict[str, Any]:
        """Get explanation for agent recommendations.

        Args:
            requirements: Requirements dict

        Returns:
            Explanation of why agents were recommended
        """
        domain = requirements.get("domain", "general")
        languages = requirements.get("languages", [])
        quality_focus = requirements.get("quality_focus", [])

        best_agents = self.feedback.get_best_agents_for_context(
            domain=domain,
            languages=languages,
            quality_focus=quality_focus,
        )

        successful_patterns = self.feedback.get_successful_patterns(
            domain=domain,
            min_success_rate=0.7,
        )

        return {
            "context": {
                "domain": domain,
                "languages": languages,
                "quality_focus": quality_focus,
            },
            "recommended_agents": [
                {
                    "template_id": tid,
                    "score": score,
                    "performance": (
                        self.feedback.get_agent_performance(tid).to_dict()
                        if self.feedback.get_agent_performance(tid)
                        else None
                    ),
                }
                for tid, score in best_agents
            ],
            "successful_patterns": [p.to_dict() for p in successful_patterns[:3]],
            "data_quality": {
                "total_executions": sum(
                    p.total_uses for p in self.feedback.get_all_performance().values()
                ),
                "agents_with_data": len(
                    [p for p in self.feedback.get_all_performance().values() if p.total_uses >= 5]
                ),
            },
        }


class FeedbackLoop:
    """High-level integration for the feedback loop.

    Provides a simple interface to:
    1. Record execution results
    2. Get improved recommendations
    3. View insights

    Example:
        >>> loop = FeedbackLoop()
        >>>
        >>> # After workflow execution
        >>> loop.record(blueprint, evaluation)
        >>>
        >>> # For next generation
        >>> agents = loop.get_recommended_agents(requirements)
        >>>
        >>> # View insights
        >>> insights = loop.get_insights()
    """

    def __init__(
        self,
        storage_path: str = ".attune/socratic/feedback",
    ):
        """Initialize the feedback loop.

        Args:
            storage_path: Path for feedback storage
        """
        self.collector = FeedbackCollector(storage_path)
        self.adaptive_generator = AdaptiveAgentGenerator(self.collector)

    def record(
        self,
        blueprint: WorkflowBlueprint,
        evaluation: SuccessEvaluation,
    ) -> None:
        """Record execution results for learning.

        Args:
            blueprint: The executed blueprint
            evaluation: The success evaluation
        """
        self.collector.record_execution(blueprint, evaluation)

    def get_recommended_agents(
        self,
        requirements: dict[str, Any],
    ) -> list[AgentBlueprint]:
        """Get recommended agents using feedback data.

        Args:
            requirements: Requirements from Socratic session

        Returns:
            List of recommended agents
        """
        return self.adaptive_generator.generate_agents_for_requirements(requirements)

    def get_insights(self) -> dict[str, Any]:
        """Get aggregated insights.

        Returns:
            Dictionary with insights and recommendations
        """
        return self.collector.get_insights()

    def get_agent_stats(self, template_id: str) -> dict[str, Any] | None:
        """Get performance stats for a specific agent.

        Args:
            template_id: Agent template ID

        Returns:
            Performance statistics or None
        """
        perf = self.collector.get_agent_performance(template_id)
        return perf.to_dict() if perf else None

    def explain_recommendations(
        self,
        requirements: dict[str, Any],
    ) -> dict[str, Any]:
        """Explain why certain agents are recommended.

        Args:
            requirements: Requirements dict

        Returns:
            Explanation dictionary
        """
        return self.adaptive_generator.get_recommendation_explanation(requirements)
