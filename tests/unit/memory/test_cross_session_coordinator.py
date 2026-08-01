"""Tests for CrossSessionCoordinator.

Covers degraded mode (mock Redis), agent_id generation, event handler
registration, heartbeat lifecycle, conflict resolution, distributed
locking, and session discovery — all without a real Redis connection.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from attune.memory.cross_session.coordinator import CrossSessionCoordinator
from attune.memory.cross_session.models import (
    CHANNEL_SESSIONS,
    KEY_ACTIVE_AGENTS,
    STALE_THRESHOLD_SECONDS,
    ConflictStrategy,
    SessionInfo,
    SessionType,
)
from attune.memory.short_term import AccessTier, RedisShortTermMemory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_memory() -> RedisShortTermMemory:
    """Return a RedisShortTermMemory wired to a MagicMock Redis client.

    Sets use_mock=True to avoid real Redis, then replaces the internal
    _client attribute so coordinator code that checks ``client is None``
    will see a working mock instead of None.
    """
    memory = RedisShortTermMemory(use_mock=True)
    mock_client = MagicMock()
    mock_client.setnx.return_value = True
    mock_client.get.return_value = None
    mock_client.hgetall.return_value = {}
    mock_client.hget.return_value = None
    # Inject mock client into the internal _base attribute
    memory._base._client = mock_client
    return memory


def _make_session_info(
    agent_id: str = "other_agent",
    access_tier: AccessTier = AccessTier.CONTRIBUTOR,
    offset_seconds: int = 0,
) -> SessionInfo:
    """Build a fresh (non-stale) SessionInfo for tests."""
    now = datetime.now() - timedelta(seconds=offset_seconds)
    return SessionInfo(
        agent_id=agent_id,
        session_type=SessionType.CLAUDE,
        access_tier=access_tier,
        capabilities=["stash", "retrieve"],
        started_at=now,
        last_heartbeat=now,
    )


# ---------------------------------------------------------------------------
# Init / degraded mode
# ---------------------------------------------------------------------------


class TestCrossSessionCoordinatorInit:
    """Initialization and degraded-mode behaviour."""

    def test_init_mock_mode_sets_degraded(self):
        """Coordinator enters degraded mode when memory.use_mock is True."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord._degraded is True

    def test_init_generates_agent_id(self):
        """agent_id is set to a non-empty string during init."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.agent_id
        assert isinstance(coord.agent_id, str)

    def test_init_agent_id_includes_session_type_prefix(self):
        """agent_id begins with the session type prefix."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(
            memory=memory,
            session_type=SessionType.WORKER,
            auto_announce=False,
        )
        assert coord.agent_id.startswith("worker_")

    def test_init_unique_agent_ids(self):
        """Each coordinator instance receives a distinct agent_id."""
        memory = RedisShortTermMemory(use_mock=True)
        ids = [
            CrossSessionCoordinator(memory=memory, auto_announce=False).agent_id for _ in range(5)
        ]
        assert len(set(ids)) == 5

    def test_init_credentials_match_access_tier(self):
        """credentials.tier matches the supplied access_tier argument."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(
            memory=memory,
            access_tier=AccessTier.STEWARD,
            auto_announce=False,
        )
        assert coord.credentials.tier == AccessTier.STEWARD

    def test_init_default_capabilities(self):
        """Default capabilities list is non-empty."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord._capabilities

    def test_init_custom_capabilities(self):
        """Supplied capabilities list is stored."""
        memory = RedisShortTermMemory(use_mock=True)
        caps = ["read", "write"]
        coord = CrossSessionCoordinator(
            memory=memory,
            capabilities=caps,
            auto_announce=False,
        )
        assert coord._capabilities == caps

    def test_session_info_property_returns_session_info(self):
        """session_info returns a SessionInfo instance."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        info = coord.session_info
        assert isinstance(info, SessionInfo)
        assert info.agent_id == coord.agent_id


# ---------------------------------------------------------------------------
# Degraded mode — announce / depart / session discovery / locking
# ---------------------------------------------------------------------------


class TestCrossSessionCoordinatorDegradedMode:
    """Degraded-mode operations when Redis client is None."""

    def test_announce_degraded_no_op(self):
        """announce() is a no-op when the Redis client is None."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        # Should not raise; memory._client is None in mock mode
        coord.announce()

    def test_get_active_sessions_degraded_returns_empty_list(self):
        """get_active_sessions() returns [] when client is None."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.get_active_sessions() == []

    def test_get_session_degraded_returns_none(self):
        """get_session() returns None when client is None."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.get_session("any_agent") is None

    def test_acquire_lock_degraded_returns_false(self):
        """acquire_lock() returns False when client is None."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.acquire_lock("some_resource") is False

    def test_release_lock_degraded_returns_false(self):
        """release_lock() returns False when client is None."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.release_lock("some_resource") is False

    def test_check_lock_degraded_returns_none(self):
        """check_lock() returns None when client is None."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.check_lock("some_resource") is None

    def test_depart_degraded_no_op(self):
        """depart() is a no-op when the Redis client is None."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        coord.depart()  # Should not raise

    def test_close_degraded_no_op(self):
        """close() calls depart() without raising in degraded mode."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        coord.close()  # Should not raise


# ---------------------------------------------------------------------------
# Heartbeat lifecycle
# ---------------------------------------------------------------------------


class TestCrossSessionCoordinatorHeartbeat:
    """Heartbeat thread management."""

    def test_start_heartbeat_creates_thread(self):
        """start_heartbeat() sets _heartbeat_thread to a Thread instance."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        coord.start_heartbeat()
        try:
            assert isinstance(coord._heartbeat_thread, threading.Thread)
        finally:
            coord.stop_heartbeat()

    def test_start_heartbeat_idempotent(self):
        """Calling start_heartbeat() twice does not create a second thread."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        coord.start_heartbeat()
        thread_first = coord._heartbeat_thread
        coord.start_heartbeat()
        assert coord._heartbeat_thread is thread_first
        coord.stop_heartbeat()

    def test_stop_heartbeat_clears_thread(self):
        """stop_heartbeat() sets _heartbeat_thread back to None."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        coord.start_heartbeat()
        coord.stop_heartbeat()
        assert coord._heartbeat_thread is None

    def test_stop_heartbeat_safe_when_not_started(self):
        """stop_heartbeat() does not raise when no thread is running."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        coord.stop_heartbeat()  # Should not raise

    def test_close_stops_heartbeat(self):
        """close() stops the heartbeat thread (via depart)."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        coord.start_heartbeat()
        coord.close()
        assert coord._heartbeat_thread is None

    def test_default_construction_heartbeat_is_stopped_by_close(self):
        """Default auto_announce spawns a heartbeat thread that close() stops.

        Regression guard for the xdist end-of-session finalize deadlock
        (docs/specs/ci-runner-hang/): the default ``auto_announce=True``
        path starts a daemon ``heartbeat-<agent_id>`` thread, and a test
        or caller that never closes the coordinator leaks it into the
        worker process. This pins that close() terminates the OS thread,
        not merely the attribute.
        """
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory)  # auto_announce=True
        thread_name = f"heartbeat-{coord._agent_id}"
        try:
            assert any(t.name == thread_name for t in threading.enumerate())
        finally:
            coord.close()
        assert coord._heartbeat_thread is None
        assert not any(t.is_alive() and t.name == thread_name for t in threading.enumerate())


