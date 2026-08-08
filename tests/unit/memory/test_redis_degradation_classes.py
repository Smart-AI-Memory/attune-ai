"""Tests for classified loud-once degradation — redis-config-truth rct-2.

Pins R3 at the resolver-consumer seam: four health classes
(healthy / degraded_auth / degraded_connectivity / disabled), the
loud-once notice for never-self-healing classes (auth rejection,
malformed config), silence for server-absent, once-per-process
semantics (the task block's named risk), P15 never-block, and
secret redaction in every message.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
import redis as redis_lib

from attune.memory.features import (
    MemoryFeatures,
    RedisHealthReport,
    RedisHealthState,
    reset_redis_health_warnings,
)

FEATURES_LOGGER = "attune.memory.features"


@pytest.fixture(autouse=True)
def _fresh_warning_state():
    """Each test starts with a fresh loud-once session scope."""
    reset_redis_health_warnings()
    yield
    reset_redis_health_warnings()


def _client_raising(exc: Exception) -> MagicMock:
    client = MagicMock()
    client.ping.side_effect = exc
    return client


class TestClassification:
    def test_healthy_when_ping_succeeds(self):
        client = MagicMock()
        client.ping.return_value = True
        with patch.object(redis_lib.Redis, "from_url", return_value=client):
            r = MemoryFeatures.classify_redis_health(env={"REDIS_URL": "redis://h:6379/0"})
        assert r.state is RedisHealthState.HEALTHY
        assert r.redacted_url == "redis://h:6379/0"

    def test_auth_error_classifies_degraded_auth(self):
        exc = redis_lib.exceptions.AuthenticationError("invalid password")
        with patch.object(redis_lib.Redis, "from_url", return_value=_client_raising(exc)):
            r = MemoryFeatures.classify_redis_health(
                env={
                    "REDIS_URL": "redis://h:6379/0",
                    "REDIS_PASSWORD": "wrongpw",  # pragma: allowlist secret
                }
            )
        assert r.state is RedisHealthState.DEGRADED_AUTH
        assert "authentication rejected" in r.detail
        assert "wrongpw" not in (r.detail + (r.redacted_url or ""))

    def test_connection_refused_classifies_degraded_connectivity(self):
        exc = redis_lib.exceptions.ConnectionError("Connection refused")
        with patch.object(redis_lib.Redis, "from_url", return_value=_client_raising(exc)):
            r = MemoryFeatures.classify_redis_health(env={"REDIS_URL": "redis://h:6379/0"})
        assert r.state is RedisHealthState.DEGRADED_CONNECTIVITY

    def test_malformed_config_classifies_degraded_auth(self):
        """Invalid config never self-heals — same loud class as auth (R3)."""
        r = MemoryFeatures.classify_redis_health(env={"REDIS_URL": "redis://h:notaport/0"})
        assert r.state is RedisHealthState.DEGRADED_AUTH
        assert "non-numeric port" in r.detail

    def test_mock_env_classifies_disabled(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_REDIS_MOCK", "true")
        r = MemoryFeatures.classify_redis_health()
        assert r.state is RedisHealthState.DISABLED

    def test_mock_flag_respected_from_injected_env(self, monkeypatch):
        """The injected env mapping decides — not process state."""
        monkeypatch.delenv("ATTUNE_REDIS_MOCK", raising=False)
        r = MemoryFeatures.classify_redis_health(env={"ATTUNE_REDIS_MOCK": "true"})
        assert r.state is RedisHealthState.DISABLED

    def test_process_mock_flag_ignored_when_env_injected(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_REDIS_MOCK", "true")
        r = MemoryFeatures.classify_redis_health(env={"REDIS_URL": "redis://127.0.0.1:1/0"})
        assert r.state is RedisHealthState.DEGRADED_CONNECTIVITY

    def test_malformed_config_detail_scrubs_embedded_credentials(self):
        """Defensive: a resolver message carrying a credentialed URL is scrubbed."""
        with patch(
            "attune.memory.config.resolve_redis_connection",
            side_effect=ValueError("bad URL redis://u:sekret@h:6379/0"),  # pragma: allowlist secret
        ):
            r = MemoryFeatures.classify_redis_health(env={"REDIS_URL": "redis://h:6379/0"})
        assert r.state is RedisHealthState.DEGRADED_AUTH
        assert "sekret" not in r.detail
        assert "redis://u:***@h:6379/0" in r.detail

    def test_missing_package_classifies_degraded_connectivity(self):
        with patch.object(MemoryFeatures, "is_redis_available", return_value=False):
            r = MemoryFeatures.classify_redis_health(env={})
        assert r.state is RedisHealthState.DEGRADED_CONNECTIVITY
        assert "not importable" in r.detail


class TestLoudOnce:
    """The XML block's validation checks: auth warns ONCE, refused never."""

    def test_auth_failure_warns_exactly_once(self, caplog):
        exc = redis_lib.exceptions.AuthenticationError("invalid password")
        with patch.object(redis_lib.Redis, "from_url", return_value=_client_raising(exc)):
            env_patch = patch.dict(
                "os.environ",
                {
                    "REDIS_URL": "redis://h:6379/0",
                    "REDIS_PASSWORD": "wrongpw",  # pragma: allowlist secret
                },
                clear=False,
            )
            with env_patch, caplog.at_level(logging.WARNING, logger=FEATURES_LOGGER):
                first = MemoryFeatures.check_redis()
                second = MemoryFeatures.check_redis()
        assert first is False and second is False
        notices = [rec for rec in caplog.records if "degraded_auth" in rec.getMessage()]
        assert len(notices) == 1, "auth degradation must warn exactly ONCE per session"

    def test_connection_refused_stays_silent(self, caplog):
        exc = redis_lib.exceptions.ConnectionError("Connection refused")
        with patch.object(redis_lib.Redis, "from_url", return_value=_client_raising(exc)):
            with (
                patch.dict("os.environ", {"REDIS_URL": "redis://h:6379/0"}, clear=False),
                caplog.at_level(logging.WARNING, logger=FEATURES_LOGGER),
            ):
                assert MemoryFeatures.check_redis() is False
        assert [rec for rec in caplog.records if rec.levelno >= logging.WARNING] == []

    def test_reset_reopens_the_once_scope(self, caplog):
        """Once-per-PROCESS semantics, reopened only by explicit reset."""
        exc = redis_lib.exceptions.AuthenticationError("invalid password")
        with patch.object(redis_lib.Redis, "from_url", return_value=_client_raising(exc)):
            with (
                patch.dict("os.environ", {"REDIS_URL": "redis://h:6379/0"}, clear=False),
                caplog.at_level(logging.WARNING, logger=FEATURES_LOGGER),
            ):
                MemoryFeatures.check_redis()
                reset_redis_health_warnings()
                MemoryFeatures.check_redis()
        notices = [rec for rec in caplog.records if "degraded_auth" in rec.getMessage()]
        assert len(notices) == 2

    def test_warning_message_redacts_password(self, caplog):
        exc = redis_lib.exceptions.AuthenticationError("invalid password")
        with patch.object(redis_lib.Redis, "from_url", return_value=_client_raising(exc)):
            with (
                patch.dict(
                    "os.environ",
                    {
                        "REDIS_URL": "redis://h:6379/0",
                        "REDIS_PASSWORD": "sup3rsecret",  # pragma: allowlist secret
                    },
                    clear=False,
                ),
                caplog.at_level(logging.WARNING, logger=FEATURES_LOGGER),
            ):
                MemoryFeatures.check_redis()
        joined = " ".join(rec.getMessage() for rec in caplog.records)
        assert "sup3rsecret" not in joined
        assert "***" in joined


class TestNeverBlock:
    """P15: no failure class raises out of the fail-open gate."""

    @pytest.mark.parametrize(
        "exc",
        [
            redis_lib.exceptions.AuthenticationError("nope"),
            redis_lib.exceptions.ConnectionError("refused"),
            redis_lib.exceptions.TimeoutError("slow"),
            OSError("socket down"),
            RuntimeError("unexpected"),
        ],
    )
    def test_check_redis_never_raises(self, exc):
        with patch.object(redis_lib.Redis, "from_url", return_value=_client_raising(exc)):
            with patch.dict("os.environ", {"REDIS_URL": "redis://h:6379/0"}, clear=False):
                assert MemoryFeatures.check_redis() is False

    def test_malformed_config_does_not_raise_from_check(self):
        with patch.dict("os.environ", {"REDIS_URL": "redis://h:notaport/0"}, clear=False):
            assert MemoryFeatures.check_redis() is False

    def test_classify_returns_report_for_every_class(self):
        """The seam always yields a typed report, never an exception."""
        r = MemoryFeatures.classify_redis_health(env={"REDIS_URL": "redis://127.0.0.1:1/0"})
        assert isinstance(r, RedisHealthReport)
