"""Agent Heartbeat Tracking System.

Pattern 1 from Agent Coordination Architecture - TTL-based heartbeat monitoring
for tracking agent execution status and detecting stale/failed agents.

Usage:
    # Start tracking an agent
    coordinator = HeartbeatCoordinator()
    coordinator.start_heartbeat(
        agent_id="code-review-abc123",
        metadata={"workflow": "code-review", "run_id": "xyz"}
    )

    # Update progress
    coordinator.beat(
        status="running",
        progress=0.5,
        current_task="Analyzing functions"
    )

    # Stop tracking
    coordinator.stop_heartbeat(final_status="completed")

    # Monitor all active agents
    active_agents = coordinator.get_active_agents()
    for agent in active_agents:
        print(f"{agent.agent_id}: {agent.status} - {agent.current_task}")

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentHeartbeat:
    """Agent heartbeat data structure.

    Represents the current state of a running agent, stored in Redis with TTL.
    """

    agent_id: str
    status: str  # "starting", "running", "completed", "failed", "cancelled"
    progress: float  # 0.0 to 1.0
    current_task: str
    last_beat: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    display_name: str | None = None  # Optional human-readable name for dashboard

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "progress": self.progress,
            "current_task": self.current_task,
            "last_beat": (
                self.last_beat.isoformat()
                if isinstance(self.last_beat, datetime)
                else self.last_beat
            ),
            "metadata": self.metadata,
            "display_name": self.display_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentHeartbeat:
        """Create from dictionary."""
        # Convert ISO string back to datetime
        last_beat = data.get("last_beat")
        if isinstance(last_beat, str):
            last_beat = datetime.fromisoformat(last_beat)
        elif not isinstance(last_beat, datetime):
            last_beat = datetime.utcnow()

        return cls(
            agent_id=data["agent_id"],
            status=data["status"],
            progress=data["progress"],
            current_task=data["current_task"],
            last_beat=last_beat,
            metadata=data.get("metadata", {}),
            display_name=data.get("display_name"),
        )


class HeartbeatCoordinator:
    """Coordinates agent heartbeats using Redis TTL keys.

    Agents publish heartbeats with a TTL. If an agent stops responding,
    its heartbeat key expires automatically, indicating failure/crash.

    Attributes:
        HEARTBEAT_TTL: Default heartbeat TTL in seconds (30s)
        HEARTBEAT_INTERVAL: Recommended update interval (10s)
    """

    HEARTBEAT_TTL = 30  # Heartbeat expires after 30s of no updates
    HEARTBEAT_INTERVAL = 10  # Agents should update every 10s

    def __init__(self, memory=None, enable_streaming: bool = False):
        """Initialize heartbeat coordinator.

        Args:
            memory: Memory instance (UnifiedMemory or ShortTermMemory).
                   If None, attempts to get from UsageTracker.
            enable_streaming: If True, publish heartbeat events to Redis Streams
                            for real-time monitoring (Pattern 4).
        """
        self.memory = memory
        self.agent_id: str | None = None
        self.display_name: str | None = None
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
            logger.warning("No memory backend available for heartbeat tracking")

    def _get_event_streamer(self):
        """Get or create EventStreamer instance (lazy initialization)."""
        if not self._enable_streaming:
            return None

        if self._event_streamer is None:
            try:
                from attune.telemetry.event_streaming import EventStreamer

                self._event_streamer = EventStreamer(memory=self.memory)
            except Exception as e:
                logger.warning(f"Failed to initialize EventStreamer: {e}")
                self._enable_streaming = False

        return self._event_streamer

    def start_heartbeat(
        self, agent_id: str, metadata: dict[str, Any] | None = None, display_name: str | None = None
    ) -> None:
        """Start heartbeat for an agent.

        Args:
            agent_id: Unique agent identifier
            metadata: Initial metadata (workflow, run_id, etc.)
            display_name: Optional human-readable name for dashboard display
        """
        if not self.memory:
            logger.debug("Heartbeat tracking disabled (no memory backend)")
            return

        self.agent_id = agent_id
        self.display_name = display_name
        self._publish_heartbeat(
            status="starting",
            progress=0.0,
            current_task="initializing",
            metadata=metadata or {},
            display_name=display_name,
        )

    def beat(self, status: str = "running", progress: float = 0.0, current_task: str = "") -> None:
        """Publish heartbeat update.

        Args:
            status: Current agent status
            progress: Progress percentage (0.0 - 1.0)
            current_task: Human-readable current task description
        """
        if not self.agent_id or not self.memory:
            return

        self._publish_heartbeat(
            status=status,
            progress=progress,
            current_task=current_task,
            metadata={},
            display_name=self.display_name,
        )

    def stop_heartbeat(self, final_status: str = "completed") -> None:
        """Stop heartbeat (agent finished).

        Args:
            final_status: Final status ("completed", "failed", "cancelled")
        """
        if not self.agent_id or not self.memory:
            return

        # Publish final heartbeat with short TTL
        self._publish_heartbeat(
            status=final_status,
            progress=1.0,
            current_task="finished",
            metadata={"final": True},
        )

        # Clear agent ID
        self.agent_id = None

    def _publish_heartbeat(
        self,
        status: str,
        progress: float,
        current_task: str,
        metadata: dict[str, Any],
        display_name: str | None = None,
    ) -> None:
        """Publish heartbeat to Redis with TTL and optionally to event stream."""
        if not self.memory or not self.agent_id:
            return

        heartbeat = AgentHeartbeat(
            agent_id=self.agent_id,
            status=status,
            progress=progress,
            current_task=current_task,
            last_beat=datetime.utcnow(),
            metadata=metadata,
            display_name=display_name,
        )

        # Store in Redis with TTL (Pattern 1)
        key = f"empathy:heartbeat:{self.agent_id}"
        try:
            # Use direct Redis access for heartbeats (need custom 30s TTL)
            if hasattr(self.memory, "_client") and self.memory._client:
                # Direct Redis access with setex for custom TTL
                import json

                self.memory._client.setex(key, self.HEARTBEAT_TTL, json.dumps(heartbeat.to_dict()))
            else:
                logger.warning("Cannot publish heartbeat: no Redis backend available")
        except Exception as e:
            logger.warning(f"Failed to publish heartbeat for {self.agent_id}: {e}")

        # Publish to event stream (Pattern 4 - optional)
        streamer = self._get_event_streamer()
        if streamer:
            try:
                streamer.publish_event(
                    event_type="agent_heartbeat",
                    data=heartbeat.to_dict(),
                    source="attune",
                )
            except Exception as e:
                logger.debug(f"Failed to publish heartbeat event to stream: {e}")

    def get_active_agents(self) -> list[AgentHeartbeat]:
        """Get all currently active agents.

        Returns:
            List of active agent heartbeats
        """
        if not self.memory:
            return []

        try:
            # Scan for empathy:heartbeat:* keys
            if hasattr(self.memory, "_client") and self.memory._client:
                keys = list(self.memory._client.scan_iter(match="empathy:heartbeat:*", count=100))
            else:
                logger.warning("Cannot scan for heartbeats: no Redis access")
                return []

            heartbeats = []
            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode("utf-8")

                data = self._retrieve_heartbeat(key)
                if data:
                    heartbeats.append(AgentHeartbeat.from_dict(data))

            return heartbeats
        except Exception as e:
            logger.error(f"Failed to get active agents: {e}")
            return []

    def is_agent_alive(self, agent_id: str) -> bool:
        """Check if agent is still alive.

        Args:
            agent_id: Agent to check

        Returns:
            True if heartbeat key exists (agent is alive)
        """
        if not self.memory:
            return False

        key = f"empathy:heartbeat:{agent_id}"
        data = self._retrieve_heartbeat(key)
        return data is not None

    def get_agent_status(self, agent_id: str) -> AgentHeartbeat | None:
        """Get current status of an agent.

        Args:
            agent_id: Agent to query

        Returns:
            AgentHeartbeat or None if agent not active
        """
        if not self.memory:
            return None

        key = f"empathy:heartbeat:{agent_id}"
        data = self._retrieve_heartbeat(key)

        if data:
            return AgentHeartbeat.from_dict(data)
        return None

    def _retrieve_heartbeat(self, key: str) -> dict[str, Any] | None:
        """Retrieve heartbeat data from memory.

        Heartbeat keys are stored directly as 'empathy:heartbeat:{agent_id}' and must be
        retrieved via direct Redis access, not through the standard retrieve() method
        which expects keys with 'working:{agent_id}:{key}' format.
        """
        if not self.memory:
            return None

        try:
            # Use direct Redis access for heartbeat keys
            if hasattr(self.memory, "_client") and self.memory._client:
                import json

                data = self.memory._client.get(key)
                if data:
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    result = json.loads(data)
                    return result if isinstance(result, dict) else None
            return None
        except Exception:
            logger.debug("Failed to retrieve heartbeat %s", key, exc_info=True)
            return None

    def get_stale_agents(self, threshold_seconds: float = 60.0) -> list[AgentHeartbeat]:
        """Get agents that haven't updated in a while (but key still exists).

        This detects agents that are stuck or slow, not crashed (TTL would expire).

        Args:
            threshold_seconds: Time without update to consider stale

        Returns:
            List of stale agent heartbeats
        """
        active = self.get_active_agents()
        now = datetime.utcnow()
        stale = []

        for agent in active:
            time_since_beat = (now - agent.last_beat).total_seconds()
            if time_since_beat > threshold_seconds and agent.status not in (
                "completed",
                "failed",
                "cancelled",
            ):
                stale.append(agent)

        return stale
