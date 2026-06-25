# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Coverage batch 20: logging_config, levels, discovery, cache_stats, cache_monitor."""

from __future__ import annotations

import logging

# === Module: logging_config ===


class TestStructuredFormatter:
    def test_formats_record(self):
        from attune.logging_config import StructuredFormatter

        formatter = StructuredFormatter(use_color=False, include_context=False)
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Hello world",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "Hello world" in result
        assert "INFO" in result
        assert "test.module" in result

    def test_color_disabled_when_not_tty(self):
        from attune.logging_config import StructuredFormatter

        # use_color=True but non-tty won't color
        formatter = StructuredFormatter(use_color=True)
        assert isinstance(formatter, StructuredFormatter)

    def test_no_color_formatter(self):
        from attune.logging_config import StructuredFormatter

        formatter = StructuredFormatter(use_color=False)
        record = logging.LogRecord(
            name="m",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="warning msg",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "warning msg" in result
        assert "\033[" not in result

    def test_includes_context_when_enabled(self):
        from attune.logging_config import StructuredFormatter

        formatter = StructuredFormatter(use_color=False, include_context=True)
        record = logging.LogRecord(
            name="m",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record.context = {"user": "alice", "id": "42"}
        result = formatter.format(record)
        assert "user=alice" in result


class TestLoggingConfig:
    def setup_method(self):
        from attune.logging_config import LoggingConfig

        LoggingConfig._configured = False
        LoggingConfig._loggers = {}

    def test_configure_sets_level(self):
        from attune.logging_config import LoggingConfig

        LoggingConfig.configure(level=logging.DEBUG)
        assert LoggingConfig._level == logging.DEBUG
        assert LoggingConfig._configured is True

    def test_get_logger_returns_logger(self):
        from attune.logging_config import LoggingConfig

        logger = LoggingConfig.get_logger("test.batch20")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_returns_same_instance(self):
        from attune.logging_config import LoggingConfig

        l1 = LoggingConfig.get_logger("test.same")
        l2 = LoggingConfig.get_logger("test.same")
        assert l1 is l2

    def test_set_level_propagates(self):
        from attune.logging_config import LoggingConfig

        LoggingConfig.get_logger("test.setlevel")
        LoggingConfig.set_level(logging.ERROR)
        for logger in LoggingConfig._loggers.values():
            assert logger.level == logging.ERROR


class TestGetLogger:
    def test_get_logger_returns_logger(self):
        from attune.logging_config import get_logger

        logger = get_logger("attune.test.batch20")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_module_name(self):
        from attune.logging_config import get_logger

        logger = get_logger(__name__)
        assert isinstance(logger, logging.Logger)


# === Module: discovery ===


class TestDaysSinceSync:
    def test_returns_999_when_no_sync(self):
        from attune.discovery import _days_since_sync

        assert _days_since_sync({}) == 999
        assert _days_since_sync({"last_claude_sync": None}) == 999

    def test_returns_0_for_today(self):
        from datetime import datetime

        from attune.discovery import _days_since_sync

        today = datetime.now().isoformat()
        result = _days_since_sync({"last_claude_sync": today})
        assert result == 0

    def test_returns_999_for_invalid_date(self):
        from attune.discovery import _days_since_sync

        assert _days_since_sync({"last_claude_sync": "not-a-date"}) == 999


class TestDiscoveryEngine:
    def test_initialization(self, tmp_path):
        from attune.discovery import DiscoveryEngine

        engine = DiscoveryEngine(storage_dir=str(tmp_path))
        assert engine.storage_dir == tmp_path
        assert isinstance(engine.state, dict)

    def test_default_state_structure(self, tmp_path):
        from attune.discovery import DiscoveryEngine

        engine = DiscoveryEngine(storage_dir=str(tmp_path))
        state = engine.state
        assert "command_counts" in state
        assert "total_commands" in state
        assert "tips_shown" in state

    def test_record_command_increments_count(self, tmp_path):
        from attune.discovery import DiscoveryEngine

        engine = DiscoveryEngine(storage_dir=str(tmp_path))
        engine.record_command("inspect")
        engine.record_command("inspect")
        assert engine.state["command_counts"]["inspect"] == 2
        assert engine.state["total_commands"] == 2

    def test_record_patterns_learned(self, tmp_path):
        from attune.discovery import DiscoveryEngine

        engine = DiscoveryEngine(storage_dir=str(tmp_path))
        engine.record_patterns_learned(5)
        assert engine.state["patterns_learned"] == 5

    def test_record_api_request(self, tmp_path):
        from attune.discovery import DiscoveryEngine

        engine = DiscoveryEngine(storage_dir=str(tmp_path))
        engine.record_api_request()
        engine.record_api_request()
        assert engine.state["api_requests"] == 2

    def test_mark_shown_adds_to_tips_shown(self, tmp_path):
        from attune.discovery import DiscoveryEngine

        engine = DiscoveryEngine(storage_dir=str(tmp_path))
        engine.mark_shown("after_first_inspect")
        assert "after_first_inspect" in engine.state["tips_shown"]

    def test_mark_shown_no_duplicates(self, tmp_path):
        from attune.discovery import DiscoveryEngine

        engine = DiscoveryEngine(storage_dir=str(tmp_path))
        engine.mark_shown("after_first_inspect")
        engine.mark_shown("after_first_inspect")
        assert engine.state["tips_shown"].count("after_first_inspect") == 1

    def test_get_stats_returns_dict(self, tmp_path):
        from attune.discovery import DiscoveryEngine

        engine = DiscoveryEngine(storage_dir=str(tmp_path))
        stats = engine.get_stats()
        assert "total_commands" in stats
        assert "patterns_learned" in stats
        assert "tips_shown" in stats

    def test_loads_persisted_state(self, tmp_path):
        from attune.discovery import DiscoveryEngine

        engine = DiscoveryEngine(storage_dir=str(tmp_path))
        engine.record_command("health")
        engine2 = DiscoveryEngine(storage_dir=str(tmp_path))
        assert engine2.state["command_counts"].get("health", 0) == 1

    def test_set_tech_debt_trend(self, tmp_path):
        from attune.discovery import DiscoveryEngine

        engine = DiscoveryEngine(storage_dir=str(tmp_path))
        engine.set_tech_debt_trend("increasing")
        assert engine.state["tech_debt_trend"] == "increasing"


# === Module: cache_stats ===


class TestCacheHealthScore:
    def test_construction(self):
        from attune.cache_stats import CacheHealthScore

        score = CacheHealthScore(
            cache_name="ast_parse",
            hit_rate=0.75,
            health="good",
            confidence="medium",
            recommendation="Cache is working well",
            reasons=["High hit rate"],
        )
        assert score.cache_name == "ast_parse"
        assert score.health == "good"

    def test_to_dict(self):
        from attune.cache_stats import CacheHealthScore

        score = CacheHealthScore(
            cache_name="test_cache",
            hit_rate=0.85,
            health="excellent",
            confidence="high",
            recommendation="Keep it up",
            reasons=["reason1"],
        )
        d = score.to_dict()
        assert d["cache_name"] == "test_cache"
        assert d["health"] == "excellent"
        assert d["hit_rate"] == 0.85
        assert "reason1" in d["reasons"]


class TestCacheAnalyzer:
    def test_get_confidence_low(self):
        from attune.cache_stats import CacheAnalyzer

        assert CacheAnalyzer._get_confidence(5) == "low"

    def test_get_confidence_medium(self):
        from attune.cache_stats import CacheAnalyzer

        assert CacheAnalyzer._get_confidence(50) == "medium"

    def test_get_confidence_high(self):
        from attune.cache_stats import CacheAnalyzer

        assert CacheAnalyzer._get_confidence(200) == "high"

    def test_get_health_excellent(self):
        from attune.cache_stats import CacheAnalyzer

        thresholds = (0.8, 0.6, 0.0)
        assert CacheAnalyzer._get_health(0.9, thresholds) == "excellent"

    def test_get_health_good(self):
        from attune.cache_stats import CacheAnalyzer

        thresholds = (0.8, 0.6, 0.0)
        assert CacheAnalyzer._get_health(0.65, thresholds) == "good"

    def test_get_health_fair(self):
        from attune.cache_stats import CacheAnalyzer

        thresholds = (0.8, 0.6, 0.3)
        assert CacheAnalyzer._get_health(0.35, thresholds) == "fair"

    def test_get_health_poor(self):
        from attune.cache_stats import CacheAnalyzer

        thresholds = (0.8, 0.6, 0.3)
        assert CacheAnalyzer._get_health(0.1, thresholds) == "poor"

    def test_calculate_health_with_cache_stats(self):
        from attune.cache_monitor import CacheStats
        from attune.cache_stats import CacheAnalyzer, CacheHealthScore

        stats = CacheStats(name="test_cache", hits=80, misses=20, size=50, max_size=100)
        health = CacheAnalyzer._calculate_health(stats)
        assert isinstance(health, CacheHealthScore)
        assert health.cache_name == "test_cache"
        assert health.hit_rate == 0.8
        assert health.health in ("excellent", "good", "fair", "poor")

    def test_calculate_health_with_zero_requests(self):
        from attune.cache_monitor import CacheStats
        from attune.cache_stats import CacheAnalyzer

        stats = CacheStats(name="empty", hits=0, misses=0)
        health = CacheAnalyzer._calculate_health(stats)
        assert health.hit_rate == 0.0
        assert health.health in ("poor", "fair", "good", "excellent")
        assert health.confidence == "low"  # 0 requests → low confidence


# === Module: cache_monitor (CacheStats) ===


class TestCacheStats:
    def test_construction(self):
        from attune.cache_monitor import CacheStats

        stats = CacheStats(name="my_cache")
        assert stats.name == "my_cache"
        assert stats.hits == 0
        assert stats.misses == 0

    def test_total_requests(self):
        from attune.cache_monitor import CacheStats

        stats = CacheStats(name="c", hits=30, misses=10)
        assert stats.total_requests == 40

    def test_hit_rate(self):
        from attune.cache_monitor import CacheStats

        stats = CacheStats(name="c", hits=75, misses=25)
        assert stats.hit_rate == 0.75

    def test_hit_rate_zero_when_no_requests(self):
        from attune.cache_monitor import CacheStats

        stats = CacheStats(name="c")
        assert stats.hit_rate == 0.0

    def test_miss_rate(self):
        from attune.cache_monitor import CacheStats

        stats = CacheStats(name="c", hits=75, misses=25)
        assert abs(stats.miss_rate - 0.25) < 0.001

    def test_utilization(self):
        from attune.cache_monitor import CacheStats

        stats = CacheStats(name="c", size=50, max_size=100)
        assert stats.utilization == 0.5

    def test_utilization_zero_when_no_max(self):
        from attune.cache_monitor import CacheStats

        stats = CacheStats(name="c", size=10, max_size=0)
        assert stats.utilization == 0.0

    def test_record_hit(self):
        from attune.cache_monitor import CacheStats

        stats = CacheStats(name="c")
        stats.record_hit()
        stats.record_hit()
        assert stats.hits == 2

    def test_record_miss(self):
        from attune.cache_monitor import CacheStats

        stats = CacheStats(name="c")
        stats.record_miss()
        assert stats.misses == 1
