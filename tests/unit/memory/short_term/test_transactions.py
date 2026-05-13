"""Tests for `attune.memory.short_term.transactions.TransactionManager`.

Covers the atomic pattern-promotion path in both mock mode (the
default for the test suite without a real Redis) and the real-
Redis branch (via a mocked client). The drift-guard goal is
behavioral: every branch in `atomic_promote_pattern` is exercised
including the validation errors, mock vs. real-client divergence,
and the WATCH/MULTI/EXEC race-condition handler.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from attune.memory.short_term import transactions as _transactions_mod
from attune.memory.short_term.base import BaseOperations
from attune.memory.short_term.transactions import TransactionManager
from attune.memory.types import (
    AccessTier,
    AgentCredentials,
    StagedPattern,
)

# Reference `redis` via the already-imported source module to avoid
# triggering "PyO3 modules compiled for CPython 3.8 or older may
# only be initialized once" on some interpreters.
redis = _transactions_mod.redis


def _make_staged_pattern(
    pattern_id: str = "pat_123",
    agent_id: str = "agent_1",
    confidence: float = 0.8,
) -> StagedPattern:
    """Build a valid StagedPattern for tests."""
    return StagedPattern(
        pattern_id=pattern_id,
        agent_id=agent_id,
        pattern_type="behavioral",
        name="test pattern",
        description="for unit tests",
        confidence=confidence,
    )


def _validator_creds(agent_id: str = "validator_1") -> AgentCredentials:
    return AgentCredentials(agent_id=agent_id, tier=AccessTier.VALIDATOR)


def _observer_creds(agent_id: str = "observer_1") -> AgentCredentials:
    return AgentCredentials(agent_id=agent_id, tier=AccessTier.OBSERVER)


@pytest.fixture
def mock_caching():
    """A mocked CacheManager with a tracked invalidate() spy."""
    return MagicMock()


@pytest.fixture
def base_mock_mode():
    """BaseOperations forced into mock mode."""
    return BaseOperations(use_mock=True)


@pytest.fixture
def transactions(base_mock_mode, mock_caching):
    """TransactionManager wired to mock-mode base + mocked cache."""
    return TransactionManager(base=base_mock_mode, caching=mock_caching)


class TestInputValidation:
    """Pattern 1 + Pattern 4 validation guards."""

    def test_empty_pattern_id_raises(self, transactions):
        with pytest.raises(ValueError, match="pattern_id cannot be empty"):
            transactions.atomic_promote_pattern("", _validator_creds())

    def test_whitespace_pattern_id_raises(self, transactions):
        with pytest.raises(ValueError, match="pattern_id cannot be empty"):
            transactions.atomic_promote_pattern("   ", _validator_creds())

    def test_min_confidence_below_range_raises(self, transactions):
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            transactions.atomic_promote_pattern("pat_1", _validator_creds(), min_confidence=-0.1)

    def test_min_confidence_above_range_raises(self, transactions):
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            transactions.atomic_promote_pattern("pat_1", _validator_creds(), min_confidence=1.5)


class TestAuthorization:
    """can_validate() gate."""

    def test_observer_credentials_rejected(self, transactions):
        ok, pattern, msg = transactions.atomic_promote_pattern("pat_1", _observer_creds())
        assert ok is False
        assert pattern is None
        assert "VALIDATOR" in msg

    def test_contributor_credentials_rejected(self, transactions):
        creds = AgentCredentials(agent_id="c1", tier=AccessTier.CONTRIBUTOR)
        ok, pattern, msg = transactions.atomic_promote_pattern("pat_1", creds)
        assert ok is False
        assert pattern is None
        assert "VALIDATOR" in msg

    def test_steward_credentials_accepted_when_pattern_missing(self, transactions):
        # Steward tier >= validator tier so it passes the auth gate;
        # exercises the "pattern not found" branch below.
        creds = AgentCredentials(agent_id="s1", tier=AccessTier.STEWARD)
        ok, _, msg = transactions.atomic_promote_pattern("pat_missing", creds)
        assert ok is False
        assert "not found" in msg


class TestMockModePath:
    """Covers the `if self._base.use_mock:` branches."""

    def test_pattern_not_in_mock_storage(self, transactions):
        ok, pattern, msg = transactions.atomic_promote_pattern("pat_missing", _validator_creds())
        assert ok is False
        assert pattern is None
        assert msg == "Pattern not found"

    def test_expired_pattern_returns_expired(self, transactions, base_mock_mode):
        key = f"{TransactionManager.PREFIX_STAGED}pat_expired"
        pattern = _make_staged_pattern("pat_expired")
        expired_ts = (datetime.now() - timedelta(seconds=10)).timestamp()
        base_mock_mode._mock_storage[key] = (
            json.dumps(_as_dict(pattern)),
            expired_ts,
        )

        ok, returned, msg = transactions.atomic_promote_pattern("pat_expired", _validator_creds())

        assert ok is False
        assert returned is None
        assert msg == "Pattern expired"

    def test_confidence_below_threshold(self, transactions, base_mock_mode):
        key = f"{TransactionManager.PREFIX_STAGED}pat_lowconf"
        pattern = _make_staged_pattern("pat_lowconf", confidence=0.3)
        base_mock_mode._mock_storage[key] = (json.dumps(_as_dict(pattern)), None)

        ok, returned, msg = transactions.atomic_promote_pattern(
            "pat_lowconf", _validator_creds(), min_confidence=0.7
        )

        assert ok is False
        assert returned is None
        assert "below threshold" in msg
        # Pattern stays in storage when promotion is rejected.
        assert key in base_mock_mode._mock_storage

    def test_successful_promotion_deletes_from_storage_and_invalidates_cache(
        self, transactions, base_mock_mode, mock_caching
    ):
        key = f"{TransactionManager.PREFIX_STAGED}pat_ok"
        pattern = _make_staged_pattern("pat_ok", confidence=0.9)
        base_mock_mode._mock_storage[key] = (json.dumps(_as_dict(pattern)), None)

        ok, returned, msg = transactions.atomic_promote_pattern(
            "pat_ok", _validator_creds(), min_confidence=0.5
        )

        assert ok is True
        assert isinstance(returned, StagedPattern)
        assert returned.pattern_id == "pat_ok"
        assert returned.confidence == 0.9
        assert msg == "Pattern promoted successfully"
        # Storage must be cleared atomically.
        assert key not in base_mock_mode._mock_storage
        # Cache invalidation must be called.
        mock_caching.invalidate.assert_called_once_with(key)


class TestRealRedisPath:
    """Covers the non-mock branch via a mocked Redis client."""

    @pytest.fixture
    def real_transactions(self, mock_caching):
        """TransactionManager with a base that has use_mock=False
        and a mocked _client attached directly."""
        base = BaseOperations(use_mock=True)
        # Flip back to "real" mode so the second `if self._base.use_mock:`
        # branch is skipped, then inject a mocked client per the
        # documented "memory._base._client = mock_client" pattern.
        base.use_mock = False
        base._client = MagicMock()
        return TransactionManager(base=base, caching=mock_caching), base

    def test_client_none_returns_not_connected(self, mock_caching):
        base = BaseOperations(use_mock=True)
        base.use_mock = False
        base._client = None
        tx = TransactionManager(base=base, caching=mock_caching)

        ok, pattern, msg = tx.atomic_promote_pattern("pat_x", _validator_creds())

        assert ok is False
        assert pattern is None
        assert msg == "Redis not connected"

    def test_pattern_not_found_in_redis(self, real_transactions):
        tx, base = real_transactions
        base._client.get.return_value = None

        ok, pattern, msg = tx.atomic_promote_pattern("pat_x", _validator_creds())

        assert ok is False
        assert pattern is None
        assert msg == "Pattern not found"
        # WATCH was set; UNWATCH followed (both in body and finally).
        base._client.watch.assert_called_once()
        assert base._client.unwatch.call_count >= 1

    def test_pattern_below_threshold_in_redis(self, real_transactions):
        tx, base = real_transactions
        pattern = _make_staged_pattern("pat_low", confidence=0.4)
        base._client.get.return_value = json.dumps(_as_dict(pattern))

        ok, returned, msg = tx.atomic_promote_pattern(
            "pat_low", _validator_creds(), min_confidence=0.7
        )

        assert ok is False
        assert returned is None
        assert "below threshold" in msg
        # Pipeline never built since we bailed before execute.
        base._client.pipeline.assert_not_called()

    def test_successful_promotion_pipelines_delete_and_invalidates(
        self, real_transactions, mock_caching
    ):
        tx, base = real_transactions
        pattern = _make_staged_pattern("pat_ok2", confidence=0.95)
        base._client.get.return_value = json.dumps(_as_dict(pattern))
        pipe = MagicMock()
        base._client.pipeline.return_value = pipe

        ok, returned, msg = tx.atomic_promote_pattern(
            "pat_ok2", _validator_creds(), min_confidence=0.5
        )

        assert ok is True
        assert isinstance(returned, StagedPattern)
        assert returned.pattern_id == "pat_ok2"
        assert msg == "Pattern promoted successfully"
        # Pipeline used with transaction=True for atomicity.
        base._client.pipeline.assert_called_once_with(True)
        key = f"{TransactionManager.PREFIX_STAGED}pat_ok2"
        pipe.delete.assert_called_once_with(key)
        pipe.execute.assert_called_once()
        mock_caching.invalidate.assert_called_once_with(key)

    def test_watch_error_returns_race_message(self, real_transactions):
        """A `redis.WatchError` during the optimistic-lock window
        is caught and surfaced as a structured failure."""
        tx, base = real_transactions
        base._client.get.side_effect = redis.WatchError("modified")

        ok, pattern, msg = tx.atomic_promote_pattern("pat_x", _validator_creds())

        assert ok is False
        assert pattern is None
        assert "modified by another process" in msg

    def test_unwatch_exception_in_finally_is_swallowed(self, real_transactions):
        """The best-effort `unwatch()` in `finally` must not propagate.

        In the success path the only `unwatch()` call lives inside
        the `finally` block (the early-return branches at lines
        166/172 are skipped because the pattern is present and
        meets the threshold). The exception there must be caught.
        """
        tx, base = real_transactions
        base._client.get.return_value = json.dumps(_as_dict(_make_staged_pattern()))
        base._client.pipeline.return_value = MagicMock()
        base._client.unwatch.side_effect = Exception("redis down")

        # Should not raise — the finally's broad-except swallows it.
        ok, _, _ = tx.atomic_promote_pattern("pat_123", _validator_creds())
        assert ok is True
        base._client.unwatch.assert_called_once()


def _as_dict(pattern: StagedPattern) -> dict:
    """Convert StagedPattern to dict for json.dumps round-trip.

    `StagedPattern.from_dict` consumes the same shape. Datetimes
    flatten to isoformat to match the wire format.
    """
    return {
        "pattern_id": pattern.pattern_id,
        "agent_id": pattern.agent_id,
        "pattern_type": pattern.pattern_type,
        "name": pattern.name,
        "description": pattern.description,
        "code": pattern.code,
        "context": pattern.context,
        "confidence": pattern.confidence,
        "staged_at": pattern.staged_at.isoformat(),
        "interests": pattern.interests,
    }