# ---------------------------------------------------------------------------
# Event handler registration
# ---------------------------------------------------------------------------


class TestCrossSessionCoordinatorEventHandlers:
    """on_session_joined / on_session_left handler registration."""

    def test_on_session_joined_registers_handler(self):
        """Registered joined-handler appears in the internal list."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        handler = MagicMock()
        coord.on_session_joined(handler)
        assert handler in coord._on_session_joined

    def test_on_session_left_registers_handler(self):
        """Registered left-handler appears in the internal list."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        handler = MagicMock()
        coord.on_session_left(handler)
        assert handler in coord._on_session_left

    def test_multiple_joined_handlers_registered(self):
        """Multiple handlers can be registered for session-joined."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        h1, h2 = MagicMock(), MagicMock()
        coord.on_session_joined(h1)
        coord.on_session_joined(h2)
        assert h1 in coord._on_session_joined
        assert h2 in coord._on_session_joined

    def test_multiple_left_handlers_registered(self):
        """Multiple handlers can be registered for session-left."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        h1, h2 = MagicMock(), MagicMock()
        coord.on_session_left(h1)
        coord.on_session_left(h2)
        assert h1 in coord._on_session_left
        assert h2 in coord._on_session_left


# ---------------------------------------------------------------------------
# Conflict resolution
# ---------------------------------------------------------------------------


