"""File system watcher for workflow hot-reload.

Monitors workflow directories for changes and triggers reloads.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class WorkflowFileHandler(FileSystemEventHandler):
    """Handles file system events for workflow files."""

    def __init__(self, reload_callback: Callable[[str, str], None]):
        """Initialize handler.

        Args:
            reload_callback: Function to call when workflow file changes (workflow_id, file_path)

        """
        super().__init__()
        self.reload_callback = reload_callback
        self._processing: set[str] = set()  # Prevent duplicate events

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events.

        Args:
            event: File system event

        """
        if event.is_directory:
            return

        # Convert file_path to str if it's bytes
        file_path_raw = event.src_path
        file_path = (
            file_path_raw.decode("utf-8") if isinstance(file_path_raw, bytes) else file_path_raw
        )

        # Only process Python files
        if not file_path.endswith(".py"):
            return

        # Skip __pycache__ and test files
        if "__pycache__" in file_path or "test_" in file_path:
            return

        # Prevent duplicate processing
        if file_path in self._processing:
            return

        try:
            self._processing.add(file_path)

            workflow_id = self._extract_workflow_id(file_path)
            if workflow_id:
                logger.info(f"Detected change in {workflow_id} ({file_path})")
                self.reload_callback(workflow_id, file_path)

        except Exception as e:  # noqa: BLE001
            logger.error(f"Error processing file change {file_path}: {e}")
        finally:
            self._processing.discard(file_path)

    def _extract_workflow_id(self, file_path: str) -> str | None:
        """Extract workflow ID from file path.

        Args:
            file_path: Path to workflow file

        Returns:
            Workflow ID or None if cannot extract

        """
        path = Path(file_path)

        # Get filename without extension
        filename = path.stem

        # Remove common suffixes
        workflow_id = filename.replace("_workflow", "").replace("workflow_", "")

        # Convert to workflow ID format (snake_case)
        workflow_id = workflow_id.lower()

        return workflow_id or None


class WorkflowFileWatcher:
    """Watches workflow directories for file changes.

    Monitors specified directories and triggers reload callbacks
    when workflow files are modified.
    """

    def __init__(self, workflow_dirs: list[Path], reload_callback: Callable[[str, str], None]):
        """Initialize watcher.

        Args:
            workflow_dirs: List of directories to watch
            reload_callback: Function to call on file changes (workflow_id, file_path)

        """
        self.workflow_dirs = [Path(d) for d in workflow_dirs]
        self.reload_callback = reload_callback
        self.observer = Observer()
        self.event_handler = WorkflowFileHandler(reload_callback)
        self._running = False

    def start(self) -> None:
        """Start watching workflow directories."""
        if self._running:
            logger.warning("Watcher already running")
            return

        valid_dirs = []
        for directory in self.workflow_dirs:
            if not directory.exists():
                logger.warning(f"Directory does not exist: {directory}")
                continue

            if not directory.is_dir():
                logger.warning(f"Not a directory: {directory}")
                continue

            # Schedule watching
            self.observer.schedule(
                self.event_handler,
                str(directory),
                recursive=True,
            )
            valid_dirs.append(directory)
            logger.info(f"Watching directory: {directory}")

        if not valid_dirs:
            logger.error("No valid directories to watch")
            return

        self.observer.start()
        self._running = True

        logger.info(
            f"Hot-reload enabled for {len(valid_dirs)} "
            f"{'directory' if len(valid_dirs) == 1 else 'directories'}",
        )

    def stop(self) -> None:
        """Stop watching workflow directories."""
        if not self._running:
            return

        self.observer.stop()
        self.observer.join(timeout=5.0)
        self._running = False

        logger.info("Hot-reload watcher stopped")

    def is_running(self) -> bool:
        """Check if watcher is running.

        Returns:
            True if watching, False otherwise

        """
        return self._running

    def __enter__(self) -> WorkflowFileWatcher:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit."""
        self.stop()
