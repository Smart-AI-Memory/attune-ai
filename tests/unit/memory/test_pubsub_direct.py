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