class TestCrossSessionCoordinatorConflictResolution:
    """Conflict resolution strategies exercised with a mocked Redis client."""

    def test_resolve_conflict_priority_higher_tier_wins(self):
        """PRIORITY_BASED: higher access tier wins the conflict."""
        memory = _mock_memory()
        other = _make_session_info(agent_id="low_agent", access_tier=AccessTier.OBSERVER)
        memory._base._client.hget.return_value = json.dumps(other.to_dict()).encode()

        coord = CrossSessionCoordinator(
            memory=memory,
            access_tier=AccessTier.STEWARD,
            auto_announce=False,
        )
        result = coord.resolve_conflict(
            resource_key="res",
            other_agent_id="low_agent",
            strategy=ConflictStrategy.PRIORITY_BASED,
        )
        assert result.winner_agent_id == coord.agent_id
        assert result.loser_agent_id == "low_agent"
        assert "Higher tier" in result.reason

    def test_resolve_conflict_priority_lower_tier_loses(self):
        """PRIORITY_BASED: lower access tier loses the conflict."""
        memory = _mock_memory()
        other = _make_session_info(agent_id="high_agent", access_tier=AccessTier.STEWARD)
        memory._base._client.hget.return_value = json.dumps(other.to_dict()).encode()

        coord = CrossSessionCoordinator(
            memory=memory,
            access_tier=AccessTier.OBSERVER,
            auto_announce=False,
        )
        result = coord.resolve_conflict(
            resource_key="res",
            other_agent_id="high_agent",
            strategy=ConflictStrategy.PRIORITY_BASED,
        )
        assert result.winner_agent_id == "high_agent"
        assert result.loser_agent_id == coord.agent_id

    def test_resolve_conflict_first_write_wins(self):
        """FIRST_WRITE_WINS: current writer wins when lock is available."""
        memory = _mock_memory()
        memory._base._client.hget.return_value = None
        memory._base._client.setnx.return_value = True  # lock available

        coord = CrossSessionCoordinator(
            memory=memory,
            access_tier=AccessTier.CONTRIBUTOR,
            auto_announce=False,
        )
        result = coord.resolve_conflict(
            resource_key="res",
            other_agent_id="other_agent",
            strategy=ConflictStrategy.FIRST_WRITE_WINS,
        )
        assert result.strategy_used == ConflictStrategy.FIRST_WRITE_WINS
        assert result.winner_agent_id == coord.agent_id

    def test_resolve_conflict_last_write_wins(self):
        """LAST_WRITE_WINS: current writer always wins."""
        memory = _mock_memory()
        memory._base._client.hget.return_value = None

        coord = CrossSessionCoordinator(
            memory=memory,
            access_tier=AccessTier.CONTRIBUTOR,
            auto_announce=False,
        )
        result = coord.resolve_conflict(
            resource_key="res",
            other_agent_id="other_agent",
            strategy=ConflictStrategy.LAST_WRITE_WINS,
        )
        assert result.strategy_used == ConflictStrategy.LAST_WRITE_WINS
        assert result.winner_agent_id == coord.agent_id


# ---------------------------------------------------------------------------
# Distributed locking (with mock client)
# ---------------------------------------------------------------------------


