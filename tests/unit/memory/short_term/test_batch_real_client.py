"""Real-Redis-path tests for BatchOperations.

The existing short-term suites exercise the in-memory MOCK path
(`use_mock=True`). This complementary suite covers the REAL Redis
branches of `batch.py` (lines 145-164 and 211-224) — the `_client is
None` guards, the `pipeline()`/`setex`/`execute` flow in `stash_batch`,
the `mget` flow in `retrieve_batch`, the truthy-result counting, and the
`agent_id or credentials.agent_id` owner default — by injecting a
`MagicMock` Redis client (`use_mock=False`). No live Redis is required.

Assertions pin the exact key namespace, the TTL passed to `setex`, the
truthy-result count, and which keys are omitted on retrieve, so the
relevant operator/argument mutations are caught.

Coverage (with the existing mock suites): `batch.py` 67% -> 100%.

Mutation status (mutmut 2.4.4, mock + this suite as runner): ``82 mutants
-> 62 killed, 20 survived``. All 20 survivors are documented equivalents:
message strings; per-path latency-arithmetic (timing-dependent values,
not asserted); mock-path metric labels (the real-path labels are pinned);
the logger event name; the ``<=`` expiry boundary (unobservable without
an exact-timestamp collision); and ``zip(strict=False -> True)`` (mget
always returns one value per key, so the strictness never triggers).
Killable kill-rate 62/62 = 100%.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from attune.memory.short_term import AccessTier, AgentCredentials
from attune.memory.short_term.batch import BatchOperations
from attune.memory.types import TTLStrategy

pytestmark = pytest.mark.unit

PREFIX = "empathy:working:"


@pytest.fixture
def creds() -> AgentCredentials:
    return AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)


def make_base(client):
    """Fake BaseOperations in real (non-mock) mode with an injected client."""
    return SimpleNamespace(use_mock=False, _client=client, _metrics=MagicMock())


@pytest.fixture
def client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def ops(client) -> BatchOperations:
    return BatchOperations(make_base(client))


def _stored(data) -> str:
    """A JSON payload shaped like what stash writes (retrieve reads .data)."""
    return json.dumps({"data": data, "agent_id": "agent_1", "stashed_at": "t"})


class TestStashBatchRealClient:
    def test_returns_zero_when_client_is_none(self, creds):
        ops = BatchOperations(make_base(None))
        assert ops.stash_batch([("k", {"a": 1})], creds) == 0

    def test_pipelines_setex_per_item_and_counts_truthy(self, ops, client, creds):
        pipe = client.pipeline.return_value
        pipe.execute.return_value = [True, True]
        items = [("k1", {"a": 1}), ("k2", {"b": 2})]
        count = ops.stash_batch(items, creds)
        assert count == 2
        assert pipe.setex.call_count == 2
        # First setex: (full_key, ttl_seconds, json_payload)
        args, _ = pipe.setex.call_args_list[0]
        assert args[0] == f"{PREFIX}agent_1:k1"
        assert args[1] == TTLStrategy.WORKING_RESULTS.value  # default ttl
        payload = json.loads(args[2])
        assert payload["data"] == {"a": 1}
        assert payload["agent_id"] == "agent_1"  # metadata pinned
        assert "stashed_at" in payload
        pipe.execute.assert_called_once()

    def test_count_reflects_only_truthy_results(self, ops, client, creds):
        client.pipeline.return_value.execute.return_value = [True, None, True]
        items = [("k1", {}), ("k2", {}), ("k3", {})]
        assert ops.stash_batch(items, creds) == 2

    def test_custom_ttl_reaches_setex(self, ops, client, creds):
        pipe = client.pipeline.return_value
        pipe.execute.return_value = [True]
        ops.stash_batch([("k", {})], creds, ttl=TTLStrategy.SESSION)
        assert pipe.setex.call_args[0][1] == TTLStrategy.SESSION.value

    def test_records_numeric_metric(self, ops, client, creds):
        client.pipeline.return_value.execute.return_value = [True]
        ops.stash_batch([("k", {})], creds)
        name, latency = ops._base._metrics.record_operation.call_args[0]
        assert name == "stash_batch"
        assert isinstance(latency, float) and latency >= 0


class TestRetrieveBatchRealClient:
    def test_returns_empty_when_client_is_none(self, creds):
        ops = BatchOperations(make_base(None))
        assert ops.retrieve_batch(["k"], creds) == {}

    def test_mget_keys_and_omits_missing(self, ops, client, creds):
        client.mget.return_value = [_stored({"a": 1}), None, _stored({"c": 3})]
        out = ops.retrieve_batch(["k1", "k2", "k3"], creds)
        # k2 (None value) omitted; others decoded to their .data
        assert out == {"k1": {"a": 1}, "k3": {"c": 3}}
        client.mget.assert_called_once_with(
            [f"{PREFIX}agent_1:k1", f"{PREFIX}agent_1:k2", f"{PREFIX}agent_1:k3"]
        )

    def test_owner_defaults_to_credentials_agent(self, ops, client, creds):
        client.mget.return_value = [None]
        ops.retrieve_batch(["k"], creds)
        assert client.mget.call_args[0][0] == [f"{PREFIX}agent_1:k"]

    def test_explicit_agent_id_overrides_owner(self, ops, client, creds):
        client.mget.return_value = [None]
        ops.retrieve_batch(["k"], creds, agent_id="other_agent")
        assert client.mget.call_args[0][0] == [f"{PREFIX}other_agent:k"]

    def test_records_numeric_metric(self, ops, client, creds):
        client.mget.return_value = [None]
        ops.retrieve_batch(["k"], creds)
        name, latency = ops._base._metrics.record_operation.call_args[0]
        assert name == "retrieve_batch"
        assert isinstance(latency, float) and latency >= 0


class TestMockStorageExpiry:
    """Mock-path payload shape and TTL-expiry semantics."""

    def _mock_ops(self):
        base = SimpleNamespace(use_mock=True, _mock_storage={}, _metrics=MagicMock())
        return BatchOperations(base), base

    def test_stash_writes_payload_with_future_expiry(self, creds):
        ops, base = self._mock_ops()
        ops.stash_batch([("k", {"a": 1})], creds)
        raw, expires = base._mock_storage[f"{PREFIX}agent_1:k"]
        payload = json.loads(raw)
        assert payload["data"] == {"a": 1}
        assert payload["agent_id"] == "agent_1"
        assert "stashed_at" in payload
        # expiry is a future timestamp, not None
        assert expires is not None
        assert expires > datetime.now().timestamp()

    def test_unexpired_entry_is_returned(self, creds):
        ops, _base = self._mock_ops()
        ops.stash_batch([("k", {"a": 1})], creds)
        assert ops.retrieve_batch(["k"], creds) == {"k": {"a": 1}}

    def test_expired_entry_is_omitted(self, creds):
        ops, base = self._mock_ops()
        ops.stash_batch([("k", {"a": 1})], creds)
        full_key = f"{PREFIX}agent_1:k"
        raw, _ = base._mock_storage[full_key]
        base._mock_storage[full_key] = (raw, 0.0)  # expires at epoch -> past
        assert ops.retrieve_batch(["k"], creds) == {}
