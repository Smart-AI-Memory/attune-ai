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
from datetime import datetime, timezone
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
        """Initialize the in-memory store with an empty data dict."""
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
        """Return True; in-memory store is always connected."""
        return True

    def get_stats(self) -> dict:
        """Return store statistics including entry count."""
        return {"entries": len(self._data), "backend": "in-memory"}

    def close(self) -> None:
        """No-op; in-memory store has no resources to release."""
        pass

    def supports_realtime(self) -> bool:
        """Return False; in-memory store does not support pub/sub."""
        return False

    def supports_distributed(self) -> bool:
        """Return False; in-memory store is single-process only."""
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
    #: Above this, a non-cheap tier is a downgrade candidate.
    EXCELLENT_QUALITY = 0.9
    #: A downgrade only fires when the target tier's own history
    #: proves it holds quality above this bar.
    DOWNGRADE_TARGET_QUALITY = 0.85

    #: The tier ladder is linear, so each verdict direction is one map.
    _UPGRADE_PATH = {"cheap": "capable", "capable": "premium"}
    _DOWNGRADE_PATH = {"premium": "capable", "capable": "cheap"}

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
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
        )

        try:
            self.memory.stash(key, entry.to_dict(), ttl=self.FEEDBACK_TTL)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to store feedback: {e}")
            return ""

        logger.debug(
            f"Recorded feedback: {workflow_name}/{stage_name} "
            f"tier={tier} quality={quality_score:.2f}",
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
            entries = self._parse_entries(self._retrieve_feedback_many(keys), limit)
            entries.sort(key=lambda e: e.timestamp, reverse=True)
            return entries[:limit]
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to get feedback history: {e}")
            return []

    def _retrieve_feedback(self, key: str) -> dict[str, Any] | None:
        """Retrieve a single feedback entry dict by key."""
        try:
            return self.memory.retrieve(key)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Failed to retrieve feedback: {e}")
            return None

    def _retrieve_feedback_many(self, keys: list[str]) -> list[tuple[str, Any]]:
        """Fetch feedback records for ``keys`` in one backend call.

        #2237: the per-key ``retrieve`` loop paid one round trip per
        record (N+1). ``retrieve_many`` is part of the MemoryBackend
        protocol and batches server-side; a backend without it (e.g. the
        in-process fallback store, where reads are free) degrades to the
        per-key path. NOTE: batching deliberately goes through the
        backend, never a raw Redis MGET — the AMS backend's ``_client``
        is an HTTP client, not redis-py, so a raw-client batch would
        read a different surface than ``retrieve`` writes.
        """
        retrieve_many = getattr(self.memory, "retrieve_many", None)
        if callable(retrieve_many):
            try:
                got = retrieve_many(list(keys))
                return [(key, got.get(key)) for key in keys]
            except Exception as e:  # noqa: BLE001
                logger.debug(f"Batched feedback retrieve failed; falling back: {e}")
        return [(key, self._retrieve_feedback(key)) for key in keys]

    @staticmethod
    def _parse_entries(records: list[tuple[str, Any]], limit: int) -> list[FeedbackEntry]:
        """Parse raw records into entries, skipping malformed ones."""
        entries: list[FeedbackEntry] = []
        for key, data in records:
            if data:
                try:
                    entries.append(FeedbackEntry.from_dict(data))
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Failed to parse feedback entry {key}: {e}")
                    continue
            if len(entries) >= limit:
                break
        return entries

    def get_quality_stats(
        self,
        workflow_name: str,
        stage_name: str,
        tier: str | ModelTier | None = None,
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

        tier_str = tier.value if isinstance(tier, ModelTier) else (tier or "all")
        return self._stats_from_history(workflow_name, stage_name, tier_str, history)

    @staticmethod
    def _stats_from_history(
        workflow_name: str,
        stage_name: str,
        tier_str: str,
        history: list[FeedbackEntry],
    ) -> QualityStats:
        """Compute stats over an already-fetched, newest-first history."""
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
        self,
        workflow_name: str,
        stage_name: str,
        current_tier: str | ModelTier | None = None,
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

        recommended, reason, confidence_override = self._tier_verdict(
            current_tier, current_stats.avg_quality, stats_by_tier
        )
        confidence = (
            confidence_override
            if confidence_override is not None
            else min(current_stats.sample_count / (self.MIN_SAMPLES * 2), 1.0)
        )

        return TierRecommendation(
            current_tier=current_tier,
            recommended_tier=recommended,
            confidence=confidence,
            reason=reason,
            stats=stats_by_tier,
        )

    def _tier_verdict(
        self,
        current_tier: str,
        avg_quality: float,
        stats_by_tier: dict,
    ) -> tuple[str, str, float | None]:
        """Resolve (recommended_tier, reason, confidence_override).

        The verdict for a tier with sufficient samples, in three
        quality bands:

        - below ``QUALITY_THRESHOLD``: climb ``_UPGRADE_PATH`` one
          rung; at the top (premium) stay put with confidence forced
          to 1.0 — there is nothing to upgrade to.
        - above ``EXCELLENT_QUALITY`` on a downgradable tier: step
          down ``_DOWNGRADE_PATH`` one rung only when the target
          tier's own history proves it holds quality above
          ``DOWNGRADE_TARGET_QUALITY``; otherwise keep the tier.
        - otherwise: acceptable — keep the current tier.

        A ``None`` confidence override means the caller applies the
        standard sample-count formula.
        """
        if avg_quality < self.QUALITY_THRESHOLD:
            upgraded = self._UPGRADE_PATH.get(current_tier)
            if upgraded is None:
                reason = f"Already using premium tier (quality: {avg_quality:.2f})"
                return "premium", reason, 1.0
            direction = "for better results" if current_tier == "cheap" else "to premium tier"
            return upgraded, f"Low quality ({avg_quality:.2f}) - upgrade {direction}", None

        if avg_quality > self.EXCELLENT_QUALITY and current_tier in self._DOWNGRADE_PATH:
            target = self._DOWNGRADE_PATH[current_tier]
            target_stats = stats_by_tier.get(target)
            if target_stats and target_stats.avg_quality > self.DOWNGRADE_TARGET_QUALITY:
                reason = f"Excellent quality ({avg_quality:.2f}) - downgrade to save cost"
                return target, reason, None
            keep = (
                "keep premium for consistency" if current_tier == "premium" else "keep capable tier"
            )
            return current_tier, f"Excellent quality ({avg_quality:.2f}) - {keep}", None

        reason = f"Acceptable quality ({avg_quality:.2f}) - maintain current tier"
        return current_tier, reason, None

    def get_underperforming_stages(
        self,
        workflow_name: str,
        quality_threshold: float = 0.7,
    ) -> list[tuple[str, QualityStats]]:
        """Get workflow stages/tiers with poor quality scores.

        Args:
            workflow_name: Name of workflow
            quality_threshold: Threshold below which a stage is underperforming

        Returns:
            List of (stage_label, stats) tuples sorted worst-first

        """
        try:
            # #2237: one scan + ONE batched fetch, grouped in memory —
            # previously O(combos x (scan + N per-key reads)) via nested
            # get_quality_stats -> get_feedback_history calls.
            keys = self.memory.keys(f"feedback:{workflow_name}:*")

            combo_keys: dict[tuple[str, str], list[str]] = {}
            for key in keys:
                parts = key.split(":")
                if len(parts) >= 4:
                    combo_keys.setdefault((parts[2], parts[3]), []).append(key)

            records = dict(self._retrieve_feedback_many(keys))

            underperforming = []
            for (stage_name, tier), keys_for_combo in combo_keys.items():
                entries = self._parse_entries(
                    [(k, records.get(k)) for k in keys_for_combo], limit=100
                )
                if not entries:
                    continue
                entries.sort(key=lambda e: e.timestamp, reverse=True)
                stats = self._stats_from_history(workflow_name, stage_name, tier, entries)
                if stats.avg_quality < quality_threshold:
                    underperforming.append((f"{stage_name}/{tier}", stats))

            underperforming.sort(key=lambda x: x[1].avg_quality)
            return underperforming
        except Exception as e:  # noqa: BLE001
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
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to clear feedback: {e}")
            return 0