class TestCrossSessionCoordinatorLocking:
    """acquire_lock / release_lock / check_lock with mocked Redis client."""

    def test_acquire_lock_success(self):
        """acquire_lock returns True when setnx succeeds."""
        memory = _mock_memory()
        memory._base._client.setnx.return_value = True

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.acquire_lock("resource_x") is True
        memory._base._client.expire.assert_called()

    def test_acquire_lock_failure(self):
        """acquire_lock returns False when setnx fails (lock held)."""
        memory = _mock_memory()
        memory._base._client.setnx.return_value = False

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.acquire_lock("resource_x") is False

    def test_release_lock_when_owner(self):
        """release_lock returns True and deletes key when we own the lock."""
        memory = _mock_memory()

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        memory._base._client.get.return_value = coord.agent_id.encode()

        assert coord.release_lock("resource_x") is True
        memory._base._client.delete.assert_called()

    def test_release_lock_when_not_owner(self):
        """release_lock returns False when another agent holds the lock."""
        memory = _mock_memory()
        memory._base._client.get.return_value = b"some_other_agent"

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.release_lock("resource_x") is False
        memory._base._client.delete.assert_not_called()

    def test_check_lock_returns_owner(self):
        """check_lock returns the agent_id string stored in the lock key."""
        memory = _mock_memory()
        memory._base._client.get.return_value = b"lock_holder"

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.check_lock("resource_x") == "lock_holder"

    def test_check_lock_returns_none_when_unlocked(self):
        """check_lock returns None when the lock key is absent."""
        memory = _mock_memory()
        memory._base._client.get.return_value = None

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.check_lock("resource_x") is None


# ---------------------------------------------------------------------------
# Session discovery with mock client
# ---------------------------------------------------------------------------


class TestCrossSessionCoordinatorSessionDiscovery:
    """get_active_sessions / get_session with mocked Redis client."""

    def test_get_active_sessions_returns_fresh_sessions(self):
        """get_active_sessions returns non-stale sessions from Redis."""
        memory = _mock_memory()
        info = _make_session_info("peer_agent")
        memory._base._client.hgetall.return_value = {
            b"peer_agent": json.dumps(info.to_dict()).encode()
        }

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        sessions = coord.get_active_sessions()
        assert len(sessions) == 1
        assert sessions[0].agent_id == "peer_agent"

    def test_get_active_sessions_filters_stale(self):
        """get_active_sessions drops sessions whose heartbeat has expired."""
        memory = _mock_memory()
        stale = _make_session_info(
            "stale_agent",
            offset_seconds=STALE_THRESHOLD_SECONDS + 100,
        )
        memory._base._client.hgetall.return_value = {
            b"stale_agent": json.dumps(stale.to_dict()).encode()
        }

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        sessions = coord.get_active_sessions()
        assert sessions == []

    def test_get_active_sessions_skips_invalid_json(self):
        """get_active_sessions tolerates malformed JSON in Redis."""
        memory = _mock_memory()
        good = _make_session_info("good_agent")
        memory._base._client.hgetall.return_value = {
            b"good_agent": json.dumps(good.to_dict()).encode(),
            b"bad_agent": b"not { valid } json",
        }

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        sessions = coord.get_active_sessions()
        assert len(sessions) == 1
        assert sessions[0].agent_id == "good_agent"

    def test_get_session_returns_session_info(self):
        """get_session returns SessionInfo for a known, fresh agent."""
        memory = _mock_memory()
        info = _make_session_info("target_agent")
        memory._base._client.hget.return_value = json.dumps(info.to_dict()).encode()

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        result = coord.get_session("target_agent")
        assert result is not None
        assert result.agent_id == "target_agent"

    def test_get_session_returns_none_for_missing_key(self):
        """get_session returns None when the key is absent in Redis."""
        memory = _mock_memory()
        memory._base._client.hget.return_value = None

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.get_session("missing_agent") is None

    def test_get_session_returns_none_for_stale(self):
        """get_session returns None when the session has expired."""
        memory = _mock_memory()
        stale = _make_session_info(
            "stale_agent",
            offset_seconds=STALE_THRESHOLD_SECONDS + 100,
        )
        memory._base._client.hget.return_value = json.dumps(stale.to_dict()).encode()

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.get_session("stale_agent") is None


