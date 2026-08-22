"""Agent Coordination via TTL Signals.

Pattern 2 from Agent Coordination Architecture - TTL-based inter-agent
communication for orchestration, synchronization, and coordination.

Usage:
    # Agent A signals completion
    coordinator = CoordinationSignals()
    coordinator.signal(
        signal_type="task_complete",
        source_agent="agent-a",
        target_agent="agent-b",
        payload={"result": "success", "data": {...}}
    )

    # Agent B waits for signal
    signal = coordinator.wait_for_signal(
        signal_type="task_complete",
        source_agent="agent-a",
        timeout=30.0
    )
    if signal:
        process(signal.payload)

    # Orchestrator broadcasts to all agents
    coordinator.broadcast(
        signal_type="abort",
        source_agent="orchestrator",
        payload={"reason": "user_cancelled"}
    )

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from attune.telemetry._redis_batch import mget_json

if TYPE_CHECKING:
    from attune.memory.types import AgentCredentials

logger = logging.getLogger(__name__)


@dataclass
class CoordinationSignal:
    """Coordination signal between agents.

    Ephemeral message with TTL, used for agent-to-agent communication.
    """

    signal_id: str
    signal_type: str  # "task_complete", "abort", "ready", "checkpoint", etc.
    source_agent: str
    target_agent: str | None  # None for broadcast
    payload: dict[str, Any]
    timestamp: datetime
    ttl_seconds: int = 60

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "payload": self.payload,
            "timestamp": (
                self.timestamp.isoformat()
                if isinstance(self.timestamp, datetime)
                else self.timestamp
            ),
            "ttl_seconds": self.ttl_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CoordinationSignal:
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now(timezone.utc)

        return cls(
            signal_id=data["signal_id"],
            signal_type=data["signal_type"],
            source_agent=data["source_agent"],
            target_agent=data.get("target_agent"),
            payload=data.get("payload", {}),
            timestamp=timestamp,
            ttl_seconds=data.get("ttl_seconds", 60),
        )


def _signal_from_record(key: str, data: dict[str, Any]) -> CoordinationSignal | None:
    """Build a signal from one scanned record, or None if it is malformed.

    Per-record tolerance (class G2): one unparseable record is skipped
    alone rather than raising into the caller's listing-wide handler.
    """
    try:
        return CoordinationSignal.from_dict(data)
    except (KeyError, TypeError, ValueError):
        logger.debug("Skipping malformed coordination signal %s", key, exc_info=True)
        return None


class CoordinationSignals:
    """TTL-based inter-agent coordination signals.

    Agents can:
    - Send signals to specific agents
    - Broadcast signals to all agents
    - Wait for specific signals with timeout
    - Check for pending signals without blocking

    Signals expire automatically via TTL, preventing stale coordination.
    """

    DEFAULT_TTL = 60  # Default signal TTL: 60 seconds
    BROADCAST_TARGET = "*"  # Special target for broadcast signals
    KEY_PREFIX = "empathy:signal:"  # Redis key prefix (consistent with framework)

    def __init__(self, memory=None, agent_id: str | None = None, enable_streaming: bool = False):
        """Initialize coordination signals.

        Args:
            memory: Memory instance for storing signals
            agent_id: This agent's ID (for receiving targeted signals)
            enable_streaming: If True, publish signal events to Redis Streams
                            for real-time monitoring (Pattern 4).

        """
        self.memory = memory
        self.agent_id = agent_id
        self._enable_streaming = enable_streaming
        self._event_streamer = None

        if self.memory is None:
            try:
                from attune.telemetry import UsageTracker

                tracker = UsageTracker.get_instance()
                if hasattr(tracker, "_memory"):
                    self.memory = tracker._memory
            except (ImportError, AttributeError):
                pass

        if self.memory is None:
            logger.warning("No memory backend available for coordination signals")

    def _get_event_streamer(self):
        """Get or create EventStreamer instance (lazy initialization)."""
        if not self._enable_streaming:
            return None

        if self._event_streamer is None:
            try:
                from attune.telemetry.event_streaming import EventStreamer

                self._event_streamer = EventStreamer(memory=self.memory)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to initialize EventStreamer: {e}")
                self._enable_streaming = False

        return self._event_streamer

    def signal(
        self,
        signal_type: str,
        source_agent: str | None = None,
        target_agent: str | None = None,
        payload: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
        credentials: AgentCredentials | None = None,
    ) -> str:
        """Send a coordination signal.

        Args:
            signal_type: Type of signal (e.g., "task_complete", "abort", "ready")
            source_agent: Source agent ID (defaults to self.agent_id)
            target_agent: Target agent ID (None for broadcast)
            payload: Signal payload data
            ttl_seconds: TTL for this signal (defaults to DEFAULT_TTL)
            credentials: Agent credentials for permission check (optional but recommended)

        Returns:
            Signal ID

        Raises:
            PermissionError: If credentials provided but agent lacks CONTRIBUTOR tier

        Security:
            Coordination signals require CONTRIBUTOR tier or higher. If credentials
            are not provided, a warning is logged but the signal is still sent
            (backward compatibility). For production use, always provide credentials.

        """
        if not self.memory:
            logger.warning("Cannot send signal: no memory backend")
            return ""

        # Permission check for coordination signals (requires CONTRIBUTOR tier)
        if credentials is not None:
            if not credentials.can_stage():
                raise PermissionError(
                    f"Agent {credentials.agent_id} (Tier {credentials.tier.name}) "
                    "cannot send coordination signals. Requires CONTRIBUTOR tier or higher.",
                )
        else:
            # Log warning if no credentials provided (security best practice)
            logger.warning(
                "Sending coordination signal without credentials - "
                "permission check bypassed. Provide credentials for secure coordination.",
            )

        source = source_agent or self.agent_id or "unknown"
        signal_id = f"signal_{uuid4().hex[:8]}"
        ttl = ttl_seconds or self.DEFAULT_TTL

        signal = CoordinationSignal(
            signal_id=signal_id,
            signal_type=signal_type,
            source_agent=source,
            target_agent=target_agent,
            payload=payload or {},
            timestamp=datetime.now(timezone.utc),
            ttl_seconds=ttl,
        )

        # Store signal with TTL (Pattern 2)
        # Key format: empathy:signal:{target}:{type}:{id}
        target_key = target_agent or self.BROADCAST_TARGET
        key = f"{self.KEY_PREFIX}{target_key}:{signal_type}:{signal_id}"

        try:
            # Use direct Redis access for custom TTL
            if hasattr(self.memory, "_client") and self.memory._client:
                import json

                self.memory._client.setex(key, ttl, json.dumps(signal.to_dict()))
            else:
                logger.warning("Cannot send signal: no Redis backend available")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to send signal {signal_id}: {e}")

        # Publish to event stream (Pattern 4 - optional)
        streamer = self._get_event_streamer()
        if streamer:
            try:
                streamer.publish_event(
                    event_type="coordination_signal",
                    data=signal.to_dict(),
                    source="attune",
                )
            except Exception as e:  # noqa: BLE001
                logger.debug(f"Failed to publish coordination signal event to stream: {e}")

        return signal_id

    def broadcast(
        self,
        signal_type: str,
        source_agent: str | None = None,
        payload: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
        credentials: AgentCredentials | None = None,
    ) -> str:
        """Broadcast signal to all agents.

        Args:
            signal_type: Type of signal
            source_agent: Source agent ID
            payload: Signal payload
            ttl_seconds: TTL for signal
            credentials: Agent credentials for permission check

        Returns:
            Signal ID

        Raises:
            PermissionError: If credentials provided but agent lacks CONTRIBUTOR tier

        """
        return self.signal(
            signal_type=signal_type,
            source_agent=source_agent,
            target_agent=None,  # Broadcast
            payload=payload,
            ttl_seconds=ttl_seconds,
            credentials=credentials,
        )

    def wait_for_signal(
        self,
        signal_type: str,
        source_agent: str | None = None,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> CoordinationSignal | None:
        """Wait for a specific signal (blocking with timeout).

        Args:
            signal_type: Type of signal to wait for
            source_agent: Optional source agent filter
            timeout: Maximum wait time in seconds
            poll_interval: Poll interval in seconds

        Returns:
            CoordinationSignal if received, None if timeout

        """
        if not self.memory or not self.agent_id:
            return None

        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check for signal
            signal = self.check_signal(
                signal_type=signal_type,
                source_agent=source_agent,
                consume=True,
            )

            if signal:
                return signal

            # Sleep before next poll
            time.sleep(poll_interval)

        return None

    def check_signal(
        self,
        signal_type: str,
        source_agent: str | None = None,
        consume: bool = True,
    ) -> CoordinationSignal | None:
        """Check for a signal without blocking.

        Args:
            signal_type: Type of signal to check
            source_agent: Optional source agent filter
            consume: If True, remove signal after reading

        Returns:
            CoordinationSignal if available, None otherwise

        """
        if not self.memory or not self.agent_id:
            return None

        try:
            # Scan for matching signals
            # Check targeted signals: empathy:signal:{agent_id}:{type}:*
            # Check broadcast signals: empathy:signal:*:{type}:*
            patterns = [
                f"{self.KEY_PREFIX}{self.agent_id}:{signal_type}:*",
                f"{self.KEY_PREFIX}{self.BROADCAST_TARGET}:{signal_type}:*",
            ]

            for pattern in patterns:
                if hasattr(self.memory, "_client"):
                    keys = list(self.memory._client.scan_iter(match=pattern, count=100))
                else:
                    continue

                # One MGET for the scanned keys, not one get() per key.
                for key, data in mget_json(self.memory._client, keys):
                    if not data:
                        continue

                    signal = _signal_from_record(key, data)
                    if signal is None:
                        continue

                    # Filter by source if specified
                    if source_agent and signal.source_agent != source_agent:
                        continue

                    # Consume signal if requested
                    if consume:
                        self._delete_signal(key)

                    return signal

            return None
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to check signal: {e}")
            return None

    def get_pending_signals(self, signal_type: str | None = None) -> list[CoordinationSignal]:
        """Get all pending signals for this agent.

        Args:
            signal_type: Optional filter by signal type

        Returns:
            List of pending signals

        """
        if not self.memory or not self.agent_id:
            return []

        try:
            # Scan for all signals for this agent
            patterns = [
                f"{self.KEY_PREFIX}{self.agent_id}:*",
                f"{self.KEY_PREFIX}{self.BROADCAST_TARGET}:*",
            ]

            signals = []
            for pattern in patterns:
                if hasattr(self.memory, "_client"):
                    keys = list(self.memory._client.scan_iter(match=pattern, count=100))
                else:
                    continue

                # One MGET for the scanned keys, not one get() per key.
                for key, data in mget_json(self.memory._client, keys):
                    if not data:
                        continue

                    signal = _signal_from_record(key, data)
                    if signal is None:
                        continue

                    # Filter by type if specified
                    if signal_type and signal.signal_type != signal_type:
                        continue

                    signals.append(signal)

            return signals
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to get pending signals: {e}")
            return []

    def clear_signals(self, signal_type: str | None = None) -> int:
        """Clear all signals for this agent.

        Args:
            signal_type: Optional filter by signal type

        Returns:
            Number of signals cleared

        """
        if not self.memory or not self.agent_id:
            return 0

        signals = self.get_pending_signals(signal_type=signal_type)
        count = 0

        for signal in signals:
            # Reconstruct key
            target_key = signal.target_agent or self.BROADCAST_TARGET
            key = f"{self.KEY_PREFIX}{target_key}:{signal.signal_type}:{signal.signal_id}"
            if self._delete_signal(key):
                count += 1

        return count

    def _delete_signal(self, key: str) -> bool:
        """Delete signal from memory."""
        if not self.memory:
            return False

        try:
            if hasattr(self.memory, "_client"):
                return self.memory._client.delete(key) > 0
            return False
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Failed to delete signal {key}: {e}")
            return False
