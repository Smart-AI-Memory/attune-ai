"""Unit tests for attune.metrics.collector module.

Tests cover:
- MetricsCollector initialization with and without db_path
- collect() returns an empty dict
- get_stats() returns an empty dict

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.metrics.collector import MetricsCollector


@pytest.mark.unit
class TestMetricsCollector:
    """Tests for MetricsCollector stub class."""

    def test_init_default_db_path_is_none(self) -> None:
        """Test that default db_path is None when not provided."""
        collector = MetricsCollector()
        assert collector.db_path is None

    def test_init_stores_db_path(self) -> None:
        """Test that db_path is stored as provided."""
        collector = MetricsCollector(db_path="/tmp/metrics.db")
        assert collector.db_path == "/tmp/metrics.db"

    def test_init_with_none_db_path_explicitly(self) -> None:
        """Test explicit None db_path."""
        collector = MetricsCollector(db_path=None)
        assert collector.db_path is None

    def test_collect_returns_empty_dict(self) -> None:
        """Test that collect() returns an empty dict."""
        collector = MetricsCollector()
        result = collector.collect()
        assert result == {}

    def test_collect_returns_dict_type(self) -> None:
        """Test that collect() returns a dict instance."""
        collector = MetricsCollector()
        result = collector.collect()
        assert isinstance(result, dict)

    def test_collect_with_db_path_still_returns_empty_dict(self) -> None:
        """Test that collect() returns empty dict regardless of db_path."""
        collector = MetricsCollector(db_path="/tmp/metrics.db")
        result = collector.collect()
        assert result == {}

    def test_get_stats_returns_empty_dict(self) -> None:
        """Test that get_stats() returns an empty dict."""
        collector = MetricsCollector()
        result = collector.get_stats()
        assert result == {}

    def test_get_stats_returns_dict_type(self) -> None:
        """Test that get_stats() returns a dict instance."""
        collector = MetricsCollector()
        result = collector.get_stats()
        assert isinstance(result, dict)

    def test_get_stats_with_db_path_still_returns_empty_dict(self) -> None:
        """Test that get_stats() returns empty dict regardless of db_path."""
        collector = MetricsCollector(db_path="/some/path.db")
        result = collector.get_stats()
        assert result == {}

    def test_multiple_collect_calls_all_return_empty(self) -> None:
        """Test that repeated collect() calls each return empty dicts."""
        collector = MetricsCollector()
        for _ in range(3):
            assert collector.collect() == {}

    def test_multiple_get_stats_calls_all_return_empty(self) -> None:
        """Test that repeated get_stats() calls each return empty dicts."""
        collector = MetricsCollector()
        for _ in range(3):
            assert collector.get_stats() == {}

    def test_collect_and_get_stats_are_independent(self) -> None:
        """Test that collect and get_stats each return separate empty dicts."""
        collector = MetricsCollector()
        r1 = collector.collect()
        r2 = collector.get_stats()
        assert r1 == r2 == {}