# ---------------------------------------------------------------------------
# Announce / depart with mock client
# ---------------------------------------------------------------------------


class TestCrossSessionCoordinatorAnnounceDepart:
    """announce() and depart() when Redis client is present."""

    def test_announce_calls_hset_and_publish(self):
        """announce() stores session data and publishes to the channel."""
        memory = _mock_memory()
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        coord.announce()

        memory._base._client.hset.assert_called()
        memory._base._client.publish.assert_called()

    def test_depart_calls_hdel_and_publish(self):
        """depart() removes session from registry and publishes departure."""
        memory = _mock_memory()
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        coord.depart()

        memory._base._client.hdel.assert_called_with(KEY_ACTIVE_AGENTS, coord.agent_id)
        memory._base._client.publish.assert_called()


# ---------------------------------------------------------------------------
# get_session with malformed stored data
# ---------------------------------------------------------------------------


class TestCrossSessionCoordinatorGetSessionInvalidData:
    """get_session() degrades to None on malformed stored session data."""

    def test_get_session_returns_none_for_invalid_json(self):
        """get_session returns None instead of raising on unparseable data."""
        memory = _mock_memory()
        memory._base._client.hget.return_value = b"not { valid } json"

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.get_session("corrupt_agent") is None

    def test_get_session_returns_none_for_missing_fields(self):
        """get_session returns None when stored JSON lacks required keys."""
        memory = _mock_memory()
        memory._base._client.hget.return_value = json.dumps({"unexpected": "shape"}).encode()

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.get_session("partial_agent") is None


# ---------------------------------------------------------------------------
# Heartbeat internals (_send_heartbeat / _heartbeat_loop)
# ---------------------------------------------------------------------------


