"""WebSocket notification system for hot-reload events.

Notifies connected clients when workflows are reloaded.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ReloadNotificationManager:
    """Manages WebSocket connections for hot-reload notifications.

    Broadcasts reload events to all connected clients.
    """

    def __init__(self):
        """Initialize notification manager."""
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Register a new WebSocket connection.

        Args:
            websocket: WebSocket connection to register

        """
        await websocket.accept()

        async with self._lock:
            self._connections.append(websocket)

        logger.info(f"WebSocket connected (total: {len(self._connections)})")

        # Send welcome message
        await self._send_to_client(
            websocket,
            {
                "event": "connected",
                "message": "Hot-reload notifications enabled",
                "active_connections": len(self._connections),
            },
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection.

        Args:
            websocket: WebSocket connection to unregister

        """
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)

        logger.info(f"WebSocket disconnected (remaining: {len(self._connections)})")

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast message to all connected clients.

        Args:
            message: Message dictionary to broadcast

        """
        if not self._connections:
            logger.debug("No active connections, skipping broadcast")
            return

        async with self._lock:
            # Create a copy to avoid modification during iteration
            connections = self._connections.copy()

        # Broadcast to all connections
        disconnected = []
        for websocket in connections:
            try:
                await self._send_to_client(websocket, message)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Error sending to client: {e}")
                disconnected.append(websocket)

        # Remove disconnected clients
        if disconnected:
            async with self._lock:
                for websocket in disconnected:
                    if websocket in self._connections:
                        self._connections.remove(websocket)

            logger.info(f"Removed {len(disconnected)} disconnected clients")

    async def _send_to_client(
        self,
        websocket: WebSocket,
        message: dict[str, Any],
    ) -> None:
        """Send message to a specific client.

        Args:
            websocket: WebSocket connection
            message: Message to send

        """
        try:
            await websocket.send_json(message)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to send message to client: {e}")
            raise

    def get_connection_count(self) -> int:
        """Get number of active connections.

        Returns:
            Number of connected clients

        """
        return len(self._connections)


# Global notification manager instance
_notification_manager: ReloadNotificationManager | None = None


def get_notification_manager() -> ReloadNotificationManager:
    """Get the global notification manager.

    Returns:
        Global ReloadNotificationManager instance

    """
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = ReloadNotificationManager()
    return _notification_manager


def create_notification_callback() -> Callable[[dict[str, Any]], None]:
    """Create a callback function for the workflow reloader.

    Returns:
        Callback function that broadcasts notifications

    """

    def notification_callback(message: dict[str, Any]) -> None:
        """Callback to broadcast reload notifications.

        Args:
            message: Notification message

        """
        manager = get_notification_manager()

        # Run async broadcast in event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a task if loop is running
                asyncio.create_task(manager.broadcast(message))
            else:
                # Run directly if no loop running
                asyncio.run(manager.broadcast(message))
        except RuntimeError:
            # No event loop, log warning
            logger.warning("No event loop available for notification")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error in notification callback: {e}")

    return notification_callback
