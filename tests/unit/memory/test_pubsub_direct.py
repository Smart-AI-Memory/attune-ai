"""Tests for attune.memory.short_term.pubsub.PubSubManager.

Covers previously-uncovered branches:
- publish() real Redis path (lines 149-157): client is None → 0; client present → publish
- subscribe() real Redis path (lines 193-215): client is None → False;
  subscriptions dict init; pubsub creation; thread start; connection error
- handler error in mock mode (line 141-143)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune.memory.short_term.pubsub import PubSubManager
from attune.memory.types import AccessTier, AgentCredentials

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_real_base(client=None):
    """Return a base mock that reports use_mock=False (real Redis path)."""
    base = MagicMock()
    base.use_mock = False
    base._client = client
    base._metrics = MagicMock()
    base._metrics.record_operation = MagicMock()
    base._config = MagicMock()
    base._config.to_redis_kwargs.return_value = {}
    return base


def _make_mock_base():
    """Return a base mock that reports use_mock=True (mock path)."""
    base = MagicMock()
    base.use_mock = True
    base._metrics = MagicMock()
    base._metrics.record_operation = MagicMock()
    return base


def _contributor():
    return AgentCredentials("agent1", AccessTier.CONTRIBUTOR)


# ---------------------------------------------------------------------------
# publish() — real Redis path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPublishRealRedis:
    def test_publish_returns_zero_when_client_none(self):
        base = _make_real_base(client=None)
        pubsub = PubSubManager(base)
        creds = _contributor()
        result = pubsub.publish("signals", {"x": 1}, creds)
        assert result == 0

    def test_publish_calls_redis_publish(self):
        mock_client = MagicMock()
        mock_client.publish.return_value = 3
        base = _make_real_base(client=mock_client)
        pubsub = PubSubManager(base)
        creds = _contributor()

        result = pubsub.publish("signals", {"event": "done"}, creds)

        assert result == 3
        mock_client.publish.assert_called_once()
        # First arg is the full channel name
        call_args = mock_client.publish.call_args[0]
        assert "pubsub:signals" in call_args[0]

    def test_publish_records_operation_latency(self):
        mock_client = MagicMock()
        mock_client.publish.return_value = 1
        base = _make_real_base(client=mock_client)
        pubsub = PubSubManager(base)
        pubsub.publish("ch", {"k": "v"}, _contributor())
        base._metrics.record_operation.assert_called_with("publish", pytest.approx(0, abs=500))


# ---------------------------------------------------------------------------
# publish() — mock mode handler error (line 141-143)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPublishMockHandlerError:
    def test_handler_exception_does_not_propagate(self):
        base = _make_mock_base()
        pubsub = PubSubManager(base)
        creds = _contributor()

        def bad_handler(msg):
            raise RuntimeError("handler broke")

        # Register the handler directly
        pubsub._mock_pubsub_handlers["pubsub:ch"] = [bad_handler]

        # Should not raise
        result = pubsub.publish("ch", {"data": 1}, creds)
        assert result == 1  # 1 handler attempted

    def test_multiple_handlers_all_called_despite_first_failing(self):
        base = _make_mock_base()
        pubsub = PubSubManager(base)
        creds = _contributor()
        called = []

        def bad_handler(msg):
            raise RuntimeError("fail")

        def good_handler(msg):
            called.append(msg)

        pubsub._mock_pubsub_handlers["pubsub:multi"] = [bad_handler, good_handler]
        pubsub.publish("multi", {"x": 1}, creds)
        assert len(called) == 1


# ---------------------------------------------------------------------------
# subscribe() — real Redis path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSubscribeRealRedis:
    def test_subscribe_returns_false_when_client_none(self):
        base = _make_real_base(client=None)
        pubsub = PubSubManager(base)
        result = pubsub.subscribe("ch", lambda m: None)
        assert result is False

    def test_subscribe_adds_to_subscriptions_dict(self):
        mock_client = MagicMock()
        mock_pubsub_obj = MagicMock()
        mock_client.pubsub.return_value = mock_pubsub_obj

        with patch("redis.Redis", return_value=mock_client):
            base = _make_real_base(client=mock_client)
            pubsub = PubSubManager(base)
            handler = lambda m: None  # noqa: E731
            pubsub.subscribe("signals", handler)

        assert "pubsub:signals" in pubsub._subscriptions
        assert handler in pubsub._subscriptions["pubsub:signals"]

    def test_subscribe_creates_pubsub_and_starts_thread(self):
        mock_client = MagicMock()
        mock_pubsub_obj = MagicMock()
        mock_client.pubsub.return_value = mock_pubsub_obj

        with (
            patch("redis.Redis", return_value=mock_client),
            patch("threading.Thread") as MockThread,
        ):
            mock_thread = MagicMock()
            MockThread.return_value = mock_thread

            base = _make_real_base(client=mock_client)
            pubsub = PubSubManager(base)
            pubsub.subscribe("ch", lambda m: None)

        MockThread.assert_called_once()
        mock_thread.start.assert_called_once()
        assert pubsub._pubsub_running is True

    def test_subscribe_second_channel_reuses_existing_pubsub(self):
        """Second subscribe should not create a new pubsub connection."""
        mock_client = MagicMock()
        mock_pubsub_obj = MagicMock()
        mock_client.pubsub.return_value = mock_pubsub_obj

        with (
            patch("redis.Redis", return_value=mock_client),
            patch("threading.Thread") as MockThread,
        ):
            MockThread.return_value = MagicMock()

            base = _make_real_base(client=mock_client)
            pubsub = PubSubManager(base)
            pubsub.subscribe("ch1", lambda m: None)
            pubsub.subscribe("ch2", lambda m: None)

        # pubsub() should only be called once (on first subscribe)
        assert mock_client.pubsub.call_count == 1

    def test_subscribe_returns_false_on_connection_error(self):
        base = _make_real_base(client=MagicMock())

        with patch("redis.Redis", side_effect=ConnectionError("refused")):
            pubsub = PubSubManager(base)
            result = pubsub.subscribe("ch", lambda m: None)

        assert result is False


# ---------------------------------------------------------------------------
# PermissionError on publish from low-tier agent
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPublishPermission:
    def test_observer_cannot_publish(self):
        base = _make_mock_base()
        pubsub = PubSubManager(base)
        observer = AgentCredentials("observer1", AccessTier.OBSERVER)

        with pytest.raises(PermissionError):
            pubsub.publish("ch", {}, observer)


# ---------------------------------------------------------------------------
# subscribe() — mock mode (lines 186-190)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSubscribeMockMode:
    def test_mock_subscribe_stores_handler(self):
        """Lines 186-190: mock mode registers handler and returns True."""
        base = _make_mock_base()
        pubsub = PubSubManager(base)
        handler = lambda m: None  # noqa: E731
        result = pubsub.subscribe("alerts", handler)
        assert result is True
        assert handler in pubsub._mock_pubsub_handlers["pubsub:alerts"]

    def test_mock_subscribe_second_handler_same_channel(self):
        """Line 197->199: existing subscriptions list — appends to existing."""
        base = _make_mock_base()
        pubsub = PubSubManager(base)
        h1 = lambda m: None  # noqa: E731
        h2 = lambda m: None  # noqa: E731
        pubsub.subscribe("ch", h1)
        pubsub.subscribe("ch", h2)
        assert h1 in pubsub._mock_pubsub_handlers["pubsub:ch"]
        assert h2 in pubsub._mock_pubsub_handlers["pubsub:ch"]

    def test_real_subscribe_second_handler_appends_to_existing(self):
        """Line 197->199: real mode — second subscribe to same channel appends."""
        mock_client = MagicMock()
        mock_pubsub_obj = MagicMock()
        mock_client.pubsub.return_value = mock_pubsub_obj

        with (
            patch("redis.Redis", return_value=mock_client),
            patch("threading.Thread") as MockThread,
        ):
            MockThread.return_value = MagicMock()
            base = _make_real_base(client=mock_client)
            pubsub = PubSubManager(base)
            h1 = lambda m: None  # noqa: E731
            h2 = lambda m: None  # noqa: E731
            pubsub.subscribe("ch", h1)
            pubsub.subscribe("ch", h2)  # second subscribe to same channel

        # Both handlers should be registered
        assert h1 in pubsub._subscriptions["pubsub:ch"]
        assert h2 in pubsub._subscriptions["pubsub:ch"]


# ---------------------------------------------------------------------------
# _pubsub_message_handler (lines 232-250)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPubSubMessageHandler:
    def test_non_message_type_returns_early(self):
        """Line 232-233: type != 'message' → early return."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        called = []
        pubsub._subscriptions["pubsub:ch"] = [lambda m: called.append(m)]

        pubsub._pubsub_message_handler(
            {"type": "subscribe", "channel": b"pubsub:ch", "data": b"{}"}
        )
        assert called == []

    def test_message_type_calls_handler(self):
        """Lines 244-247: 'message' type → calls registered handlers."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        called = []
        pubsub._subscriptions["pubsub:ch"] = [lambda m: called.append(m)]

        pubsub._pubsub_message_handler(
            {"type": "message", "channel": b"pubsub:ch", "data": b'{"event": "test"}'}
        )
        assert len(called) == 1
        assert called[0] == {"event": "test"}

    def test_str_channel_not_decoded(self):
        """Line 236->239: non-bytes channel skips the decode branch."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        called = []
        pubsub._subscriptions["pubsub:ch"] = [lambda m: called.append(m)]

        pubsub._pubsub_message_handler(
            {"type": "message", "channel": "pubsub:ch", "data": '{"k": 1}'}
        )
        assert called[0] == {"k": 1}

    def test_bytes_channel_decoded(self):
        """Line 236-237: bytes channel decoded to str."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        called = []
        pubsub._subscriptions["pubsub:ch"] = [lambda m: called.append(m)]

        pubsub._pubsub_message_handler(
            {"type": "message", "channel": b"pubsub:ch", "data": b'{"k": 1}'}
        )
        assert len(called) == 1

    def test_invalid_json_creates_raw_payload(self):
        """Lines 241-242: JSONDecodeError → payload = {'raw': data}."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        called = []
        pubsub._subscriptions["pubsub:ch"] = [lambda m: called.append(m)]

        pubsub._pubsub_message_handler(
            {"type": "message", "channel": b"pubsub:ch", "data": b"not-json"}
        )
        assert called[0] == {"raw": b"not-json"}

    def test_handler_exception_does_not_propagate(self):
        """Lines 248-250: handler raises → logged, not re-raised."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)

        def bad_handler(m):
            raise RuntimeError("handler crash")

        pubsub._subscriptions["pubsub:ch"] = [bad_handler]
        # Should not raise
        pubsub._pubsub_message_handler(
            {"type": "message", "channel": b"pubsub:ch", "data": b'{"x": 1}'}
        )

    def test_no_handlers_for_channel(self):
        """Line 244: no handlers for channel → no-op."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        # No subscriptions registered
        pubsub._pubsub_message_handler(
            {"type": "message", "channel": b"pubsub:unknown", "data": b'{"x": 1}'}
        )


