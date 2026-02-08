"""Unit tests for WebSocket hot-reload notification system.

This test suite provides comprehensive coverage for the WebSocket-based
hot-reload notification system, including connection management, broadcasting,
and error handling.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("watchdog", reason="watchdog required for hot-reload tests")

from attune.hot_reload.websocket import (  # noqa: E402
    ReloadNotificationManager,
    create_notification_callback,
    get_notification_manager,
)


@pytest.mark.unit
class TestReloadNotificationManagerInit:
    """Test suite for ReloadNotificationManager initialization."""

    def test_init_creates_empty_connections_list(self):
        """Test that initialization creates empty connections list."""
        manager = ReloadNotificationManager()

        assert manager._connections == []

    def test_init_creates_async_lock(self):
        """Test that initialization creates async lock."""
        manager = ReloadNotificationManager()

        assert isinstance(manager._lock, asyncio.Lock)

    def test_get_connection_count_returns_zero_initially(self):
        """Test that connection count is 0 for new manager."""
        manager = ReloadNotificationManager()

        assert manager.get_connection_count() == 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestReloadNotificationManagerConnect:
    """Test suite for WebSocket connection registration."""

    async def test_connect_accepts_websocket(self):
        """Test that connect accepts WebSocket connection."""
        manager = ReloadNotificationManager()
        websocket = AsyncMock()

        await manager.connect(websocket)

        websocket.accept.assert_called_once()

    async def test_connect_adds_websocket_to_connections(self):
        """Test that connect adds WebSocket to connections list."""
        manager = ReloadNotificationManager()
        websocket = AsyncMock()

        await manager.connect(websocket)

        assert websocket in manager._connections
        assert manager.get_connection_count() == 1

    async def test_connect_sends_welcome_message(self):
        """Test that connect sends welcome message to client."""
        manager = ReloadNotificationManager()
        websocket = AsyncMock()

        await manager.connect(websocket)

        # Verify send_json was called with welcome message
        websocket.send_json.assert_called_once()
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["event"] == "connected"
        assert call_args["message"] == "Hot-reload notifications enabled"
        assert call_args["active_connections"] == 1

    async def test_connect_multiple_websockets(self):
        """Test connecting multiple WebSocket clients."""
        manager = ReloadNotificationManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)

        assert manager.get_connection_count() == 3
        assert ws1 in manager._connections
        assert ws2 in manager._connections
        assert ws3 in manager._connections


@pytest.mark.unit
@pytest.mark.asyncio
class TestReloadNotificationManagerDisconnect:
    """Test suite for WebSocket disconnection."""

    async def test_disconnect_removes_websocket_from_connections(self):
        """Test that disconnect removes WebSocket from connections."""
        manager = ReloadNotificationManager()
        websocket = AsyncMock()

        # Connect then disconnect
        await manager.connect(websocket)
        assert manager.get_connection_count() == 1

        await manager.disconnect(websocket)
        assert manager.get_connection_count() == 0
        assert websocket not in manager._connections

    async def test_disconnect_handles_nonexistent_websocket(self):
        """Test that disconnect handles WebSocket not in connections."""
        manager = ReloadNotificationManager()
        websocket = AsyncMock()

        # Disconnect without connecting - should not raise
        await manager.disconnect(websocket)
        assert manager.get_connection_count() == 0

    async def test_disconnect_leaves_other_connections_intact(self):
        """Test that disconnect only removes specified WebSocket."""
        manager = ReloadNotificationManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        # Connect all three
        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)
        assert manager.get_connection_count() == 3

        # Disconnect ws2
        await manager.disconnect(ws2)

        assert manager.get_connection_count() == 2
        assert ws1 in manager._connections
        assert ws2 not in manager._connections
        assert ws3 in manager._connections


@pytest.mark.unit
@pytest.mark.asyncio
class TestReloadNotificationManagerBroadcast:
    """Test suite for broadcast functionality."""

    async def test_broadcast_sends_to_all_connected_clients(self):
        """Test that broadcast sends message to all clients."""
        manager = ReloadNotificationManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        # Connect clients
        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)

        # Clear previous send_json calls from connect
        ws1.send_json.reset_mock()
        ws2.send_json.reset_mock()
        ws3.send_json.reset_mock()

        # Broadcast message
        message = {"event": "reload", "workflow": "test-workflow"}
        await manager.broadcast(message)

        # All clients should receive message
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)
        ws3.send_json.assert_called_once_with(message)

    async def test_broadcast_does_nothing_when_no_connections(self):
        """Test that broadcast does nothing when no clients connected."""
        manager = ReloadNotificationManager()

        # Broadcast with no connections - should not raise
        message = {"event": "reload", "workflow": "test"}
        await manager.broadcast(message)

        # Should complete without error
        assert manager.get_connection_count() == 0

    async def test_broadcast_handles_send_error_and_removes_client(self):
        """Test that broadcast removes client on send error."""
        manager = ReloadNotificationManager()
        ws_good = AsyncMock()
        ws_bad = AsyncMock()

        # Connect both (send_json works for welcome message)
        await manager.connect(ws_good)
        await manager.connect(ws_bad)
        assert manager.get_connection_count() == 2

        # Clear previous calls
        ws_good.send_json.reset_mock()
        ws_bad.send_json.reset_mock()

        # NOW make ws_bad fail on next send
        ws_bad.send_json.side_effect = Exception("Connection closed")

        # Broadcast message
        message = {"event": "reload"}
        await manager.broadcast(message)

        # Good client should receive message
        ws_good.send_json.assert_called_once_with(message)

        # Bad client should be removed from connections
        assert ws_good in manager._connections
        assert ws_bad not in manager._connections
        assert manager.get_connection_count() == 1

    async def test_broadcast_removes_multiple_failed_clients(self):
        """Test that broadcast removes all failed clients."""
        manager = ReloadNotificationManager()
        ws1 = AsyncMock()  # Good
        ws2 = AsyncMock()  # Bad
        ws3 = AsyncMock()  # Bad
        ws4 = AsyncMock()  # Good

        # Connect all (send_json works for welcome messages)
        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)
        await manager.connect(ws4)
        assert manager.get_connection_count() == 4

        # Clear previous calls
        ws1.send_json.reset_mock()
        ws2.send_json.reset_mock()
        ws3.send_json.reset_mock()
        ws4.send_json.reset_mock()

        # NOW make ws2 and ws3 fail on next send
        ws2.send_json.side_effect = Exception("Error 1")
        ws3.send_json.side_effect = Exception("Error 2")

        # Broadcast
        await manager.broadcast({"event": "reload"})

        # Only good clients should remain
        assert ws1 in manager._connections
        assert ws2 not in manager._connections
        assert ws3 not in manager._connections
        assert ws4 in manager._connections
        assert manager.get_connection_count() == 2


@pytest.mark.unit
@pytest.mark.asyncio
class TestReloadNotificationManagerSendToClient:
    """Test suite for sending to individual clients."""

    async def test_send_to_client_sends_json_message(self):
        """Test that _send_to_client sends JSON message to WebSocket."""
        manager = ReloadNotificationManager()
        websocket = AsyncMock()

        message = {"event": "test", "data": "value"}
        await manager._send_to_client(websocket, message)

        websocket.send_json.assert_called_once_with(message)

    async def test_send_to_client_raises_on_error(self):
        """Test that _send_to_client raises exception on send error."""
        manager = ReloadNotificationManager()
        websocket = AsyncMock()
        websocket.send_json.side_effect = Exception("Send failed")

        message = {"event": "test"}

        with pytest.raises(Exception, match="Send failed"):
            await manager._send_to_client(websocket, message)


@pytest.mark.unit
class TestGetNotificationManager:
    """Test suite for global notification manager."""

    def test_get_notification_manager_returns_instance(self):
        """Test that get_notification_manager returns ReloadNotificationManager."""
        manager = get_notification_manager()

        assert isinstance(manager, ReloadNotificationManager)

    def test_get_notification_manager_returns_singleton(self):
        """Test that get_notification_manager returns same instance."""
        manager1 = get_notification_manager()
        manager2 = get_notification_manager()

        assert manager1 is manager2

    def test_get_notification_manager_creates_on_first_call(self):
        """Test that get_notification_manager creates manager on first call."""
        # Clear global state
        import attune.hot_reload.websocket as ws_module

        ws_module._notification_manager = None

        # First call should create new instance
        manager = get_notification_manager()
        assert manager is not None
        assert isinstance(manager, ReloadNotificationManager)


@pytest.mark.unit
class TestCreateNotificationCallback:
    """Test suite for notification callback creation."""

    def test_create_notification_callback_returns_callable(self):
        """Test that create_notification_callback returns callable."""
        callback = create_notification_callback()

        assert callable(callback)

    @patch("attune.hot_reload.websocket.get_notification_manager")
    @patch("attune.hot_reload.websocket.asyncio.get_event_loop")
    def test_callback_broadcasts_message_with_running_loop(self, mock_get_loop, mock_get_manager):
        """Test that callback broadcasts when event loop is running."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        mock_get_loop.return_value = mock_loop

        # Create and call callback
        callback = create_notification_callback()
        message = {"event": "reload", "workflow": "test"}

        with patch("attune.hot_reload.websocket.asyncio.create_task") as mock_create_task:
            callback(message)

            # Should create task for broadcast
            mock_create_task.assert_called_once()

    @patch("attune.hot_reload.websocket.get_notification_manager")
    @patch("attune.hot_reload.websocket.asyncio.get_event_loop")
    @patch("attune.hot_reload.websocket.asyncio.run")
    def test_callback_broadcasts_with_non_running_loop(
        self, mock_run, mock_get_loop, mock_get_manager
    ):
        """Test that callback uses asyncio.run when loop not running."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        mock_loop = MagicMock()
        mock_loop.is_running.return_value = False
        mock_get_loop.return_value = mock_loop

        # Create and call callback
        callback = create_notification_callback()
        message = {"event": "reload"}

        callback(message)

        # Should use asyncio.run
        mock_run.assert_called_once()

    @patch("attune.hot_reload.websocket.get_notification_manager")
    @patch("attune.hot_reload.websocket.asyncio.get_event_loop")
    def test_callback_handles_runtime_error(self, mock_get_loop, mock_get_manager):
        """Test that callback handles RuntimeError gracefully."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        mock_get_loop.side_effect = RuntimeError("No event loop")

        # Create and call callback
        callback = create_notification_callback()
        message = {"event": "reload"}

        # Should not raise - logs warning instead
        callback(message)

    @patch("attune.hot_reload.websocket.get_notification_manager")
    @patch("attune.hot_reload.websocket.asyncio.get_event_loop")
    def test_callback_handles_general_exception(self, mock_get_loop, mock_get_manager):
        """Test that callback handles general exceptions gracefully."""
        # Setup manager to return normally
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        # Make get_event_loop raise exception inside try/except
        mock_get_loop.side_effect = Exception("Unexpected error")

        # Create and call callback
        callback = create_notification_callback()
        message = {"event": "reload"}

        # Should not raise - logs error instead
        callback(message)