class TestCrossSessionCoordinatorHeartbeatInternals:
    """Direct exercise of the heartbeat send path and loop body."""

    def test_send_heartbeat_degraded_no_op(self):
        """_send_heartbeat() is a no-op when the Redis client is None."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        coord._send_heartbeat()  # Should not raise

    def test_send_heartbeat_updates_timestamp_and_stores(self):
        """_send_heartbeat() refreshes last_heartbeat and writes to Redis."""
        memory = _mock_memory()
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        before = coord.session_info.last_heartbeat

        coord._send_heartbeat()

        assert coord.session_info.last_heartbeat >= before
        args, _kwargs = memory._base._client.hset.call_args
        assert args[0] == KEY_ACTIVE_AGENTS
        assert args[1] == coord.agent_id
        stored = json.loads(args[2])
        assert stored["agent_id"] == coord.agent_id

    def test_heartbeat_loop_sends_until_stop_event_fires(self):
        """_heartbeat_loop() sends heartbeats until the stop event is set."""
        memory = _mock_memory()
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        # First wait returns False (keep running), second returns True (stop).
        coord._heartbeat_stop = MagicMock()
        coord._heartbeat_stop.wait.side_effect = [False, True]

        coord._heartbeat_loop()

        assert memory._base._client.hset.call_count == 1


# ---------------------------------------------------------------------------
# check_lock with a non-bytes owner value
# ---------------------------------------------------------------------------


class TestCrossSessionCoordinatorCheckLockStrOwner:
    """check_lock() when the client returns an already-decoded string."""

    def test_check_lock_returns_str_owner_unchanged(self):
        """check_lock returns the owner when Redis yields str, not bytes."""
        memory = _mock_memory()
        memory._base._client.get.return_value = "str_lock_holder"

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coord.check_lock("resource_x") == "str_lock_holder"


# ---------------------------------------------------------------------------
# subscribe_to_sessions event dispatch
# ---------------------------------------------------------------------------


def _pubsub_with_messages(memory: RedisShortTermMemory, messages: list[dict]) -> MagicMock:
    """Wire a mock pubsub whose listen() yields the given finite messages."""
    pubsub = MagicMock()
    pubsub.listen.return_value = messages
    memory._base._client.pubsub.return_value = pubsub
    return pubsub


class TestCrossSessionCoordinatorSubscribe:
    """subscribe_to_sessions() event loop with a mocked pubsub."""

    def test_subscribe_degraded_returns_without_subscribing(self):
        """subscribe_to_sessions() returns immediately when client is None."""
        memory = RedisShortTermMemory(use_mock=True)
        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        coord.subscribe_to_sessions()  # Should not raise, no client to use

    def test_subscribe_subscribes_to_sessions_channel(self):
        """subscribe_to_sessions() subscribes the pubsub to CHANNEL_SESSIONS."""
        memory = _mock_memory()
        pubsub = _pubsub_with_messages(memory, [])

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        coord.subscribe_to_sessions()

        pubsub.subscribe.assert_called_once_with(CHANNEL_SESSIONS)

    def test_subscribe_dispatches_session_joined_to_handlers(self):
        """A session_joined event invokes registered joined-handlers."""
        memory = _mock_memory()
        info = _make_session_info("joining_peer")
        event = {"event": "session_joined", "session": info.to_dict()}
        _pubsub_with_messages(
            memory,
            [{"type": "message", "data": json.dumps(event).encode()}],
        )

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        handler = MagicMock()
        coord.on_session_joined(handler)
        coord.subscribe_to_sessions()

        handler.assert_called_once()
        received = handler.call_args[0][0]
        assert isinstance(received, SessionInfo)
        assert received.agent_id == "joining_peer"

    def test_subscribe_dispatches_session_left_to_handlers(self):
        """A session_left event invokes left-handlers with the agent_id."""
        memory = _mock_memory()
        event = {"event": "session_left", "agent_id": "departing_peer"}
        _pubsub_with_messages(
            memory,
            [{"type": "message", "data": json.dumps(event)}],
        )

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        handler = MagicMock()
        coord.on_session_left(handler)
        coord.subscribe_to_sessions()

        handler.assert_called_once_with("departing_peer")

    def test_subscribe_skips_non_message_types(self):
        """Subscription-confirmation messages are ignored, not dispatched."""
        memory = _mock_memory()
        _pubsub_with_messages(memory, [{"type": "subscribe", "data": 1}])

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        joined = MagicMock()
        left = MagicMock()
        coord.on_session_joined(joined)
        coord.on_session_left(left)
        coord.subscribe_to_sessions()

        joined.assert_not_called()
        left.assert_not_called()

    def test_subscribe_tolerates_malformed_event_payloads(self):
        """Malformed payloads are logged and skipped; later events still fire."""
        memory = _mock_memory()
        good = {"event": "session_left", "agent_id": "still_works"}
        _pubsub_with_messages(
            memory,
            [
                {"type": "message", "data": b"not { valid } json"},
                # Valid JSON but missing the "session" key -> KeyError path
                {"type": "message", "data": json.dumps({"event": "session_joined"})},
                {"type": "message", "data": json.dumps(good)},
            ],
        )

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        left = MagicMock()
        coord.on_session_left(left)
        coord.subscribe_to_sessions()  # Should not raise

        left.assert_called_once_with("still_works")

    def test_subscribe_ignores_unknown_event_names(self):
        """Events with unrecognized names dispatch to no handlers."""
        memory = _mock_memory()
        _pubsub_with_messages(
            memory,
            [{"type": "message", "data": json.dumps({"event": "mystery"})}],
        )

        coord = CrossSessionCoordinator(memory=memory, auto_announce=False)
        joined = MagicMock()
        left = MagicMock()
        coord.on_session_joined(joined)
        coord.on_session_left(left)
        coord.subscribe_to_sessions()

        joined.assert_not_called()
        left.assert_not_called()