# ---------------------------------------------------------------------------
# _pubsub_listener (lines 263-318)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPubSubListener:
    def test_loop_exits_when_pubsub_running_false(self):
        """Line 263->exit: loop exits when _pubsub_running is False."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        pubsub._pubsub_running = False
        # Should return immediately
        pubsub._pubsub_listener()

    def test_loop_exits_when_pubsub_is_none(self):
        """Line 265: break when _pubsub is None."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        pubsub._pubsub_running = True
        pubsub._pubsub = None
        pubsub._pubsub_listener()
        # Should break immediately without error

    def test_loop_runs_one_iteration_then_stops(self):
        """Lines 267-268: successful get_message → resets reconnect_attempts."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        mock_pubsub_obj = MagicMock()
        pubsub._pubsub = mock_pubsub_obj
        pubsub._pubsub_running = True

        call_count = [0]

        def mock_get_message(**kwargs):
            call_count[0] += 1
            pubsub._pubsub_running = False  # Stop after first iteration
            return None

        mock_pubsub_obj.get_message.side_effect = mock_get_message
        pubsub._pubsub_listener()
        assert call_count[0] == 1

    def test_connection_error_reconnects(self):
        """Lines 269-314: ConnectionError → reconnect attempt."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        mock_pubsub_obj = MagicMock()
        pubsub._pubsub = mock_pubsub_obj
        pubsub._pubsub_client = MagicMock()
        pubsub._pubsub_running = True
        pubsub._subscriptions = {"pubsub:ch": [lambda m: None]}

        new_redis = MagicMock()
        new_pubsub = MagicMock()
        new_redis.pubsub.return_value = new_pubsub

        mock_pubsub_obj.get_message.side_effect = ConnectionError("connection lost")

        def stop_after_reconnect(**kwargs):
            pubsub._pubsub_running = False
            return None

        new_pubsub.get_message.side_effect = stop_after_reconnect

        with (
            patch("time.sleep"),
            patch("redis.Redis", return_value=new_redis),
        ):
            pubsub._pubsub_listener()

        # Reconnect happened: new pubsub was used at least once
        assert new_pubsub.get_message.called

    def test_reconnect_exhausted_stops_listener(self):
        """Lines 271-278: > max_reconnect_attempts → sets _pubsub_running = False."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        mock_pubsub_obj = MagicMock()
        pubsub._pubsub = mock_pubsub_obj
        pubsub._pubsub_client = MagicMock()
        pubsub._pubsub_running = True

        # Always raise ConnectionError to exhaust reconnect attempts
        mock_pubsub_obj.get_message.side_effect = ConnectionError("permanent failure")

        # Reconnect will also fail
        with (
            patch("time.sleep"),
            patch("redis.Redis", side_effect=ConnectionError("still broken")),
        ):
            pubsub._pubsub_listener()

        assert pubsub._pubsub_running is False

    def test_reconnect_attempt_fails_gracefully(self):
        """Lines 308-314: reconnect raises → logged, continues loop."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        mock_pubsub_obj = MagicMock()
        pubsub._pubsub = mock_pubsub_obj
        pubsub._pubsub_client = MagicMock()
        pubsub._pubsub_running = True
        pubsub._subscriptions = {"pubsub:ch": []}

        # First raise to enter reconnect branch; redis.Redis fails so self._pubsub
        # is NOT reassigned. Next iteration: stop the loop.
        call_count = [0]

        def mock_get_message(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ConnectionError("transient")
            pubsub._pubsub_running = False
            return None

        mock_pubsub_obj.get_message.side_effect = mock_get_message

        with (
            patch("time.sleep"),
            patch("redis.Redis", side_effect=Exception("reconnect failed")),
        ):
            pubsub._pubsub_listener()

        assert call_count[0] >= 2

    def test_reconnect_when_pubsub_client_is_none(self):
        """Line 293->300: skip close() block when _pubsub_client is None."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        mock_pubsub_obj = MagicMock()
        pubsub._pubsub = mock_pubsub_obj
        pubsub._pubsub_client = None  # explicitly None
        pubsub._pubsub_running = True
        pubsub._subscriptions = {"pubsub:ch": []}

        new_redis = MagicMock()
        new_pubsub = MagicMock()
        new_redis.pubsub.return_value = new_pubsub

        mock_pubsub_obj.get_message.side_effect = ConnectionError("lost")

        def stop_after_reconnect(**kwargs):
            pubsub._pubsub_running = False
            return None

        new_pubsub.get_message.side_effect = stop_after_reconnect

        with (
            patch("time.sleep"),
            patch("redis.Redis", return_value=new_redis),
        ):
            pubsub._pubsub_listener()

        assert new_pubsub.get_message.called

    def test_reconnect_close_raises_swallowed(self):
        """Lines 296-298: _pubsub_client.close() raising is swallowed."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        mock_pubsub_obj = MagicMock()
        pubsub._pubsub = mock_pubsub_obj
        old_client = MagicMock()
        old_client.close.side_effect = RuntimeError("close failed")
        pubsub._pubsub_client = old_client
        pubsub._pubsub_running = True
        pubsub._subscriptions = {"pubsub:ch": []}

        new_redis = MagicMock()
        new_pubsub = MagicMock()
        new_redis.pubsub.return_value = new_pubsub

        mock_pubsub_obj.get_message.side_effect = ConnectionError("lost")

        def stop_after_reconnect(**kwargs):
            pubsub._pubsub_running = False
            return None

        new_pubsub.get_message.side_effect = stop_after_reconnect

        with (
            patch("time.sleep"),
            patch("redis.Redis", return_value=new_redis),
        ):
            pubsub._pubsub_listener()

        # close() was attempted and its exception was swallowed
        assert old_client.close.called
        assert new_pubsub.get_message.called

    def test_unexpected_exception_continues_loop(self):
        """Lines 315-318: unexpected Exception → logged, continues."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        mock_pubsub_obj = MagicMock()
        pubsub._pubsub = mock_pubsub_obj
        pubsub._pubsub_running = True

        call_count = [0]

        def mock_get_message(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("unexpected error")  # not ConnectionError
            pubsub._pubsub_running = False
            return None

        mock_pubsub_obj.get_message.side_effect = mock_get_message

        with patch("time.sleep"):
            pubsub._pubsub_listener()

        assert call_count[0] == 2

    def test_reconnect_resubscribes_all_channels(self):
        """Lines 305-306: after reconnect, re-subscribes to all channels."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        mock_pubsub_obj = MagicMock()
        pubsub._pubsub = mock_pubsub_obj
        pubsub._pubsub_client = MagicMock()
        pubsub._pubsub_running = True
        pubsub._subscriptions = {
            "pubsub:ch1": [lambda m: None],
            "pubsub:ch2": [lambda m: None],
        }

        new_pubsub = MagicMock()
        new_redis = MagicMock()
        new_redis.pubsub.return_value = new_pubsub

        mock_pubsub_obj.get_message.side_effect = ConnectionError("lost")

        def stop_after_reconnect(**kwargs):
            pubsub._pubsub_running = False
            return None

        new_pubsub.get_message.side_effect = stop_after_reconnect

        with (
            patch("time.sleep"),
            patch("redis.Redis", return_value=new_redis),
        ):
            pubsub._pubsub_listener()

        # Re-subscribe should be called for both channels
        assert new_pubsub.subscribe.call_count >= 2


# ---------------------------------------------------------------------------
# unsubscribe() (lines 334-347)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUnsubscribe:
    def test_mock_mode_removes_handler(self):
        """Lines 337-339: mock mode → pops from handlers dict."""
        base = _make_mock_base()
        pubsub = PubSubManager(base)
        pubsub._mock_pubsub_handlers["pubsub:ch"] = [lambda m: None]
        result = pubsub.unsubscribe("ch")
        assert result is True
        assert "pubsub:ch" not in pubsub._mock_pubsub_handlers

    def test_real_mode_no_pubsub_returns_false(self):
        """Lines 342-343: no pubsub connection → returns False."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        pubsub._pubsub = None
        result = pubsub.unsubscribe("ch")
        assert result is False

    def test_real_mode_with_pubsub_unsubscribes(self):
        """Lines 345-347: pubsub present → calls pubsub.unsubscribe."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        mock_pubsub_obj = MagicMock()
        pubsub._pubsub = mock_pubsub_obj
        pubsub._subscriptions["pubsub:ch"] = [lambda m: None]

        result = pubsub.unsubscribe("ch")

        assert result is True
        mock_pubsub_obj.unsubscribe.assert_called_once_with("pubsub:ch")
        assert "pubsub:ch" not in pubsub._subscriptions


# ---------------------------------------------------------------------------
# close() (lines 359-370)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClose:
    def test_close_stops_running_flag(self):
        """Line 359: sets _pubsub_running = False."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        pubsub._pubsub_running = True
        pubsub.close()
        assert pubsub._pubsub_running is False

    def test_close_joins_thread(self):
        """Lines 360-362: joins and clears thread."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        mock_thread = MagicMock()
        pubsub._pubsub_thread = mock_thread
        pubsub.close()
        mock_thread.join.assert_called_once_with(timeout=3.0)
        assert pubsub._pubsub_thread is None

    def test_close_closes_pubsub(self):
        """Lines 363-365: closes and clears pubsub."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        mock_pubsub_obj = MagicMock()
        pubsub._pubsub = mock_pubsub_obj
        pubsub.close()
        mock_pubsub_obj.close.assert_called_once()
        assert pubsub._pubsub is None

    def test_close_closes_pubsub_client(self):
        """Lines 366-368: closes and clears pubsub_client."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        mock_client = MagicMock()
        pubsub._pubsub_client = mock_client
        pubsub.close()
        mock_client.close.assert_called_once()
        assert pubsub._pubsub_client is None

    def test_close_clears_subscriptions(self):
        """Lines 369-370: clears subscriptions and mock handlers."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        pubsub._subscriptions["pubsub:ch"] = [lambda m: None]
        pubsub._mock_pubsub_handlers["pubsub:ch"] = [lambda m: None]
        pubsub.close()
        assert pubsub._subscriptions == {}
        assert pubsub._mock_pubsub_handlers == {}

    def test_close_handles_no_thread_or_pubsub(self):
        """close() safe when thread and pubsub are None."""
        base = _make_real_base(client=MagicMock())
        pubsub = PubSubManager(base)
        pubsub._pubsub_thread = None
        pubsub._pubsub = None
        pubsub._pubsub_client = None
        pubsub.close()  # Should not raise
