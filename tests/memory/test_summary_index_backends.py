"""Backend-branch + edge-case tests for ConversationSummaryIndex.

Complements tests/memory/test_summary_index.py (which exercises the
mock-backed happy path) by covering the parts that suite leaves at 82%:

- The low-level Redis helpers in all three modes — mock, real-client,
  and the ``_client is None`` degraded path — including the
  ``if result else <empty>`` guards on real-client returns.
- ``_mock_get`` TTL expiration.
- update_summary 'answered' clearing, get_context JSON-decode guard,
  recall_decisions time-range / empty-summary / bad-date branches, and
  clear_session's non-mock topic-index cleanup.

Mode switching: a mock RedisShortTermMemory is built, then its
``use_mock`` / ``_client`` attributes are flipped — the helpers read
only those two fields, so this exercises the real branches with zero
network and no real Redis.
"""

import json
import time

import pytest

from attune.memory import ConversationSummaryIndex, RedisShortTermMemory

# ===========================================================================
# Fakes / fixtures
# ===========================================================================


class FakeRedisClient:
    """Minimal Redis client stub with configurable return values.

    Records srem calls so clear_session's non-mock branch is observable.
    """

    def __init__(self, **returns):
        self._returns = returns
        self.srem_calls: list[tuple] = []

    def hset(self, key, mapping=None):
        return self._returns.get("hset", 1)

    def hget(self, key, field):
        return self._returns.get("hget", "value")

    def hgetall(self, key):
        return self._returns.get("hgetall", {"field": "value"})

    def zadd(self, key, mapping):
        return self._returns.get("zadd", 1)

    def zrevrange(self, key, start, stop):
        return self._returns.get("zrevrange", ["member"])

    def sadd(self, key, *members):
        return self._returns.get("sadd", len(members))

    def smembers(self, key):
        return self._returns.get("smembers", {"member"})

    def expire(self, key, seconds):
        return self._returns.get("expire", True)

    def srem(self, key, member):
        self.srem_calls.append((key, member))
        return 1


class FakeMemory:
    """Stand-in for the memory object in non-mock mode.

    ConversationSummaryIndex's helpers only read these four attributes;
    RedisShortTermMemory exposes use_mock/_client as read-only
    properties, so a purpose-built fake is the clean way to drive the
    real (non-mock) helper branches without a live Redis.
    """

    def __init__(self, client):
        self.use_mock = False
        self._client = client
        self._mock_storage: dict = {}
        self.deleted: list[str] = []

    def _delete(self, key):
        self.deleted.append(key)


@pytest.fixture
def mock_index():
    """ConversationSummaryIndex over a mock RedisShortTermMemory."""
    return ConversationSummaryIndex(RedisShortTermMemory(use_mock=True))


def _index_with_client(client):
    """Build an index in non-mock mode backed by the given client (or None)."""
    return ConversationSummaryIndex(FakeMemory(client))


# ===========================================================================
# Low-level helpers — _client is None (degraded) branch
# ===========================================================================


def test_helpers_return_empty_defaults_when_client_none():
    """With no client, each helper returns its documented empty value."""
    idx = _index_with_client(None)
    assert idx._hset("k", {"a": "b"}) is False
    assert idx._hget("k", "a") is None
    assert idx._hgetall("k") == {}
    assert idx._zadd("k", 1.0, "m") is False
    assert idx._zrevrange("k", 0, 5) == []
    assert idx._sadd("k", "m") == 0
    assert idx._smembers("k") == set()
    assert idx._expire("k", 60) is False


# ===========================================================================
# Low-level helpers — real-client branch (truthy returns)
# ===========================================================================


def test_helpers_delegate_to_client_on_truthy_returns():
    """Helpers forward to the client and coerce truthy results."""
    idx = _index_with_client(FakeRedisClient())
    assert idx._hset("k", {"a": "b"}) is True
    assert idx._hget("k", "a") == "value"
    assert idx._hgetall("k") == {"field": "value"}
    assert idx._zadd("k", 1.0, "m") is True
    assert idx._zrevrange("k", 0, 5) == ["member"]
    assert idx._sadd("k", "m") == 1
    assert idx._smembers("k") == {"member"}
    assert idx._expire("k", 60) is True


def test_helpers_return_empty_on_falsy_client_returns():
    """The `if result else <empty>` guards map falsy client returns."""
    idx = _index_with_client(FakeRedisClient(hget=None, hgetall={}, zrevrange=[], smembers=set()))
    assert idx._hget("k", "a") is None
    assert idx._hgetall("k") == {}
    assert idx._zrevrange("k", 0, 5) == []
    assert idx._smembers("k") == set()


# ===========================================================================
# Low-level helpers — mock branch coverage (read-side helpers)
# ===========================================================================


