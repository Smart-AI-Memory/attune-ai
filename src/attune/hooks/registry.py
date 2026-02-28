"""Hook Registry

Central registry for managing and dispatching hooks by event type.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
from collections.abc import Callable
from typing import Any

from attune.hooks.config import (
    HookConfig,
    HookDefinition,
    HookEvent,
    HookMatcher,
    HookRule,
    HookType,
)

logger = logging.getLogger(__name__)


class HookRegistry:
    """Central registry for hook management and dispatch.

    The registry handles:
    - Loading hook configuration
    - Matching events to hooks
    - Dispatching hooks to the executor
    - Tracking hook execution results

    Example:
        registry = HookRegistry()
        registry.load_config(config)

        # Register a Python function hook
        registry.register(
            event=HookEvent.SESSION_START,
            handler=my_session_start_handler,
            description="Initialize session state"
        )

        # Fire hooks for an event
        results = await registry.fire(
            HookEvent.SESSION_START,
            context={"session_id": "abc123"}
        )

    """

    def __init__(self, config: HookConfig | None = None):
        """Initialize the hook registry.

        Args:
            config: Optional hook configuration to load

        """
        self.config = config or HookConfig()
        self._python_handlers: dict[str, Callable] = {}
        self._execution_log: list[dict[str, Any]] = []

    def load_config(self, config: HookConfig) -> None:
        """Load or replace hook configuration.

        Args:
            config: New hook configuration

        """
        self.config = config
        logger.info("Loaded hook configuration with %d event types", len(config.hooks))

    def register(
        self,
        event: HookEvent,
        handler: Callable[..., Any],
        description: str = "",
        matcher: HookMatcher | None = None,
        priority: int = 0,
    ) -> str:
        """Register a Python function as a hook handler.

        Args:
            event: Event type to hook
            handler: Python callable to execute
            description: Human-readable description
            matcher: Optional matcher for conditional execution
            priority: Execution priority (higher = earlier)

        Returns:
            Handler ID for later reference

        """
        # Generate unique handler ID
        handler_id = f"{event.value}_{handler.__name__}_{id(handler)}"
        self._python_handlers[handler_id] = handler

        # Create hook definition pointing to the handler
        hook_def = HookDefinition(
            type=HookType.PYTHON,
            command=handler_id,
            description=description,
        )

        self.config.add_hook(
            event=event,
            hook=hook_def,
            matcher=matcher,
            priority=priority,
        )

        logger.debug("Registered hook '%s' for event %s", handler_id, event.value)
        return handler_id

    def unregister(self, handler_id: str) -> bool:
        """Unregister a hook handler by ID.

        Args:
            handler_id: Handler ID returned from register()

        Returns:
            True if handler was found and removed

        """
        if handler_id in self._python_handlers:
            del self._python_handlers[handler_id]
            # Remove from config rules
            for event_rules in self.config.hooks.values():
                for rule in event_rules:
                    rule.hooks = [h for h in rule.hooks if h.command != handler_id]
            logger.debug("Unregistered hook '%s'", handler_id)
            return True
        return False

    def get_matching_hooks(
        self,
        event: HookEvent,
        context: dict[str, Any],
    ) -> list[tuple[HookRule, HookDefinition]]:
        """Get all hooks that match the given event and context.

        Args:
            event: Event type
            context: Event context for matching

        Returns:
            List of (rule, hook) tuples that match

        """
        if not self.config.enabled:
            return []

        matching = []
        for rule in self.config.get_hooks_for_event(event):
            if rule.matcher.matches(context):
                for hook in rule.hooks:
                    matching.append((rule, hook))

        return matching

    async def fire(
        self,
        event: HookEvent,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Fire all matching hooks for an event.

        Args:
            event: Event type to fire
            context: Event context for matching and execution

        Returns:
            List of execution results

        """
        from attune.hooks.executor import HookExecutor

        context = context or {}
        matching_hooks = self.get_matching_hooks(event, context)

        if not matching_hooks:
            logger.debug("No hooks matched for event %s", event.value)
            return []

        logger.info(
            "Firing %d hook(s) for event %s",
            len(matching_hooks),
            event.value,
        )

        executor = HookExecutor(python_handlers=self._python_handlers)
        results = []

        for _rule, hook in matching_hooks:
            try:
                result = await executor.execute(hook, context)
                execution_record = {
                    "event": event.value,
                    "hook": hook.command,
                    "description": hook.description,
                    "success": result.get("success", False),
                    "output": result.get("output"),
                    "error": result.get("error"),
                    "duration_ms": result.get("duration_ms"),
                }
                results.append(execution_record)

                if self.config.log_executions:
                    self._execution_log.append(execution_record)

            except Exception as e:
                error_record = {
                    "event": event.value,
                    "hook": hook.command,
                    "success": False,
                    "error": str(e),
                }
                results.append(error_record)
                logger.error("Hook execution failed: %s - %s", hook.command, e)

                if hook.on_error == "raise":
                    raise

        return results

    def fire_sync(
        self,
        event: HookEvent,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Synchronous version of fire().

        Args:
            event: Event type to fire
            context: Event context

        Returns:
            List of execution results

        """
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, use run_coroutine_threadsafe

            future = asyncio.run_coroutine_threadsafe(
                self.fire(event, context),
                loop,
            )
            return future.result(timeout=self.config.default_timeout)
        except RuntimeError:
            # No running loop, create one
            return asyncio.run(self.fire(event, context))

    def get_execution_log(
        self,
        limit: int = 100,
        event_filter: HookEvent | None = None,
    ) -> list[dict[str, Any]]:
        """Get recent hook execution log entries.

        Args:
            limit: Maximum entries to return
            event_filter: Optional event type filter

        Returns:
            List of execution records

        """
        log = self._execution_log
        if event_filter:
            log = [e for e in log if e.get("event") == event_filter.value]
        return log[-limit:]

    def clear_execution_log(self) -> None:
        """Clear the execution log."""
        self._execution_log.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get hook registry statistics.

        Returns:
            Dictionary with stats

        """
        total_hooks = sum(
            sum(len(rule.hooks) for rule in rules) for rules in self.config.hooks.values()
        )

        executions = len(self._execution_log)
        successes = sum(1 for e in self._execution_log if e.get("success"))

        return {
            "enabled": self.config.enabled,
            "total_hooks": total_hooks,
            "event_types": len([v for v in self.config.hooks.values() if v]),
            "python_handlers": len(self._python_handlers),
            "total_executions": executions,
            "successful_executions": successes,
            "success_rate": (successes / executions * 100) if executions else 0,
        }
