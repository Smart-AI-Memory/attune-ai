"""Agent-to-LLM Feedback Loop for Quality-Based Learning.

Pattern 6 from Agent Coordination Architecture - Collect quality ratings
on LLM responses and use feedback to inform routing decisions.

Data models live in feedback_models.py; this module contains the
FeedbackLoop class with pluggable storage and recommendation logic.
When Redis is unavailable the loop falls back to an in-process
in-memory store so it works out of the box on a default PyPI install.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import fnmatch
import logging
import threading
import time
from datetime import datetime
from typing import Any
from uuid import uuid4

from .feedback_models import (
    FeedbackEntry,
    ModelTier,
    QualityStats,
    TierRecommendation,
)

# Re-export models for backward compatibility
__all__ = [
    "FeedbackEntry",
    "FeedbackLoop",
    "ModelTier",
    "QualityStats",
    "TierRecommendation",
]

logger = logging.getLogger(__name__)


class _InMemoryStore:
    """Minimal in-memory backend used when no Redis is available.

    Implements the MemoryBackend protocol surface needed by FeedbackLoop:
    stash, retrieve, delete, keys, is_connected.  TTL is honoured lazily
    (expired entries are pruned on access rather than with a background
    thread, keeping the implementation dependency-free).
    """

    def __init__(self) -> None:
        # value -> (data, expires_at_monotonic | None)
        self._data: dict[str, tuple[Any, float | None]] = {}
        self._lock = threading.Lock()

    def stash(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        agent_id: str | None = None,
    ) -> bool:
        """Store a value, optionally expiring after *ttl* seconds."""
        expires_at = time.monotonic() + ttl if ttl else None
        with self._lock:
            self._data[key] = (value, expires_at)
        return True

    def retrieve(self, key: str, agent_id: str | None = None) -> Any | None:
        """Return value or None if missing / expired."""
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at and time.monotonic() > expires_at:
                del self._data[key]
                return None
            return value

    def delete(self, key: str) -> bool:
        """Remove a key; returns True if it existed."""
        with self._lock:
            return self._data.pop(key, None) is not None

    def keys(self, pattern: str = "*") -> list[str]:
        """Return keys matching a glob *pattern*, pruning expired entries."""
        now = time.monotonic()
        with self._lock:
            expired = [k for k, (_, exp) in self._data.items() if exp and now > exp]
            for k in expired:
                del self._data[k]
            return [k for k in self._data if fnmatch.fnmatch(k, pattern)]

    def is_connected(self) -> bool:
        return True

    def get_stats(self) -> dict:
        return {"entries": len(self._data), "backend": "in-memory"}

    def close(self) -> None:
        pass

    def supports_realtime(self) -> bool:
        return False

    def supports_distributed(self) -> bool:
        return False


class FeedbackLoop:
    """Agent-to-LLM feedback loop for quality-based learning.

    Collects quality ratings on LLM responses and uses feedback to:
    - Recommend tier upgrades/downgrades
    - Track quality trends over time
    - Identify underperforming stages
    - Optimize routing based on historical performance

    Storage is pluggable via the MemoryBackend protocol.  When Redis is
    not available the loop falls back to an in-process _InMemoryStore so
    it is always functional on a default PyPI install (data is lost on
    process exit, which is acceptable for dev environments).

    Attributes:
        FEEDBACK_TTL: Feedback entry TTL in seconds (7 days)
        MIN_SAMPLES: Minimum samples needed for a recommendation (10)
        QUALITY_THRESHOLD: Quality below this triggers upgrade advice (0.7)
    """

    FEEDBACK_TTL = 604800  # 7 days
    MIN_SAMPLES = 10
    QUALITY_THRESHOLD = 0.7

    def __init__(self, memory=None) -> None:
        """Initialise the feedback loop.

        Args:
            memory: Optional MemoryBackend instance.  When omitted the loop
                tries the UsageTracker's backend (Redis when available) and
                falls back to an in-memory store.
        """
        self.memory = memory

        if self.memory is None:
            try:
                from attune.telemetry import UsageTracker

                tracker = UsageTracker.get_instance()
                if hasattr(tracker, "_memory") and tracker._memory is not None:
                    self.memory = tracker._memory
            except (ImportError, AttributeError):
                pass

        if self.memory is None:
            self.memory = _InMemoryStore()
            logger.debug("FeedbackLoop using in-memory store (Redis not available)")

    def record_feedback(
        self,
        workflow_name: str,
        stage_name: str,
        tier: str | ModelTier,
        quality_score: float,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Record quality feedback for a workflow stage execution.

        Args:
            workflow_name: Name of workflow
            stage_name: Name of stage within workflow
            tier: Model tier used (CHEAP, CAPABLE, PREMIUM)
            quality_score: Quality rating 0.0-1.0 (0=bad, 1=excellent)
            metadata: Optional metadata (tokens, latency, etc.)

        Returns:
            Feedback ID if stored, empty string otherwise

        Example:
            >>> feedback = FeedbackLoop()
            >>> feedback.record_feedback(
            ...     workflow_name="code-review",
            ...     stage_name="analysis",
            ...     tier=ModelTier.CHEAP,
            ...     quality_score=0.85,
            ...     metadata={"tokens": 150, "latency_ms": 1200}
            ... )
        """
        if not 0.0 <= quality_score <= 1.0:
            logger.warning(f"Invalid quality score: {quality_score} (must be 0.0-1.0)")
            return ""

        if isinstance(tier, ModelTier):
            tier = tier.value

        feedback_id = f"feedback_{uuid4().hex[:8]}"
        key = f"feedback:{workflow_name}:{stage_name}:{tier}:{feedback_id}"

        entry = FeedbackEntry(
            feedback_id=feedback_id,
            workflow_name=workflow_name,
            stage_name=stage_name,
            tier=tier,
            quality_score=quality_score,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )

        try:
            self.memory.stash(key, entry.to_dict(), ttl=self.FEEDBACK_TTL)
        except Exception as e:
            logger.error(f"Failed to store feedback: {e}")
            return ""

        logger.debug(
            f"Recorded feedback: {workflow_name}/{stage_name} "
            f"tier={tier} quality={quality_score:.2f}"
        )
        return feedback_id

    def get_feedback_history(
        self,
        workflow_name: str,
        stage_name: str,
        tier: str | ModelTier | None = None,
        limit: int = 100,
    ) -> list[FeedbackEntry]:
        """Get feedback history for a workflow stage.

        Args:
            workflow_name: Name of workflow
            stage_name: Name of stage
            tier: Optional filter by tier
            limit: Maximum number of entries to return

        Returns:
            List of feedback entries (newest first)
        """
        if isinstance(tier, ModelTier):
            tier = tier.value

        try:
            pattern = (
                f"feedback:{workflow_name}:{stage_name}:{tier}:*"
                if tier
                else f"feedback:{workflow_name}:{stage_name}:*"
            )
            keys = self.memory.keys(pattern)

            entries: list[FeedbackEntry] = []
            for key in keys:
                data = self._retrieve_feedback(key)
                if data:
                    try:
                        entries.append(FeedbackEntry.from_dict(data))
                    except Exception as e:
                        logger.error(f"Failed to parse feedback entry {key}: {e}")
                        continue
                if len(entries) >= limit:
                    break

            entries.sort(key=lambda e: e.timestamp, reverse=True)
            return entries[:limit]
        except Exception as e:
            logger.error(f"Failed to get feedback history: {e}")
            return []

    def _retrieve_feedback(self, key: str) -> dict[str, Any] | None:
        """Retrieve a single feedback entry dict by key."""
        try:
            return self.memory.retrieve(key)
        except Exception as e:
            logger.debug(f"Failed to retrieve feedback: {e}")
            return None

    def get_quality_stats(
        self, workflow_name: str, stage_name: str, tier: str | ModelTier | None = None
    ) -> QualityStats | None:
        """Get quality statistics for a workflow stage.

        Args:
            workflow_name: Name of workflow
            stage_name: Name of stage
            tier: Optional filter by tier

        Returns:
            Quality statistics or None if insufficient data
        """
        history = self.get_feedback_history(workflow_name, stage_name, tier=tier)

        if not history:
            return None

        quality_scores = [entry.quality_score for entry in history]
        avg_quality = sum(quality_scores) / len(quality_scores)
        min_quality = min(quality_scores)
        max_quality = max(quality_scores)

        if len(history) >= 4:
            recent = quality_scores[: len(quality_scores) // 2]
            older = quality_scores[len(quality_scores) // 2 :]
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)
            recent_trend = (recent_avg - older_avg) / max(older_avg, 0.1)
        else:
            recent_trend = 0.0

        tier_str = tier.value if isinstance(tier, ModelTier) else (tier or "all")

        return QualityStats(
            workflow_name=workflow_name,
            stage_name=stage_name,
            tier=tier_str,
            avg_quality=avg_quality,
            min_quality=min_quality,
            max_quality=max_quality,
            sample_count=len(history),
            recent_trend=recent_trend,
        )

    def recommend_tier(
        self, workflow_name: str, stage_name: str, current_tier: str | ModelTier | None = None
    ) -> TierRecommendation:
        """Recommend optimal tier based on quality feedback.

        Analyzes historical quality data and recommends:
        - Downgrade if current tier consistently delivers high quality
        - Upgrade if current tier delivers poor quality
        - Keep current if quality is acceptable

        Args:
            workflow_name: Name of workflow
            stage_name: Name of stage
            current_tier: Current tier in use (if known)

        Returns:
            Tier recommendation with confidence and reasoning
        """
        if isinstance(current_tier, ModelTier):
            current_tier = current_tier.value

        stats_by_tier = {}
        for tier in ["cheap", "capable", "premium"]:
            stats = self.get_quality_stats(workflow_name, stage_name, tier=tier)
            if stats:
                stats_by_tier[tier] = stats

        if not stats_by_tier:
            return TierRecommendation(
                current_tier=current_tier or "unknown",
                recommended_tier=current_tier or "cheap",
                confidence=0.0,
                reason="No feedback data available",
                stats={},
            )

        if not current_tier:
            all_history = self.get_feedback_history(workflow_name, stage_name, tier=None, limit=1)
            current_tier = all_history[0].tier if all_history else "cheap"

        current_stats = stats_by_tier.get(current_tier)

        if not current_stats or current_stats.sample_count < self.MIN_SAMPLES:
            return TierRecommendation(
                current_tier=current_tier,
                recommended_tier=current_tier,
                confidence=0.0,
                reason=(
                    f"Insufficient data (need {self.MIN_SAMPLES} samples, "
                    f"have {current_stats.sample_count if current_stats else 0})"
                ),
                stats=stats_by_tier,
            )

        avg_quality = current_stats.avg_quality
        confidence = min(current_stats.sample_count / (self.MIN_SAMPLES * 2), 1.0)

        if avg_quality < self.QUALITY_THRESHOLD:
            if current_tier == "cheap":
                recommended = "capable"
                reason = f"Low quality ({avg_quality:.2f}) - upgrade for better results"
            elif current_tier == "capable":
                recommended = "premium"
                reason = f"Low quality ({avg_quality:.2f}) - upgrade to premium tier"
            else:
                recommended = "premium"
                reason = f"Already using premium tier (quality: {avg_quality:.2f})"
                confidence = 1.0
        elif avg_quality > 0.9 and current_tier != "cheap":
            if current_tier == "premium":
                capable_stats = stats_by_tier.get("capable")
                if capable_stats and capable_stats.avg_quality > 0.85:
                    recommended = "capable"
                    reason = f"Excellent quality ({avg_quality:.2f}) - downgrade to save cost"
                else:
                    recommended = "premium"
                    reason = f"Excellent quality ({avg_quality:.2f}) - keep premium for consistency"
            elif current_tier == "capable":
                cheap_stats = stats_by_tier.get("cheap")
                if cheap_stats and cheap_stats.avg_quality > 0.85:
                    recommended = "cheap"
                    reason = f"Excellent quality ({avg_quality:.2f}) - downgrade to save cost"
                else:
                    recommended = "capable"
                    reason = f"Excellent quality ({avg_quality:.2f}) - keep capable tier"
            else:
                recommended = current_tier
                reason = f"Excellent quality ({avg_quality:.2f}) - maintain current tier"
        else:
            recommended = current_tier
            reason = f"Acceptable quality ({avg_quality:.2f}) - maintain current tier"

        return TierRecommendation(
            current_tier=current_tier,
            recommended_tier=recommended,
            confidence=confidence,
            reason=reason,
            stats=stats_by_tier,
        )

    def get_underperforming_stages(
        self, workflow_name: str, quality_threshold: float = 0.7
    ) -> list[tuple[str, QualityStats]]:
        """Get workflow stages/tiers with poor quality scores.

        Args:
            workflow_name: Name of workflow
            quality_threshold: Threshold below which a stage is underperforming

        Returns:
            List of (stage_label, stats) tuples sorted worst-first
        """
        try:
            keys = self.memory.keys(f"feedback:{workflow_name}:*")

            stage_tier_combos: set[tuple[str, str]] = set()
            for key in keys:
                parts = key.split(":")
                if len(parts) >= 4:
                    stage_tier_combos.add((parts[2], parts[3]))

            underperforming = []
            for stage_name, tier in stage_tier_combos:
                stats = self.get_quality_stats(workflow_name, stage_name, tier=tier)
                if stats and stats.avg_quality < quality_threshold:
                    underperforming.append((f"{stage_name}/{tier}", stats))

            underperforming.sort(key=lambda x: x[1].avg_quality)
            return underperforming
        except Exception as e:
            logger.error(f"Failed to get underperforming stages: {e}")
            return []

    def clear_feedback(self, workflow_name: str, stage_name: str | None = None) -> int:
        """Clear feedback history for a workflow or stage.

        Args:
            workflow_name: Name of workflow
            stage_name: Optional stage name (clears all stages if None)

        Returns:
            Number of feedback entries cleared
        """
        try:
            pattern = (
                f"feedback:{workflow_name}:{stage_name}:*"
                if stage_name
                else f"feedback:{workflow_name}:*"
            )
            keys = self.memory.keys(pattern)
            return sum(1 for k in keys if self.memory.delete(k))
        except Exception as e:
            logger.error(f"Failed to clear feedback: {e}")
            return 0
