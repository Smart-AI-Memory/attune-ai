"""Dynamic workflow reloader for hot-reload.

Handles reloading workflow modules without server restart.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import importlib
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ReloadResult:
    """Result of a workflow reload operation."""

    def __init__(
        self,
        success: bool,
        workflow_id: str,
        message: str,
        error: str | None = None,
    ):
        """Initialize reload result.

        Args:
            success: Whether reload succeeded
            workflow_id: ID of workflow that was reloaded
            message: Status message
            error: Error message if failed

        """
        self.success = success
        self.workflow_id = workflow_id
        self.message = message
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "workflow_id": self.workflow_id,
            "message": self.message,
            "error": self.error,
        }


class WorkflowReloader:
    """Handles dynamic reloading of workflow modules.

    Supports hot-reload of workflows without server restart by:
    1. Unloading old module from sys.modules
    2. Reloading module with importlib
    3. Re-registering workflow with workflow API
    4. Notifying clients via callback
    """

    def __init__(
        self,
        register_callback: Callable[[str, type], bool],
        notification_callback: Callable[[dict], None] | None = None,
    ):
        """Initialize reloader.

        Args:
            register_callback: Function to register workflow (workflow_id, workflow_class) -> success
            notification_callback: Optional function to notify clients of reload events

        """
        self.register_callback = register_callback
        self.notification_callback = notification_callback
        self._reload_count = 0

    def reload_workflow(self, workflow_id: str, file_path: str) -> ReloadResult:
        """Reload a workflow module.

        Args:
            workflow_id: Workflow identifier
            file_path: Path to workflow file

        Returns:
            ReloadResult with outcome

        """
        logger.info(f"Attempting to reload workflow: {workflow_id} from {file_path}")

        try:
            # Get module name from file path
            module_name = self._get_module_name(file_path)
            if not module_name:
                error_msg = f"Could not determine module name from {file_path}"
                logger.error(error_msg)
                return ReloadResult(
                    success=False,
                    workflow_id=workflow_id,
                    message="Failed to reload",
                    error=error_msg,
                )

            # Unload old module
            self._unload_module(module_name)

            # Reload module
            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                error_msg = f"Failed to import module {module_name}: {e}"
                logger.error(error_msg)
                self._notify_reload_failed(workflow_id, error_msg)
                return ReloadResult(
                    success=False,
                    workflow_id=workflow_id,
                    message="Import failed",
                    error=error_msg,
                )

            # Find workflow class in module
            workflow_class = self._find_workflow_class(module)
            if not workflow_class:
                error_msg = f"No workflow class found in {module_name}"
                logger.error(error_msg)
                self._notify_reload_failed(workflow_id, error_msg)
                return ReloadResult(
                    success=False,
                    workflow_id=workflow_id,
                    message="No workflow class found",
                    error=error_msg,
                )

            # Re-register workflow
            success = self.register_callback(workflow_id, workflow_class)

            if success:
                self._reload_count += 1
                logger.info(
                    f"✓ Successfully reloaded {workflow_id} ({self._reload_count} total reloads)",
                )
                self._notify_reload_success(workflow_id)

                return ReloadResult(
                    success=True,
                    workflow_id=workflow_id,
                    message=f"Reloaded successfully (reload #{self._reload_count})",
                )
            error_msg = "Registration failed"
            logger.error(f"Failed to re-register {workflow_id}")
            self._notify_reload_failed(workflow_id, error_msg)
            return ReloadResult(
                success=False,
                workflow_id=workflow_id,
                message="Registration failed",
                error=error_msg,
            )

        except Exception as e:  # noqa: BLE001
            error_msg = f"Unexpected error reloading {workflow_id}: {e}"
            logger.exception(error_msg)
            self._notify_reload_failed(workflow_id, str(e))
            return ReloadResult(
                success=False,
                workflow_id=workflow_id,
                message="Unexpected error",
                error=str(e),
            )

    def _get_module_name(self, file_path: str) -> str | None:
        """Get Python module name from file path.

        Args:
            file_path: Path to Python file

        Returns:
            Module name or None if cannot determine

        """
        try:
            path = Path(file_path).resolve()

            # Remove .py extension
            if not path.suffix == ".py":
                return None

            # Get parts relative to project root
            # Try to find common patterns: workflows/, empathy_software_plugin/workflows/
            parts = path.parts

            # Find workflow directory in path
            workflow_dir_indices = [i for i, part in enumerate(parts) if "workflow" in part.lower()]

            if not workflow_dir_indices:
                return None

            # Take from first workflow directory
            start_idx = workflow_dir_indices[0]

            # Build module name
            module_parts = list(parts[start_idx:])
            module_parts[-1] = module_parts[-1].replace(".py", "")

            module_name = ".".join(module_parts)
            return module_name

        except Exception as e:  # noqa: BLE001
            logger.error(f"Error getting module name from {file_path}: {e}")
            return None

    def _unload_module(self, module_name: str) -> None:
        """Unload module from sys.modules.

        Args:
            module_name: Name of module to unload

        """
        # Unload exact module
        if module_name in sys.modules:
            del sys.modules[module_name]
            logger.debug(f"Unloaded module: {module_name}")

        # Also unload any submodules
        submodules = [name for name in sys.modules.keys() if name.startswith(f"{module_name}.")]
        for submodule in submodules:
            del sys.modules[submodule]
            logger.debug(f"Unloaded submodule: {submodule}")

    def _find_workflow_class(self, module: Any) -> type | None:
        """Find workflow class in module.

        Args:
            module: Python module

        Returns:
            Workflow class or None if not found

        """
        # Look for classes ending with "Workflow"
        for name in dir(module):
            if name.endswith("Workflow") and not name.startswith("_"):
                attr = getattr(module, name)
                if isinstance(attr, type):
                    return attr

        return None

    def _notify_reload_success(self, workflow_id: str) -> None:
        """Notify clients of successful reload.

        Args:
            workflow_id: ID of reloaded workflow

        """
        if self.notification_callback:
            try:
                self.notification_callback(
                    {
                        "event": "workflow_reloaded",
                        "workflow_id": workflow_id,
                        "success": True,
                        "reload_count": self._reload_count,
                    },
                )
            except Exception as e:  # noqa: BLE001
                logger.error(f"Error sending reload notification: {e}")

    def _notify_reload_failed(self, workflow_id: str, error: str) -> None:
        """Notify clients of failed reload.

        Args:
            workflow_id: ID of workflow that failed to reload
            error: Error message

        """
        if self.notification_callback:
            try:
                self.notification_callback(
                    {
                        "event": "workflow_reload_failed",
                        "workflow_id": workflow_id,
                        "success": False,
                        "error": error,
                    },
                )
            except Exception as e:  # noqa: BLE001
                logger.error(f"Error sending failure notification: {e}")

    def get_reload_count(self) -> int:
        """Get total number of successful reloads.

        Returns:
            Reload count

        """
        return self._reload_count
