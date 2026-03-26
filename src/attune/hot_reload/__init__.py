"""Hot-Reload Infrastructure for Workflow Factory.

Enables real-time workflow reloading during development without server restarts.

Features:
- File system monitoring with watchdog
- Dynamic module reloading
- WebSocket notifications to frontend
- Graceful error handling
- Development mode toggle

Usage:
    from hot_reload.integration import HotReloadIntegration

    app = FastAPI()
    hot_reload = HotReloadIntegration(app, register_workflow)

    @app.on_event("startup")
    async def startup():
        hot_reload.start()

    @app.on_event("shutdown")
    async def shutdown():
        hot_reload.stop()

Environment Variables:
    HOT_RELOAD_ENABLED: Enable hot-reload (default: false)
    HOT_RELOAD_WATCH_DIRS: Comma-separated directories to watch
    HOT_RELOAD_WS_PATH: WebSocket path (default: /ws/hot-reload)
    HOT_RELOAD_DELAY: Reload delay in seconds (default: 0.5)

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from .config import HotReloadConfig, get_hot_reload_config
from .integration import HotReloadIntegration
from .reloader import ReloadResult, WorkflowReloader
from .watcher import WorkflowFileWatcher
from .websocket import (
    ReloadNotificationManager,
    create_notification_callback,
    get_notification_manager,
)

__all__ = [
    # Core components
    "WorkflowFileWatcher",
    "WorkflowReloader",
    "ReloadResult",
    # WebSocket
    "ReloadNotificationManager",
    "get_notification_manager",
    "create_notification_callback",
    # Config
    "HotReloadConfig",
    "get_hot_reload_config",
    # Integration
    "HotReloadIntegration",
]

from attune import __version__
