"""Pub/Sub messaging for real-time agent communication.

This module provides publish/subscribe messaging:
- Publish: Send messages to channels
- Subscribe: Register handlers for channels
- Unsubscribe: Remove handlers
- Background listener thread management

Key Prefix: PREFIX_PUBSUB = "pubsub:"

Classes:
    PubSubManager: Real-time publish/subscribe operations

Example:
    >>> from attune.memory.short_term.pubsub import PubSubManager
    >>> from attune.memory.types import AgentCredentials, AccessTier
    >>> pubsub = PubSubManager(base_ops)
    >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
    >>> def handler(msg): print(msg)
    >>> pubsub.subscribe("signals", handler)
    >>> pubsub.publish("signals", {"event": "done"}, creds)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0

"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from attune.memory.types import (
    AgentCredentials,
)

if TYPE_CHECKING:
    from redis.client import PubSub

    from attune.memory.short_term.base import BaseOperations

logger = structlog.get_logger(__name__)


class PubSubManager:
    """Real-time publish/subscribe operations.

    Provides channel-based messaging for agent communication.
    Uses Redis Pub/Sub for real-time message delivery with
    background listener threads.

    The class manages its own state for subscriptions and
    background threads, composed with BaseOperations for
    Redis client access.

    Attributes:
        PREFIX_PUBSUB: Key prefix for pubsub channels

    Example:
        >>> pubsub = PubSubManager(base_ops)
        >>> def on_signal(msg):
        ...     print(f"Signal: {msg['data']}")
        >>> pubsub.subscribe("agent_signals", on_signal)
        >>> pubsub.publish("agent_signals", {"type": "heartbeat"}, creds)

    """

    PREFIX_PUBSUB = "pubsub:"

    def __init__(self, base: BaseOperations) -> None:
        """Initialize pub/sub manager.

        Args:
            base: BaseOperations instance for Redis client access

        """
        self._base = base
        self._pubsub: PubSub | None = None
        self._pubsub_client = None  # Dedicated Redis connection for Pub/Sub
        self._pubsub_thread: threading.Thread | None = None
        self._subscriptions: dict[str, list[Callable[[dict], None]]] = {}
        self._pubsub_running: bool = False
        self._mock_pubsub_handlers: dict[str, list[Callable[[dict], None]]] = {}

    def publish(
        self,
        channel: str,
        message: dict,
        credentials: AgentCredentials,
    ) -> int:
        """Publish a message to a channel for real-time notifications.

        Args:
            channel: Channel name (will be prefixed)
            message: Message payload (dict)
            credentials: Agent credentials (must be CONTRIBUTOR+)

        Returns:
            Number of subscribers that received the message

        Raises:
            PermissionError: If credentials lack publish access

        Example:
            >>> pubsub.publish(
            ...     "agent_signals",
            ...     {"event": "task_complete", "task_id": "123"},
            ...     creds
            ... )
            2

        """
        if not credentials.can_stage():
            raise PermissionError(
                f"Agent {credentials.agent_id} cannot publish. "
                "Requires CONTRIBUTOR tier or higher.",
            )

        start_time = time.perf_counter()
        full_channel = f"{self.PREFIX_PUBSUB}{channel}"

        payload = {
            "channel": channel,
            "from_agent": credentials.agent_id,
            "timestamp": datetime.now().isoformat(),
            "data": message,
        }

        # Handle mock mode
        if self._base.use_mock:
            handlers = self._mock_pubsub_handlers.get(full_channel, [])
            for handler in handlers:
                try:
                    handler(payload)
                except Exception as e:
                    logger.warning("pubsub_handler_error", channel=channel, error=str(e))
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._base._metrics.record_operation("publish", latency_ms)
            return len(handlers)

        # Handle real Redis client
        if self._base._client is None:
            return 0

        count = self._base._client.publish(full_channel, json.dumps(payload))
        latency_ms = (time.perf_counter() - start_time) * 1000
        self._base._metrics.record_operation("publish", latency_ms)

        logger.debug("pubsub_published", channel=channel, subscribers=count)
        return int(count)

    def subscribe(
        self,
        channel: str,
        handler: Callable[[dict], None],
        credentials: AgentCredentials | None = None,
    ) -> bool:
        """Subscribe to a channel for real-time notifications.

        Args:
            channel: Channel name to subscribe to
            handler: Callback function receiving message dict
            credentials: Optional credentials (any tier can subscribe)

        Returns:
            True if subscribed successfully

        Example:
            >>> def on_message(msg):
            ...     print(f"Received: {msg['data']}")
            >>> pubsub.subscribe("agent_signals", on_message)
            True

        """
        full_channel = f"{self.PREFIX_PUBSUB}{channel}"

        # Handle mock mode
        if self._base.use_mock:
            if full_channel not in self._mock_pubsub_handlers:
                self._mock_pubsub_handlers[full_channel] = []
            self._mock_pubsub_handlers[full_channel].append(handler)
            logger.info("pubsub_subscribed_mock", channel=channel)
            return True

        # Handle real Redis client
        if self._base._client is None:
            return False

        # Store handler
        if full_channel not in self._subscriptions:
            self._subscriptions[full_channel] = []
        self._subscriptions[full_channel].append(handler)

        # Create dedicated Pub/Sub connection (separate from main pool)
        if self._pubsub is None:
            try:
                import redis

                kwargs = self._base._config.to_redis_kwargs()
                self._pubsub_client = redis.Redis(**kwargs)
                self._pubsub = self._pubsub_client.pubsub()
            except Exception as e:
                logger.error("pubsub_connection_failed", error=str(e))
                return False

        # Subscribe with internal handler
        self._pubsub.subscribe(**{full_channel: self._pubsub_message_handler})

        # Start listener thread if not running
        if not self._pubsub_running:
            self._pubsub_running = True
            self._pubsub_thread = threading.Thread(
                target=self._pubsub_listener,
                daemon=True,
                name="redis-pubsub-listener",
            )
            self._pubsub_thread.start()

        logger.info("pubsub_subscribed", channel=channel)
        return True

    def _pubsub_message_handler(self, message: dict) -> None:
        """Internal handler for pubsub messages."""
        if message["type"] != "message":
            return

        channel = message["channel"]
        if isinstance(channel, bytes):
            channel = channel.decode()

        try:
            payload = json.loads(message["data"])
        except json.JSONDecodeError:
            payload = {"raw": message["data"]}

        handlers = self._subscriptions.get(channel, [])
        for handler in handlers:
            try:
                handler(payload)
            except Exception as e:
                logger.warning("pubsub_handler_error", channel=channel, error=str(e))

    def _pubsub_listener(self) -> None:
        """Background thread for listening to pubsub messages.

        Includes reconnection logic with exponential backoff on
        connection failures. Re-subscribes to all channels after
        reconnecting.
        """
        reconnect_attempts = 0
        max_reconnect_attempts = 5
        base_delay = 1.0

        while self._pubsub_running:
            if self._pubsub is None:
                break
            try:
                self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                reconnect_attempts = 0  # Reset on success
            except (ConnectionError, TimeoutError, OSError) as e:
                reconnect_attempts += 1
                if reconnect_attempts > max_reconnect_attempts:
                    logger.error(
                        "pubsub_reconnect_exhausted",
                        attempts=reconnect_attempts,
                        error=str(e),
                    )
                    self._pubsub_running = False
                    break

                delay = min(base_delay * (2 ** (reconnect_attempts - 1)), 30.0)
                logger.warning(
                    "pubsub_reconnecting",
                    attempt=reconnect_attempts,
                    delay=delay,
                    error=str(e),
                )
                time.sleep(delay)

                # Attempt to reconnect and resubscribe
                try:
                    import redis

                    if self._pubsub_client:
                        try:
                            self._pubsub_client.close()
                        except Exception:
                            # INTENTIONAL: Best-effort cleanup before reconnect
                            pass

                    kwargs = self._base._config.to_redis_kwargs()
                    self._pubsub_client = redis.Redis(**kwargs)
                    self._pubsub = self._pubsub_client.pubsub()

                    # Re-subscribe to all channels
                    for channel in self._subscriptions:
                        self._pubsub.subscribe(**{channel: self._pubsub_message_handler})
                    logger.info("pubsub_reconnected", channels=list(self._subscriptions.keys()))
                except Exception as reconnect_err:
                    logger.warning(
                        "pubsub_reconnect_failed",
                        attempt=reconnect_attempts,
                        error=str(reconnect_err),
                    )
            except Exception as e:
                # INTENTIONAL: Listener thread must not crash on unexpected errors
                logger.warning("pubsub_listener_error", error=str(e))
                time.sleep(1)

    def unsubscribe(self, channel: str) -> bool:
        """Unsubscribe from a channel.

        Args:
            channel: Channel name to unsubscribe from

        Returns:
            True if unsubscribed successfully

        Example:
            >>> pubsub.unsubscribe("agent_signals")
            True

        """
        full_channel = f"{self.PREFIX_PUBSUB}{channel}"

        # Handle mock mode
        if self._base.use_mock:
            self._mock_pubsub_handlers.pop(full_channel, None)
            return True

        # Handle real Redis client
        if self._pubsub is None:
            return False

        self._pubsub.unsubscribe(full_channel)
        self._subscriptions.pop(full_channel, None)
        return True

    def close(self) -> None:
        """Close pubsub connection and stop listener thread.

        Should be called when the manager is no longer needed
        to clean up resources and stop background threads.

        Example:
            >>> pubsub.close()

        """
        self._pubsub_running = False
        if self._pubsub_thread is not None:
            self._pubsub_thread.join(timeout=3.0)
            self._pubsub_thread = None
        if self._pubsub:
            self._pubsub.close()
            self._pubsub = None
        if self._pubsub_client:
            self._pubsub_client.close()
            self._pubsub_client = None
        self._subscriptions.clear()
        self._mock_pubsub_handlers.clear()