def test_mock_read_helpers_round_trip(mock_index):
    """Mock-mode read helpers reflect what the write helpers stored."""
    mock_index._hset("h", {"field": "v"})
    assert mock_index._hget("h", "field") == "v"
    assert mock_index._hgetall("h") == {"field": "v"}

    mock_index._sadd("s", "m1", "m1", "m2")  # duplicate ignored
    assert mock_index._smembers("s") == {"m1", "m2"}

    mock_index._zadd("z", 1.0, "low")
    mock_index._zadd("z", 2.0, "high")
    assert mock_index._zrevrange("z", 0, 1) == ["high", "low"]  # score-desc

    assert mock_index._expire("h", 99) is True
    assert mock_index._expire("missing-key", 99) is False


def test_mock_read_helpers_return_empty_on_missing_key(mock_index):
    """Mock-mode reads of an absent key return the empty default."""
    assert mock_index._hget("absent", "field") is None
    assert mock_index._smembers("absent") == set()


def test_mock_get_evicts_expired_entry(mock_index):
    """_mock_get deletes and reports-missing an entry past its TTL."""
    mem = mock_index._memory
    mem._mock_storage["expired"] = ({"field": "v"}, time.time() - 1)
    assert mock_index._hgetall("expired") == {}
    assert "expired" not in mem._mock_storage


# ===========================================================================
# update_summary — the 'answered' clearing branch
# ===========================================================================


def test_update_summary_answered_clears_matching_question(mock_index):
    """An 'answered' event removes the matching open question."""
    sid = "s1"
    mock_index.update_summary(sid, {"type": "question", "content": "use JWT?"})
    ctx = mock_index.get_context_for_agent(sid)
    assert any("jwt" in q.lower() for q in ctx.open_questions)

    mock_index.update_summary(sid, {"type": "answered", "content": "JWT"})
    ctx = mock_index.get_context_for_agent(sid)
    assert not any("jwt" in q.lower() for q in ctx.open_questions)


# ===========================================================================
# get_context_for_agent — malformed timeline entry guard
# ===========================================================================


def test_get_context_skips_corrupt_timeline_entry(mock_index):
    """A non-JSON timeline entry is skipped, not raised."""
    sid = "s1"
    mock_index.update_summary(sid, {"type": "started", "content": "real work"})
    # Inject a corrupt timeline entry directly into the sorted set.
    timeline_key = f"{mock_index.PREFIX_TIMELINE}{sid}"
    mock_index._zadd(timeline_key, time.time(), "{not json")

    ctx = mock_index.get_context_for_agent(sid)
    # The valid entry survives; the corrupt one is dropped.
    assert all(isinstance(e, dict) for e in ctx.recent_events)


# ===========================================================================
# recall_decisions — continue branches
# ===========================================================================


def test_recall_decisions_skips_session_without_summary(mock_index):
    """A topic-indexed session with no summary is skipped (no crash)."""
    topic_key = f"{mock_index.PREFIX_TOPIC}auth"
    mock_index._sadd(topic_key, "ghost-session")  # indexed but no summary
    assert mock_index.recall_decisions("auth") == []


def test_recall_decisions_excludes_out_of_time_range(mock_index):
    """A decision older than days_back is excluded."""
    sid = "old"
    summary_key = f"{mock_index.PREFIX_SUMMARY}{sid}"
    mock_index._sadd(f"{mock_index.PREFIX_TOPIC}auth", sid)
    mock_index._hset(
        summary_key,
        {
            "decisions": json.dumps(["chose auth strategy"]),
            "updated_at": "2000-01-01T00:00:00",  # ancient
            "topics": json.dumps(["auth"]),
        },
    )
    assert mock_index.recall_decisions("auth", days_back=7) == []


def test_recall_decisions_tolerates_bad_updated_at(mock_index):
    """A non-ISO updated_at is tolerated; the decision still surfaces."""
    sid = "weird"
    summary_key = f"{mock_index.PREFIX_SUMMARY}{sid}"
    mock_index._sadd(f"{mock_index.PREFIX_TOPIC}auth", sid)
    mock_index._hset(
        summary_key,
        {
            "decisions": json.dumps(["auth decision here"]),
            "updated_at": "not-a-real-date",
            "topics": json.dumps(["auth"]),
        },
    )
    results = mock_index.recall_decisions("auth")
    assert len(results) == 1
    assert results[0]["session"] == sid


# ===========================================================================
# clear_session — non-mock topic-index cleanup branch
# ===========================================================================


def test_clear_session_non_mock_calls_srem():
    """In non-mock mode, clear_session srem's the session from topic sets."""
    client = FakeRedisClient(hgetall={"topics": json.dumps(["auth", "api"])})
    idx = _index_with_client(client)

    assert idx.clear_session("s1") is True
    # One srem per topic, each removing the session.
    assert sorted(client.srem_calls) == [
        (f"{idx.PREFIX_TOPIC}api", "s1"),
        (f"{idx.PREFIX_TOPIC}auth", "s1"),
    ]
    # Summary + timeline both deleted.
    assert len(idx._memory.deleted) == 2
