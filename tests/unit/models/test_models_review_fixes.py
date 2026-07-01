"""Regression guards for the ``src/attune/models`` review fixes.

Each test pins a specific HIGH/MEDIUM bug the code review found so it
cannot silently return. See the review for context.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import attune.models.telemetry as tel
from attune.models.adaptive_routing import AdaptiveModelRouter
from attune.models.circuit_breaker import CircuitBreaker
from attune.models.telemetry.data_models import LLMCallRecord
from attune.models.telemetry.storage import TelemetryStore
from attune.telemetry.usage_ping import _endpoint_host_blocked


@pytest.mark.unit
class TestTelemetryConvenienceFunctions:
    """H1/H2: the module-level helpers called non-existent store methods
    (``log_llm_call`` / ``log_workflow_run``) — an AttributeError on the
    public API. They must call ``log_call`` / ``log_workflow``.
    """

    def test_helpers_call_the_real_store_methods(self, monkeypatch):
        mock_store = MagicMock()
        monkeypatch.setattr(tel, "get_telemetry_store", lambda: mock_store)

        tel.log_llm_call("rec-a")
        tel.log_workflow_run("rec-b")

        mock_store.log_call.assert_called_once_with("rec-a")
        mock_store.log_workflow.assert_called_once_with("rec-b")
        # The old (broken) method names must never be used.
        assert not mock_store.log_llm_call.called
        assert not mock_store.log_workflow_run.called


@pytest.mark.unit
class TestTelemetryStoreSecurity:
    """H4: storage_dir reached the filesystem with no path validation."""

    def test_rejects_system_directory(self):
        with pytest.raises(ValueError):
            TelemetryStore(storage_dir="/etc/cron.d")

    def test_allows_a_normal_directory(self, tmp_path):
        store = TelemetryStore(storage_dir=str(tmp_path / "telemetry"))
        assert store.storage_dir.exists()


@pytest.mark.unit
class TestReadJsonlRecency:
    """M2: ``_read_jsonl`` truncated from the OLDEST records — "recent"
    reads returned stale data once a log exceeded ``limit``.
    """

    def test_get_calls_returns_the_most_recent(self, tmp_path):
        store = TelemetryStore(storage_dir=str(tmp_path))
        for i in range(5):  # appended oldest -> newest
            store.log_call(LLMCallRecord(call_id=str(i), timestamp=f"2026-01-0{i + 1}T00:00:00Z"))

        recent = store.get_calls(limit=2)

        assert {r.call_id for r in recent} == {"3", "4"}  # newest two, not {"0","1"}
        assert recent[-1].call_id == "4"  # records[-1] is the latest


@pytest.mark.unit
class TestUsagePingSsrfGuard:
    """M5: ``sync`` validated only the scheme, not the host."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://169.254.169.254/latest/meta-data",  # cloud metadata
            "http://127.0.0.1:9000",
            "http://localhost/collect",
            "http://10.0.0.5/x",
            "http://192.168.1.1/x",
            "http://[::1]/x",
        ],
    )
    def test_blocks_internal_hosts(self, url):
        assert _endpoint_host_blocked(url) is True

    def test_allows_a_public_host(self):
        assert _endpoint_host_blocked("https://telemetry.example.com/collect") is False


@pytest.mark.unit
class TestCircuitBreakerHalfOpen:
    """M8: ``half_open_calls`` was stored but never enforced — after the
    recovery timeout every call was let through.
    """

    def test_half_open_limits_probe_calls(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=0, half_open_calls=1)
        cb.record_failure("anthropic", "capable")
        cb.record_failure("anthropic", "capable")  # opens the circuit

        # recovery_timeout=0 -> immediately half-open; only ONE probe allowed
        assert cb.is_available("anthropic", "capable") is True
        assert cb.is_available("anthropic", "capable") is False  # budget spent

        cb.record_success("anthropic", "capable")  # a probe succeeded -> closed
        assert cb.is_available("anthropic", "capable") is True


@pytest.mark.unit
class TestAdaptiveRoutingLogging:
    """H3: the module used a stdlib logger but called it with structlog
    keyword events (``logger.warning("event", key=val)``) — a TypeError
    the moment the no-candidates path emitted.
    """

    def test_no_candidates_path_does_not_crash(self):
        telemetry = MagicMock()
        telemetry.get_recent_entries.return_value = [
            {
                "workflow": "w",
                "stage": "s",
                "model": "m",
                "tier": "capable",
                "success": True,
                "cost": 1.0,
                "duration_ms": 100,
            }
            for _ in range(10)
        ]
        router = AdaptiveModelRouter(telemetry)

        # An impossibly tight cost constraint filters every candidate out,
        # forcing the logger.warning("adaptive_routing_no_candidates", ...) path.
        result = router.get_best_model("w", "s", max_cost=0.0001)

        assert isinstance(result, str) and result  # returns a fallback, no TypeError

    def test_recent_window_counts_newest_calls(self):
        # get_recent_entries is newest-first; the 5 most-recent are failures.
        telemetry = MagicMock()
        telemetry.get_recent_entries.return_value = [
            {
                "workflow": "w",
                "stage": "s",
                "model": "m",
                "tier": "capable",
                "success": i >= 5,
                "cost": 0.001,
                "duration_ms": 100,
            }
            for i in range(30)
        ]
        router = AdaptiveModelRouter(telemetry)

        perfs = router._analyze_model_performance("w", "s")

        assert len(perfs) == 1
        assert perfs[0].recent_failures == 5
