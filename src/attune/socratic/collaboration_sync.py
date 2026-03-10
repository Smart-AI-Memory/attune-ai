"""Collaboration Real-Time Sync Support.

Adapter and event model for real-time synchronization of collaborative sessions.
Extracted from collaboration.py for maintainability.

Contains:
- SyncEvent: Dataclass for sync events
- SyncAdapter: Base adapter for real-time infrastructure (WebSocket, SSE, etc.)

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SyncEvent:
    """An event for real-time synchronization."""

    event_id: str
    session_id: str
    event_type: str
    payload: dict[str, Any]
    author_id: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert the collaboration event to a dictionary."""
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "author_id": self.author_id,
            "timestamp": self.timestamp.isoformat(),
        }


class SyncAdapter:
    """Adapter for real-time synchronization.

    Override this class to integrate with your preferred
    real-time infrastructure (WebSocket, SSE, etc.).
    """

    def __init__(self, session_id: str):
        """Initialize the adapter.

        Args:
            session_id: Session to sync

        """
        self.session_id = session_id
        self._event_handlers: list[Callable[[SyncEvent], None]] = []

    def emit(self, event: SyncEvent):
        """Emit an event to all connected clients.

        Override this to implement actual network transmission.
        """
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Handler failure should not prevent other handlers.
                # Event propagation must continue for sync reliability.
                pass

    def on_event(self, handler: Callable[[SyncEvent], None]):
        """Register an event handler.

        Args:
            handler: Callback for incoming events

        """
        self._event_handlers.append(handler)

    def create_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        author_id: str,
    ) -> SyncEvent:
        """Create a sync event.

        Args:
            event_type: Type of event
            payload: Event data
            author_id: Author of the event

        Returns:
            Created SyncEvent

        """
        event_id = hashlib.sha256(
            f"{self.session_id}:{event_type}:{time.time()}".encode(),
        ).hexdigest()[:12]

        return SyncEvent(
            event_id=event_id,
            session_id=self.session_id,
            event_type=event_type,
            payload=payload,
            author_id=author_id,
        )
