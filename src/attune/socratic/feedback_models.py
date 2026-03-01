"""Feedback Data Models

Data structures for tracking agent performance and workflow patterns
in the feedback loop system.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AgentPerformance:
    """Performance statistics for an agent template."""

    template_id: str
    total_uses: int = 0
    successful_uses: int = 0
    average_score: float = 0.0
    scores: list[float] = field(default_factory=list)

    # Context-specific performance
    by_domain: dict[str, dict[str, float]] = field(default_factory=dict)
    by_language: dict[str, dict[str, float]] = field(default_factory=dict)
    by_quality_focus: dict[str, dict[str, float]] = field(default_factory=dict)

    # Trend data
    recent_scores: list[tuple[str, float]] = field(default_factory=list)  # (timestamp, score)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_uses == 0:
            return 0.0
        return self.successful_uses / self.total_uses

    @property
    def trend(self) -> str:
        """Determine performance trend."""
        if len(self.recent_scores) < 5:
            return "insufficient_data"

        recent_5 = [s for _, s in self.recent_scores[-5:]]
        older_5 = (
            [s for _, s in self.recent_scores[-10:-5]] if len(self.recent_scores) >= 10 else []
        )

        if not older_5:
            return "stable"

        recent_avg = sum(recent_5) / len(recent_5)
        older_avg = sum(older_5) / len(older_5)

        if recent_avg > older_avg * 1.1:
            return "improving"
        if recent_avg < older_avg * 0.9:
            return "declining"
        return "stable"

    def record_use(
        self,
        success: bool,
        score: float,
        domain: str | None = None,
        languages: list[str] | None = None,
        quality_focus: list[str] | None = None,
    ) -> None:
        """Record a use of this agent."""
        self.total_uses += 1
        if success:
            self.successful_uses += 1

        self.scores.append(score)
        self.average_score = sum(self.scores) / len(self.scores)

        # Record with timestamp for trend analysis
        self.recent_scores.append((datetime.now().isoformat(), score))
        # Keep last 100 scores
        if len(self.recent_scores) > 100:
            self.recent_scores = self.recent_scores[-100:]

        # Record by context
        if domain:
            if domain not in self.by_domain:
                self.by_domain[domain] = {"uses": 0, "successes": 0, "total_score": 0}
            self.by_domain[domain]["uses"] += 1
            self.by_domain[domain]["successes"] += 1 if success else 0
            self.by_domain[domain]["total_score"] += score

        if languages:
            for lang in languages:
                if lang not in self.by_language:
                    self.by_language[lang] = {"uses": 0, "successes": 0, "total_score": 0}
                self.by_language[lang]["uses"] += 1
                self.by_language[lang]["successes"] += 1 if success else 0
                self.by_language[lang]["total_score"] += score

        if quality_focus:
            for qf in quality_focus:
                if qf not in self.by_quality_focus:
                    self.by_quality_focus[qf] = {"uses": 0, "successes": 0, "total_score": 0}
                self.by_quality_focus[qf]["uses"] += 1
                self.by_quality_focus[qf]["successes"] += 1 if success else 0
                self.by_quality_focus[qf]["total_score"] += score

    def get_score_for_context(
        self,
        domain: str | None = None,
        languages: list[str] | None = None,
        quality_focus: list[str] | None = None,
    ) -> float:
        """Get a weighted score for a specific context."""
        scores = []
        weights = []

        # Base score
        if self.total_uses > 0:
            scores.append(self.average_score)
            weights.append(1.0)

        # Domain-specific score
        if domain and domain in self.by_domain:
            d = self.by_domain[domain]
            if d["uses"] > 0:
                scores.append(d["total_score"] / d["uses"])
                weights.append(2.0)  # Higher weight for domain match

        # Language-specific score
        if languages:
            for lang in languages:
                if lang in self.by_language:
                    lang_stats = self.by_language[lang]
                    if lang_stats["uses"] > 0:
                        scores.append(lang_stats["total_score"] / lang_stats["uses"])
                        weights.append(1.5)

        # Quality focus score
        if quality_focus:
            for qf in quality_focus:
                if qf in self.by_quality_focus:
                    q = self.by_quality_focus[qf]
                    if q["uses"] > 0:
                        scores.append(q["total_score"] / q["uses"])
                        weights.append(1.5)

        if not scores:
            return 0.5  # Default neutral score

        # Weighted average
        return sum(s * w for s, w in zip(scores, weights, strict=False)) / sum(weights)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "template_id": self.template_id,
            "total_uses": self.total_uses,
            "successful_uses": self.successful_uses,
            "average_score": self.average_score,
            "success_rate": self.success_rate,
            "trend": self.trend,
            "by_domain": self.by_domain,
            "by_language": self.by_language,
            "by_quality_focus": self.by_quality_focus,
            "recent_scores": self.recent_scores[-20:],  # Last 20 for display
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentPerformance:
        """Deserialize from dictionary."""
        perf = cls(template_id=data.get("template_id", ""))
        perf.total_uses = data.get("total_uses", 0)
        perf.successful_uses = data.get("successful_uses", 0)
        perf.average_score = data.get("average_score", 0.0)
        perf.by_domain = data.get("by_domain", {})
        perf.by_language = data.get("by_language", {})
        perf.by_quality_focus = data.get("by_quality_focus", {})
        perf.recent_scores = data.get("recent_scores", [])
        return perf


@dataclass
class WorkflowPattern:
    """Pattern of successful workflow configurations."""

    pattern_id: str
    domain: str
    agent_combination: list[str]  # List of template IDs
    stage_configuration: list[dict[str, Any]]
    uses: int = 0
    successes: int = 0
    average_score: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.uses == 0:
            return 0.0
        return self.successes / self.uses

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "domain": self.domain,
            "agent_combination": self.agent_combination,
            "stage_configuration": self.stage_configuration,
            "uses": self.uses,
            "successes": self.successes,
            "average_score": self.average_score,
            "success_rate": self.success_rate,
        }