@pytest.mark.unit
class TestReloadNotificationManagerEdgeCases:
    """Test suite for edge cases."""

    @pytest.mark.asyncio
    async def test_broadcast_with_empty_message(self):
        """Test that broadcast handles empty message."""
        manager = ReloadNotificationManager()
        websocket = AsyncMock()

        await manager.connect(websocket)
        websocket.send_json.reset_mock()

        # Broadcast empty message
        await manager.broadcast({})

        websocket.send_json.assert_called_once_with({})

    @pytest.mark.asyncio
    async def test_broadcast_with_complex_message(self):
        """Test that broadcast handles complex nested message."""
        manager = ReloadNotificationManager()
        websocket = AsyncMock()

        await manager.connect(websocket)
        websocket.send_json.reset_mock()

        # Complex message with nested data
        message = {
            "event": "reload",
            "workflow": "test-workflow",
            "data": {
                "files": ["file1.py", "file2.py"],
                "metadata": {"timestamp": 123456, "version": "1.0"},
            },
        }

        await manager.broadcast(message)

        websocket.send_json.assert_called_once_with(message)

    def test_get_connection_count_is_thread_safe(self):
        """Test that get_connection_count can be called safely."""
        manager = ReloadNotificationManager()

        # Should be safe to call multiple times
        count1 = manager.get_connection_count()
        count2 = manager.get_connection_count()

        assert count1 == count2 == 0

    @pytest.mark.asyncio
    async def test_connect_and_disconnect_same_websocket_multiple_times(self):
        """Test connecting and disconnecting same WebSocket multiple times."""
        manager = ReloadNotificationManager()
        websocket = AsyncMock()

        # Connect
        await manager.connect(websocket)
        assert manager.get_connection_count() == 1

        # Disconnect
        await manager.disconnect(websocket)
        assert manager.get_connection_count() == 0

        # Connect again
        await manager.connect(websocket)
        assert manager.get_connection_count() == 1

        # Disconnect again
        await manager.disconnect(websocket)
        assert manager.get_connection_count() == 0
