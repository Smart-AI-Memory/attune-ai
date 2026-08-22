"""Scan-then-fetch listings must cost ONE round trip, not N.

Every listing below scans a key pattern and then reads the records. The
regression this pins is a *round-trip count*: a refactor that swaps the
batched read back for a per-key ``get()`` loop keeps every functional
assertion green while restoring the N+1 pattern, so the transport itself
is asserted here.

The fake client counts calls and REFUSES ``get`` outright inside the
listing paths, so the N+1 shape fails loudly rather than silently.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from attune.telemetry._redis_batch import decode_json_object, mget_json
from attune.telemetry.agent_coordination import CoordinationSignals
from attune.telemetry.agent_tracking import HeartbeatCoordinator
from attune.telemetry.approval_gates import ApprovalGate


class CountingClient:
    """Redis stand-in that counts round trips and bans per-key get()."""

    def __init__(self, records: dict[str, object], *, allow_get: bool = False):
        # ``records`` values are pre-encoded payloads (bytes/str) or None.
        self.records = records
        self.allow_get = allow_get
        self.mget_calls: list[list[str]] = []
        self.get_calls: list[str] = []
        self.setex_calls: list[tuple[str, int, str]] = []

    def scan_iter(self, match: str = "*", count: int = 100):
        # Returned as bytes, exactly as redis-py does by default.
        yield from (key.encode() for key in self.records)

    def mget(self, keys):
        keys = list(keys)
        self.mget_calls.append(keys)
        return [self.records.get(key) for key in keys]

    def get(self, key):
        self.get_calls.append(key)
        if not self.allow_get:
            raise AssertionError(
                f"per-key get({key!r}) in a listing path — the batched read regressed to N+1"
            )
        return self.records.get(key)

    def setex(self, key, ttl, value):
        self.setex_calls.append((key, ttl, value))
        return True

    def delete(self, key):
        self.records.pop(key, None)
        return 1


class FakeMemory:
    def __init__(self, client):
        self._client = client


def _approval(request_id: str, *, status: str = "pending", age_seconds: float = 0.0) -> bytes:
    ts = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    return json.dumps(
        {
            "request_id": request_id,
            "approval_type": "deploy",
            "agent_id": "agent-1",
            "context": {},
            "timestamp": ts.isoformat(),
            "timeout_seconds": 300.0,
            "status": status,
        }
    ).encode()


def _signal(signal_id: str, *, signal_type: str = "ready") -> bytes:
    return json.dumps(
        {
            "signal_id": signal_id,
            "signal_type": signal_type,
            "source_agent": "agent-2",
            "target_agent": "agent-1",
            "payload": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": 60,
        }
    ).encode()


def _heartbeat(agent_id: str) -> bytes:
    return json.dumps(
        {
            "agent_id": agent_id,
            "status": "running",
            "progress": 0.5,
            "current_task": "work",
            "last_beat": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        }
    ).encode()


class TestApprovalGateBatching:
    def test_pending_approvals_uses_one_mget_for_many_keys(self):
        records = {f"approval_request:approval_{i}": _approval(f"approval_{i}") for i in range(5)}
        client = CountingClient(records)
        gate = ApprovalGate(memory=FakeMemory(client))

        pending = gate.get_pending_approvals()

        assert len(pending) == 5
        assert len(client.mget_calls) == 1
        assert client.get_calls == []

    def test_pending_approvals_skips_malformed_record_only(self):
        records = {
            "approval_request:good_1": _approval("good_1"),
            "approval_request:not_json": b"{not json",
            "approval_request:not_an_object": b"[1, 2, 3]",
            "approval_request:missing_field": json.dumps({"approval_type": "deploy"}).encode(),
            "approval_request:bad_timestamp": json.dumps(
                {
                    "request_id": "bad_ts",
                    "approval_type": "deploy",
                    "agent_id": "agent-1",
                    "timestamp": "not-a-timestamp",
                }
            ).encode(),
            "approval_request:absent": None,
            "approval_request:good_2": _approval("good_2"),
        }
        client = CountingClient(records)
        gate = ApprovalGate(memory=FakeMemory(client))

        pending = gate.get_pending_approvals()

        assert [r.request_id for r in pending] == ["good_1", "good_2"]
        assert len(client.mget_calls) == 1

    def test_clear_expired_requests_uses_one_mget(self):
        records = {
            "approval_request:fresh": _approval("fresh"),
            "approval_request:stale": _approval("stale", age_seconds=1000),
        }
        client = CountingClient(records)
        gate = ApprovalGate(memory=FakeMemory(client))

        assert gate.clear_expired_requests() == 1
        assert len(client.mget_calls) == 1
        assert client.get_calls == []
        assert [call[0] for call in client.setex_calls] == ["approval_request:stale"]

    def test_clear_expired_requests_skips_malformed_record_only(self):
        records = {
            "approval_request:broken": b"{not json",
            "approval_request:stale": _approval("stale", age_seconds=1000),
        }
        client = CountingClient(records)
        gate = ApprovalGate(memory=FakeMemory(client))

        assert gate.clear_expired_requests() == 1


class TestCoordinationSignalBatching:
    def test_pending_signals_uses_one_mget_per_scanned_pattern(self):
        records = {f"signal:agent-1:ready:sig{i}": _signal(f"sig{i}") for i in range(4)}
        client = CountingClient(records)
        signals = CoordinationSignals(memory=FakeMemory(client), agent_id="agent-1")

        pending = signals.get_pending_signals()

        # Two scanned patterns (targeted + broadcast) => at most one MGET each.
        assert len(pending) == 8  # same fake keys served for both patterns
        assert len(client.mget_calls) == 2
        assert client.get_calls == []

    def test_check_signal_uses_one_mget(self):
        records = {"signal:agent-1:ready:sig1": _signal("sig1")}
        client = CountingClient(records)
        signals = CoordinationSignals(memory=FakeMemory(client), agent_id="agent-1")

        found = signals.check_signal("ready", consume=False)

        assert found is not None
        assert found.signal_id == "sig1"
        assert len(client.mget_calls) == 1
        assert client.get_calls == []

    def test_pending_signals_skips_malformed_record_only(self):
        records = {
            "signal:agent-1:ready:good": _signal("good"),
            "signal:agent-1:ready:broken": b"{not json",
            "signal:agent-1:ready:incomplete": json.dumps({"signal_id": "x"}).encode(),
        }
        client = CountingClient(records)
        signals = CoordinationSignals(memory=FakeMemory(client), agent_id="agent-1")

        pending = signals.get_pending_signals()

        assert {s.signal_id for s in pending} == {"good"}


class TestHeartbeatBatching:
    def test_active_agents_uses_one_mget_for_many_keys(self):
        records = {f"empathy:heartbeat:agent-{i}": _heartbeat(f"agent-{i}") for i in range(6)}
        client = CountingClient(records)
        coordinator = HeartbeatCoordinator(memory=FakeMemory(client))

        active = coordinator.get_active_agents()

        assert len(active) == 6
        assert len(client.mget_calls) == 1
        assert client.get_calls == []

    def test_active_agents_skips_malformed_record_only(self):
        records = {
            "empathy:heartbeat:good": _heartbeat("good"),
            "empathy:heartbeat:broken": b"{not json",
            "empathy:heartbeat:incomplete": json.dumps({"agent_id": "x"}).encode(),
            "empathy:heartbeat:absent": None,
        }
        client = CountingClient(records)
        coordinator = HeartbeatCoordinator(memory=FakeMemory(client))

        active = coordinator.get_active_agents()

        assert [h.agent_id for h in active] == ["good"]


class TestMgetJsonHelper:
    def test_decodes_bytes_keys_and_values_in_order(self):
        client = CountingClient({"a": b'{"n": 1}', "b": '{"n": 2}'})

        assert mget_json(client, [b"a", b"b"]) == [("a", {"n": 1}), ("b", {"n": 2})]

    def test_empty_keys_makes_no_round_trip(self):
        client = CountingClient({})

        assert mget_json(client, []) == []
        assert client.mget_calls == []

    def test_chunks_large_key_sets(self):
        from attune.telemetry import _redis_batch

        keys = [f"k{i}" for i in range(_redis_batch._MGET_CHUNK + 1)]
        client = CountingClient({k: b'{"n": 1}' for k in keys})

        records = mget_json(client, keys)

        assert len(records) == len(keys)
        assert len(client.mget_calls) == 2

    def test_mget_errors_are_not_swallowed(self):
        class BrokenClient(CountingClient):
            def mget(self, keys):
                raise ConnectionError("redis down")

        with pytest.raises(ConnectionError):
            mget_json(BrokenClient({}), ["a"])

    @pytest.mark.parametrize(
        "raw",
        [None, b"", "", b"{not json", b"[1,2]", b'"a string"', b"\xff\xfe", 12345],
    )
    def test_decode_json_object_is_total(self, raw):
        assert decode_json_object(raw) is None


class TestListingsDegradeWithoutRedis:
    def test_listings_return_empty_when_mget_fails(self):
        class BrokenClient(CountingClient):
            def mget(self, keys):
                raise ConnectionError("redis down")

        records = {"approval_request:a": _approval("a")}
        gate = ApprovalGate(memory=FakeMemory(BrokenClient(records)))
        assert gate.get_pending_approvals() == []
        assert gate.clear_expired_requests() == 0

        signals = CoordinationSignals(
            memory=FakeMemory(BrokenClient({"signal:agent-1:ready:s": _signal("s")})),
            agent_id="agent-1",
        )
        assert signals.get_pending_signals() == []
        assert signals.check_signal("ready") is None

        coordinator = HeartbeatCoordinator(
            memory=FakeMemory(BrokenClient({"empathy:heartbeat:a": _heartbeat("a")}))
        )
        assert coordinator.get_active_agents() == []
