"""Characterization tests for FeedbackLoop.recommend_tier (complexity D23).

Pins the CURRENT behavior of ``recommend_tier`` in
``src/attune/telemetry/feedback_loop.py`` (~line 337) so a later
table-driven refactor can prove behavior preservation.

Branches already pinned by ``tests/unit/telemetry/test_feedback_loop.py``
(TestFeedbackLoop / TestFeedbackLoopBranches) are NOT duplicated here:

- no feedback data at all, ``current_tier`` explicitly given
  (``test_recommend_tier_no_data``)
- insufficient samples, ``current_stats`` present but below
  ``MIN_SAMPLES`` (``test_recommend_tier_insufficient_samples``)
- low quality on "cheap" -> recommend "capable"
  (``test_recommend_tier_upgrade_on_low_quality``)
- acceptable quality on "cheap" -> maintain
  (``test_recommend_tier_maintain_on_acceptable_quality``)
- low quality on "premium" -> stays "premium"
  (``test_recommend_tier_already_premium``, weak on confidence)
- low quality on "capable" -> recommend "premium"
  (``test_recommend_tier_capable_low_quality_upgrades_to_premium``)
- ``current_tier=None`` inferred from history, at least reaching the
  branch (``test_recommend_tier_no_current_tier_inferred_from_history``,
  weak assertion)
- ``ModelTier`` enum -> ``.value`` conversion for ``current_tier``
  (``test_recommend_tier_model_tier_enum``, weak assertion)

This file covers the remaining/under-asserted branches: the
``current_tier=None`` empty-store path, the "current tier has zero
stats" path, the history-inference fallback-to-"cheap" path (forced,
since it is not reachable through the real store), all four
"excellent quality" downgrade/keep combinations for premium and
capable, the "excellent quality but tier is cheap" exemption, and the
numeric boundaries the code compares against (``QUALITY_THRESHOLD``
0.7, the 0.9 "excellent" cutoff, the 0.85 downgrade-target cutoff,
``MIN_SAMPLES`` 10, and the confidence formula's 0.0-1.0 clamp).

Stats are injected directly via a ``get_quality_stats`` replacement
(and, where needed, ``get_feedback_history``) rather than seeded
through ``record_feedback``, so exact floating-point boundary values
(0.7, 0.85, 0.9) are hit precisely instead of depending on averaging
arithmetic.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime, timezone

from attune.telemetry.feedback_loop import FeedbackEntry, FeedbackLoop, QualityStats


def _stats(tier: str, avg: float, count: int = 15, trend: float = 0.0) -> QualityStats:
    """Build a QualityStats with a precise, hardcoded avg_quality."""
    return QualityStats(
        workflow_name="wf",
        stage_name="stage",
        tier=tier,
        avg_quality=avg,
        min_quality=avg,
        max_quality=avg,
        sample_count=count,
        recent_trend=trend,
    )


def _stats_provider(stats_map: dict):
    """Return a get_quality_stats replacement keyed by the `tier` kwarg.

    recommend_tier always calls ``self.get_quality_stats(workflow_name,
    stage_name, tier=tier)`` with tier in {"cheap", "capable", "premium"},
    so keying on that kwarg is sufficient to control stats_by_tier
    deterministically.
    """

    def _get(workflow_name, stage_name, tier=None):
        return stats_map.get(tier)

    return _get


class TestNoDataAndZeroStatsPaths:
    """stats_by_tier empty, or current_tier has no entry in it at all."""

    def test_no_feedback_data_and_current_tier_none(self):
        """stats_by_tier empty + current_tier=None -> 'unknown'/'cheap'.

        Distinct from the already-pinned ``test_recommend_tier_no_data``,
        which passes an explicit current_tier="cheap".
        """
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider({})

        rec = loop.recommend_tier("wf", "stage", current_tier=None)

        assert rec.current_tier == "unknown"
        assert rec.recommended_tier == "cheap"
        assert rec.confidence == 0.0
        assert "No feedback data" in rec.reason
        assert rec.stats == {}

    def test_current_stats_none_reports_zero_samples(self):
        """current_tier has no key in stats_by_tier at all (not just too
        few samples) -> 'Insufficient data ... have 0'."""
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider({"cheap": _stats("cheap", 0.8)})

        rec = loop.recommend_tier("wf", "stage", current_tier="premium")

        assert rec.current_tier == "premium"
        assert rec.recommended_tier == "premium"
        assert rec.confidence == 0.0
        assert "Insufficient data" in rec.reason
        assert "have 0" in rec.reason


class TestCurrentTierNoneInference:
    """current_tier=None -> inferred from the most recent history entry."""

    def test_inferred_from_history_when_available(self):
        """History lookup returns an entry -> its tier becomes current_tier,
        and the recommendation still runs end to end (strengthens the
        existing weak assertion in test_feedback_loop.py)."""
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider({"capable": _stats("capable", 0.8)})
        entry = FeedbackEntry(
            feedback_id="fb1",
            workflow_name="wf",
            stage_name="stage",
            tier="capable",
            quality_score=0.8,
            timestamp=datetime.now(timezone.utc),
        )
        loop.get_feedback_history = lambda workflow_name, stage_name, tier=None, limit=100: [
            entry,
        ]

        rec = loop.recommend_tier("wf", "stage", current_tier=None)

        assert rec.current_tier == "capable"
        assert rec.recommended_tier == "capable"
        assert "Acceptable quality" in rec.reason

    def test_history_lookup_empty_defaults_to_cheap(self):
        """current_tier=None and the unfiltered history probe returns
        nothing (line ~379's else branch) -> defaults to "cheap".

        Not reachable through the real store in normal operation: if
        stats_by_tier is non-empty, at least one entry must be visible
        to the unfiltered (tier=None) history query too. Forced here via
        a get_feedback_history replacement to pin the documented
        fallback, then flows into the "current tier has zero stats"
        branch (mirrors test_current_stats_none_reports_zero_samples).
        """
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider({"capable": _stats("capable", 0.8)})
        loop.get_feedback_history = lambda workflow_name, stage_name, tier=None, limit=100: []

        rec = loop.recommend_tier("wf", "stage", current_tier=None)

        assert rec.current_tier == "cheap"
        assert rec.recommended_tier == "cheap"
        assert rec.confidence == 0.0
        assert "Insufficient data" in rec.reason
        assert "have 0" in rec.reason


class TestSampleCountBoundaries:
    """MIN_SAMPLES (10) threshold and the confidence formula's clamp."""

    def test_insufficient_at_min_samples_minus_one(self):
        """sample_count=9 (MIN_SAMPLES - 1) -> still insufficient."""
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider({"cheap": _stats("cheap", 0.8, count=9)})

        rec = loop.recommend_tier("wf", "stage", current_tier="cheap")

        assert rec.confidence == 0.0
        assert "Insufficient data" in rec.reason
        assert "have 9" in rec.reason

    def test_sufficient_at_exact_min_samples(self):
        """sample_count=10 (== MIN_SAMPLES) -> no longer insufficient;
        confidence = min(10 / 20, 1.0) = 0.5."""
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider({"cheap": _stats("cheap", 0.8, count=10)})

        rec = loop.recommend_tier("wf", "stage", current_tier="cheap")

        assert "Insufficient data" not in rec.reason
        assert rec.recommended_tier == "cheap"
        assert rec.confidence == 0.5

    def test_confidence_saturates_at_double_min_samples(self):
        """sample_count=20 (== MIN_SAMPLES * 2) -> confidence hits 1.0."""
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider({"cheap": _stats("cheap", 0.8, count=20)})

        rec = loop.recommend_tier("wf", "stage", current_tier="cheap")

        assert rec.confidence == 1.0

    def test_confidence_capped_above_double_min_samples(self):
        """sample_count=50 -> confidence stays clamped at 1.0, not 2.5."""
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider({"cheap": _stats("cheap", 0.8, count=50)})

        rec = loop.recommend_tier("wf", "stage", current_tier="cheap")

        assert rec.confidence == 1.0

    def test_low_quality_premium_confidence_forced_to_one(self):
        """The 'already premium, low quality' branch overrides confidence
        to 1.0 regardless of sample_count, distinct from the normal
        formula (sample_count=15 would otherwise give confidence 0.75).
        """
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider({"premium": _stats("premium", 0.3, count=15)})

        rec = loop.recommend_tier("wf", "stage", current_tier="premium")

        assert rec.confidence == 1.0
        assert "Already using premium" in rec.reason


class TestQualityThresholdBoundaries:
    """The 0.7 (low-quality) and 0.9 (excellent-quality) cutoffs."""

    def test_quality_exactly_at_threshold_is_not_low(self):
        """avg_quality == QUALITY_THRESHOLD (0.7) exactly is NOT < 0.7,
        so it falls into the acceptable/maintain branch, not upgrade."""
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider({"cheap": _stats("cheap", 0.7)})

        rec = loop.recommend_tier("wf", "stage", current_tier="cheap")

        assert rec.recommended_tier == "cheap"
        assert "Acceptable quality" in rec.reason

    def test_quality_just_below_threshold_triggers_upgrade(self):
        """avg_quality just under 0.7 triggers the low-quality branch."""
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider(
            {"cheap": _stats("cheap", 0.6999999999999998)},
        )

        rec = loop.recommend_tier("wf", "stage", current_tier="cheap")

        assert rec.recommended_tier == "capable"
        assert "Low quality" in rec.reason

    def test_quality_exactly_at_0_9_is_not_excellent(self):
        """avg_quality == 0.9 exactly is NOT > 0.9, so a non-cheap tier
        stays on the acceptable/maintain branch rather than the
        excellent-quality downgrade/keep branch. Uses "capable" (not
        "cheap") so the cheap-tier exemption doesn't also mask this."""
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider({"capable": _stats("capable", 0.9)})

        rec = loop.recommend_tier("wf", "stage", current_tier="capable")

        assert rec.recommended_tier == "capable"
        assert "Acceptable quality" in rec.reason
        assert "Excellent" not in rec.reason

    def test_excellent_quality_on_cheap_tier_is_still_acceptable(self):
        """avg_quality > 0.9 on the "cheap" tier is exempted from the
        excellent-quality branch by `current_tier != "cheap"` and falls
        through to the plain acceptable/maintain branch instead."""
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider({"cheap": _stats("cheap", 0.99)})

        rec = loop.recommend_tier("wf", "stage", current_tier="cheap")

        assert rec.recommended_tier == "cheap"
        assert "Acceptable quality" in rec.reason
        assert "Excellent" not in rec.reason


class TestExcellentQualityCapableTier:
    """avg_quality > 0.9 with current_tier="capable" (downgrade target: cheap)."""

    def test_downgrades_to_cheap_when_cheap_stats_are_good(self):
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider(
            {
                "capable": _stats("capable", 0.95),
                "cheap": _stats("cheap", 0.9),
            },
        )

        rec = loop.recommend_tier("wf", "stage", current_tier="capable")

        assert rec.recommended_tier == "cheap"
        assert "downgrade to save cost" in rec.reason

    def test_keeps_capable_when_cheap_stats_missing(self):
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider({"capable": _stats("capable", 0.95)})

        rec = loop.recommend_tier("wf", "stage", current_tier="capable")

        assert rec.recommended_tier == "capable"
        assert "keep capable tier" in rec.reason

    def test_keeps_capable_when_cheap_quality_at_0_85_boundary(self):
        """cheap avg_quality == 0.85 exactly is NOT > 0.85, so no
        downgrade -- keeps capable."""
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider(
            {
                "capable": _stats("capable", 0.95),
                "cheap": _stats("cheap", 0.85),
            },
        )

        rec = loop.recommend_tier("wf", "stage", current_tier="capable")

        assert rec.recommended_tier == "capable"
        assert "keep capable tier" in rec.reason


class TestExcellentQualityPremiumTier:
    """avg_quality > 0.9 with current_tier="premium" (downgrade target: capable)."""

    def test_downgrades_to_capable_when_capable_stats_are_good(self):
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider(
            {
                "premium": _stats("premium", 0.95),
                "capable": _stats("capable", 0.9),
            },
        )

        rec = loop.recommend_tier("wf", "stage", current_tier="premium")

        assert rec.recommended_tier == "capable"
        assert "downgrade to save cost" in rec.reason

    def test_keeps_premium_when_capable_stats_missing(self):
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider({"premium": _stats("premium", 0.95)})

        rec = loop.recommend_tier("wf", "stage", current_tier="premium")

        assert rec.recommended_tier == "premium"
        assert "keep premium for consistency" in rec.reason

    def test_keeps_premium_when_capable_quality_at_0_85_boundary(self):
        """capable avg_quality == 0.85 exactly is NOT > 0.85, so no
        downgrade -- keeps premium."""
        loop = FeedbackLoop()
        loop.get_quality_stats = _stats_provider(
            {
                "premium": _stats("premium", 0.95),
                "capable": _stats("capable", 0.85),
            },
        )

        rec = loop.recommend_tier("wf", "stage", current_tier="premium")

        assert rec.recommended_tier == "premium"
        assert "keep premium for consistency" in rec.reason
