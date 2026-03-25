"""Tests for cache_stats module — CacheHealthScore, CacheAnalyzer, CacheReporter."""

from __future__ import annotations

import pytest

from attune.cache_monitor import CacheMonitor, CacheStats
from attune.cache_stats import CacheAnalyzer, CacheHealthScore, CacheReporter


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the CacheMonitor singleton before and after each test."""
    CacheMonitor.reset_instance()
    yield
    CacheMonitor.reset_instance()


# ---------------------------------------------------------------------------
# CacheHealthScore dataclass
# ---------------------------------------------------------------------------


class TestCacheHealthScore:
    """CacheHealthScore creation and serialization."""

    def test_to_dict_round_trips_all_fields(self):
        score = CacheHealthScore(
            cache_name="test",
            hit_rate=0.7531,
            health="good",
            confidence="high",
            recommendation="Keep monitoring",
            reasons=["Strong hit rate"],
        )
        d = score.to_dict()
        assert d["cache_name"] == "test"
        assert d["hit_rate"] == 0.7531
        assert d["health"] == "good"
        assert d["confidence"] == "high"
        assert d["recommendation"] == "Keep monitoring"
        assert d["reasons"] == ["Strong hit rate"]

    def test_to_dict_rounds_hit_rate(self):
        score = CacheHealthScore(
            cache_name="x",
            hit_rate=0.123456789,
            health="fair",
            confidence="low",
            recommendation="",
            reasons=[],
        )
        assert score.to_dict()["hit_rate"] == 0.1235


# ---------------------------------------------------------------------------
# CacheAnalyzer._calculate_health — low request count (< 10)
# ---------------------------------------------------------------------------


class TestCalculateHealthLowRequests:
    """Health calculation with < 10 total requests (low confidence)."""

    def test_excellent_when_hit_rate_above_80pct(self):
        stats = CacheStats(name="c", hits=8, misses=1, max_size=100)
        # 9 total requests => < 10 => low confidence
        health = CacheAnalyzer._calculate_health(stats)
        assert health.health == "excellent"
        assert health.confidence == "low"

    def test_good_when_hit_rate_between_60_and_80(self):
        stats = CacheStats(name="c", hits=6, misses=3, max_size=100)
        # 9 total, hit_rate ~0.667 => good, low confidence
        health = CacheAnalyzer._calculate_health(stats)
        assert health.health == "good"
        assert health.confidence == "low"

    def test_fair_when_hit_rate_below_60(self):
        stats = CacheStats(name="c", hits=3, misses=6, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert health.health == "fair"
        assert health.confidence == "low"


# ---------------------------------------------------------------------------
# CacheAnalyzer._calculate_health — medium request count (10-99)
# ---------------------------------------------------------------------------


class TestCalculateHealthMediumRequests:
    """Health calculation with 10-99 total requests (medium confidence)."""

    def test_excellent_when_hit_rate_above_70(self):
        stats = CacheStats(name="c", hits=35, misses=15, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert health.health == "excellent"
        assert health.confidence == "medium"

    def test_good_when_hit_rate_between_50_and_70(self):
        stats = CacheStats(name="c", hits=30, misses=20, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert health.health == "good"
        assert health.confidence == "medium"

    def test_fair_when_hit_rate_between_30_and_50(self):
        stats = CacheStats(name="c", hits=18, misses=32, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert health.health == "fair"
        assert health.confidence == "medium"

    def test_poor_when_hit_rate_below_30(self):
        stats = CacheStats(name="c", hits=10, misses=40, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert health.health == "poor"
        assert health.confidence == "medium"


# ---------------------------------------------------------------------------
# CacheAnalyzer._calculate_health — high request count (100+)
# ---------------------------------------------------------------------------


class TestCalculateHealthHighRequests:
    """Health calculation with >= 100 total requests (high confidence)."""

    def test_excellent_when_hit_rate_above_60(self):
        stats = CacheStats(name="c", hits=70, misses=30, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert health.health == "excellent"
        assert health.confidence == "high"

    def test_good_when_hit_rate_between_40_and_60(self):
        stats = CacheStats(name="c", hits=50, misses=50, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert health.health == "good"
        assert health.confidence == "high"

    def test_fair_when_hit_rate_between_20_and_40(self):
        stats = CacheStats(name="c", hits=25, misses=75, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert health.health == "fair"
        assert health.confidence == "high"

    def test_poor_when_hit_rate_below_20(self):
        stats = CacheStats(name="c", hits=10, misses=90, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert health.health == "poor"
        assert health.confidence == "high"


# ---------------------------------------------------------------------------
# CacheAnalyzer._calculate_health — recommendations / reasons
# ---------------------------------------------------------------------------


class TestCalculateHealthRecommendations:
    """Recommendation and reason text in health scores."""

    def test_strong_hit_rate_high_volume_recommendation(self):
        stats = CacheStats(name="c", hits=80, misses=20, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert "performing well" in health.recommendation

    def test_strong_hit_rate_low_volume_recommendation(self):
        stats = CacheStats(name="c", hits=8, misses=1, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert "promise" in health.recommendation

    def test_moderate_hit_rate_recommendation(self):
        stats = CacheStats(name="c", hits=60, misses=40, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert "cache key strategy" in health.recommendation

    def test_low_hit_rate_recommendation(self):
        stats = CacheStats(name="c", hits=25, misses=75, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert "invalidation strategy" in health.recommendation

    def test_very_low_hit_rate_recommendation(self):
        stats = CacheStats(name="c", hits=5, misses=95, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert "disabling" in health.recommendation

    def test_high_utilization_appends_size_recommendation(self):
        stats = CacheStats(name="c", hits=70, misses=30, size=95, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert "increasing cache size" in health.recommendation
        assert "nearly full" in health.reasons[-1]

    def test_low_utilization_appends_reduce_recommendation(self):
        stats = CacheStats(name="c", hits=30, misses=25, size=5, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert "reducing cache size" in health.recommendation
        assert "underutilized" in health.reasons[-1]

    def test_thrashing_detected_at_high_volume_low_hit_rate(self):
        stats = CacheStats(name="c", hits=100, misses=1000, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert any("thrashing" in r for r in health.reasons)


# ---------------------------------------------------------------------------
# CacheAnalyzer.analyze_cache / analyze_all
# ---------------------------------------------------------------------------


class TestCacheAnalyzerPublicAPI:
    """Public methods on CacheAnalyzer."""

    def test_analyze_cache_returns_none_for_unknown(self):
        assert CacheAnalyzer.analyze_cache("nonexistent") is None

    def test_analyze_cache_returns_health_score(self):
        monitor = CacheMonitor.get_instance()
        monitor.register_cache("demo", max_size=100)
        for _ in range(50):
            monitor.record_hit("demo")
        for _ in range(50):
            monitor.record_miss("demo")

        result = CacheAnalyzer.analyze_cache("demo")
        assert isinstance(result, CacheHealthScore)
        assert result.cache_name == "demo"

    def test_analyze_all_returns_dict(self):
        monitor = CacheMonitor.get_instance()
        monitor.register_cache("a", max_size=10)
        monitor.register_cache("b", max_size=10)
        monitor.record_hit("a")
        monitor.record_miss("b")

        results = CacheAnalyzer.analyze_all()
        assert "a" in results
        assert "b" in results
        assert isinstance(results["a"], CacheHealthScore)

    def test_analyze_all_empty_when_no_caches(self):
        results = CacheAnalyzer.analyze_all()
        assert results == {}


# ---------------------------------------------------------------------------
# CacheReporter
# ---------------------------------------------------------------------------


class TestCacheReporterHealthReport:
    """CacheReporter.generate_health_report."""

    def test_no_caches_message(self):
        report = CacheReporter.generate_health_report()
        assert "No caches registered" in report

    def test_contains_header_and_summary(self):
        monitor = CacheMonitor.get_instance()
        monitor.register_cache("alpha", max_size=100)
        for _ in range(20):
            monitor.record_hit("alpha")
        for _ in range(10):
            monitor.record_miss("alpha")

        report = CacheReporter.generate_health_report()
        assert "CACHE HEALTH REPORT" in report
        assert "SUMMARY" in report
        assert "alpha" in report

    def test_verbose_includes_reasons(self):
        monitor = CacheMonitor.get_instance()
        monitor.register_cache("beta", max_size=100)
        for _ in range(80):
            monitor.record_hit("beta")
        for _ in range(20):
            monitor.record_miss("beta")

        report = CacheReporter.generate_health_report(verbose=True)
        assert "hit rate" in report.lower() or "cache effectiveness" in report.lower()

    def test_sorts_by_health_then_hit_rate(self):
        monitor = CacheMonitor.get_instance()
        monitor.register_cache("poor_cache", max_size=100)
        monitor.register_cache("good_cache", max_size=100)

        for _ in range(100):
            monitor.record_miss("poor_cache")
        for _ in range(80):
            monitor.record_hit("good_cache")
        for _ in range(20):
            monitor.record_miss("good_cache")

        report = CacheReporter.generate_health_report()
        good_pos = report.index("good_cache")
        poor_pos = report.index("poor_cache")
        assert good_pos < poor_pos

    def test_summary_counts(self):
        monitor = CacheMonitor.get_instance()
        monitor.register_cache("c1", max_size=100)
        for _ in range(100):
            monitor.record_hit("c1")

        report = CacheReporter.generate_health_report()
        assert "Total Caches:    1" in report


class TestCacheReporterOptimizationReport:
    """CacheReporter.generate_optimization_report."""

    def test_optimization_report_structure(self):
        monitor = CacheMonitor.get_instance()
        monitor.register_cache("low", max_size=100)
        monitor.register_cache("high", max_size=100)

        for _ in range(50):
            monitor.record_miss("low")
        for _ in range(80):
            monitor.record_hit("high")
        for _ in range(20):
            monitor.record_miss("high")

        report = CacheReporter.generate_optimization_report()
        assert "OPTIMIZATION OPPORTUNITIES" in report
        assert "LOW-PERFORMING" in report
        assert "HIGH-PERFORMING" in report

    def test_optimization_report_no_underperformers(self):
        monitor = CacheMonitor.get_instance()
        monitor.register_cache("good", max_size=100)
        for _ in range(80):
            monitor.record_hit("good")

        report = CacheReporter.generate_optimization_report()
        assert "LOW-PERFORMING" not in report


class TestCacheReporterFullReport:
    """CacheReporter.generate_full_report."""

    def test_full_report_combines_sections(self):
        monitor = CacheMonitor.get_instance()
        monitor.register_cache("main", max_size=100)
        for _ in range(30):
            monitor.record_hit("main")
        for _ in range(20):
            monitor.record_miss("main")

        report = CacheReporter.generate_full_report()
        assert "COMPREHENSIVE CACHE ANALYSIS REPORT" in report
        assert "CACHE HEALTH REPORT" in report
        assert "OPTIMIZATION OPPORTUNITIES" in report
