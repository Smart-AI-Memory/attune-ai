"""Integration example for hot-reload with workflow API.

Shows how to integrate hot-reload into the existing workflow_api.py.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
from collections.abc import Callable

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .config import get_hot_reload_config
from .reloader import WorkflowReloader
from .watcher import WorkflowFileWatcher
from .websocket import create_notification_callback, get_notification_manager

logger = logging.getLogger(__name__)


class HotReloadIntegration:
    """Integrates hot-reload with workflow API.

    Example usage in workflow_api.py:

        from hot_reload.integration import HotReloadIntegration

        # Create FastAPI app
        app = FastAPI()

        # Initialize hot-reload (if enabled)
        hot_reload = HotReloadIntegration(app, register_workflow)

        @app.on_event("startup")
        async def startup_event():
            init_workflows()  # Initialize workflows
            hot_reload.start()  # Start hot-reload watcher

        @app.on_event("shutdown")
        async def shutdown_event():
            hot_reload.stop()

    """

    def __init__(
        self,
        app: FastAPI,
        register_callback: Callable[[str, type], bool],
    ):
        """Initialize hot-reload integration.

        Args:
            app: FastAPI application instance
            register_callback: Function to register workflow (workflow_id, workflow_class) -> bool

        """
        self.app = app
        self.register_callback = register_callback
        self.config = get_hot_reload_config()

        # Initialize components
        self.notification_callback = create_notification_callback()
        self.reloader = WorkflowReloader(
            register_callback=self._register_workflow_wrapper,
            notification_callback=self.notification_callback,
        )

        self.watcher: WorkflowFileWatcher | None = None

        # Add WebSocket endpoint to app
        if self.config.enabled:
            self._setup_websocket_endpoint()

    def _register_workflow_wrapper(self, workflow_id: str, workflow_class: type) -> bool:
        """Wrapper for register callback that handles errors.

        Args:
            workflow_id: Workflow identifier
            workflow_class: Workflow class to register

        Returns:
            True if registration succeeded

        """
        try:
            return self.register_callback(workflow_id, workflow_class)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error registering workflow {workflow_id}: {e}")
            return False

    def _setup_websocket_endpoint(self) -> None:
        """Add WebSocket endpoint to FastAPI app."""

        @self.app.websocket(self.config.websocket_path)
        async def hot_reload_websocket(websocket: WebSocket):
            """WebSocket endpoint for hot-reload notifications."""
            manager = get_notification_manager()

            await manager.connect(websocket)

            try:
                # Keep connection alive
                while True:
                    # Receive ping messages
                    await websocket.receive_text()

            except WebSocketDisconnect:
                await manager.disconnect(websocket)
            except Exception as e:  # noqa: BLE001
                logger.error(f"WebSocket error: {e}")
                await manager.disconnect(websocket)

        logger.info(f"WebSocket endpoint added: {self.config.websocket_path}")

    def start(self) -> None:
        """Start hot-reload watcher."""
        if not self.config.enabled:
            logger.info("Hot-reload disabled (set HOT_RELOAD_ENABLED=true to enable)")
            return

        if not self.config.watch_dirs:
            logger.warning("No workflow directories found to watch")
            return

        if self.watcher and self.watcher.is_running():
            logger.warning("Hot-reload already started")
            return

        # Create watcher
        self.watcher = WorkflowFileWatcher(
            workflow_dirs=self.config.watch_dirs,
            reload_callback=self._on_file_change,
        )

        # Start watching
        self.watcher.start()

        logger.info(f"🔥 Hot-reload started - watching {len(self.config.watch_dirs)} directories")

    def stop(self) -> None:
        """Stop hot-reload watcher."""
        if self.watcher:
            self.watcher.stop()
            self.watcher = None
            logger.info("Hot-reload stopped")

    def _on_file_change(self, workflow_id: str, file_path: str) -> None:
        """Handle file change event.

        Args:
            workflow_id: ID of workflow that changed
            file_path: Path to changed file

        """
        logger.info(f"File change detected: {workflow_id} ({file_path})")

        # Reload workflow
        result = self.reloader.reload_workflow(workflow_id, file_path)

        if result.success:
            logger.info(f"✓ {result.message}")
        else:
            logger.error(f"✗ Reload failed: {result.error}")

    def get_status(self) -> dict:
        """Get hot-reload status.

        Returns:
            Status dictionary

        """
        return {
            "enabled": self.config.enabled,
            "running": self.watcher.is_running() if self.watcher else False,
            "watch_dirs": [str(d) for d in self.config.watch_dirs],
            "reload_count": self.reloader.get_reload_count(),
            "websocket_connections": get_notification_manager().get_connection_count(),
            "websocket_path": self.config.websocket_path,
        }


# Example usage in workflow_api.py:
"""
from fastapi import FastAPI
from hot_reload.integration import HotReloadIntegration

app = FastAPI(title="Empathy Workflow API")

# Global hot-reload instance
hot_reload = None


def register_workflow(workflow_id: str, workflow_class: type, *args, **kwargs) -> bool:
    '''Register workflow with WORKFLOWS dict'''
    try:
        WORKFLOWS[workflow_id] = workflow_class(*args, **kwargs)
        logger.info(f"✓ Registered workflow: {workflow_id}")
        return True
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to register {workflow_id}: {e}")
        return False


@app.on_event("startup")
async def startup_event():
    global hot_reload

    # Initialize workflows
    init_workflows()

    # Start hot-reload
    hot_reload = HotReloadIntegration(app, register_workflow)
    hot_reload.start()


@app.on_event("shutdown")
async def shutdown_event():
    if hot_reload:
        hot_reload.stop()


@app.get("/api/hot-reload/status")
async def get_hot_reload_status():
    '''Get hot-reload status'''
    if not hot_reload:
        return {"enabled": False}
    return hot_reload.get_status()
"""
