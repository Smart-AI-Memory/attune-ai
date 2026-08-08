"""Hook Executor

Executes hook actions (commands, Python functions, webhooks).

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import asyncio
import importlib
import logging
import shlex
import time
from collections.abc import Callable
from typing import Any

from attune.hooks.config import HookDefinition, HookType

logger = logging.getLogger(__name__)


class HookExecutor:
    """Executor for running hook actions.

    Supports three hook types:
    - COMMAND: Run shell commands with variable substitution
    - PYTHON: Import and call Python functions
    - WEBHOOK: POST to webhook URLs

    Example:
        executor = HookExecutor()

        # Execute a command hook
        result = await executor.execute(
            HookDefinition(type=HookType.COMMAND, command="echo {file_path}"),
            context={"file_path": "/path/to/file.py"}
        )

    """

    def __init__(self, python_handlers: dict[str, Callable] | None = None):
        """Initialize the executor.

        Args:
            python_handlers: Map of handler IDs to Python callables

        """
        self._python_handlers = python_handlers or {}

    async def execute(
        self,
        hook: HookDefinition,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a hook action.

        Args:
            hook: Hook definition to execute
            context: Execution context with variables

        Returns:
            Execution result dictionary

        """
        start_time = time.time()

        try:
            if hook.async_execution:
                # Fire and forget
                asyncio.create_task(self._execute_internal(hook, context))
                return {
                    "success": True,
                    "output": "Hook scheduled for async execution",
                    "async": True,
                    "duration_ms": 0,
                }

            result = await asyncio.wait_for(
                self._execute_internal(hook, context),
                timeout=hook.timeout,
            )

            duration_ms = (time.time() - start_time) * 1000
            return {
                "success": True,
                "output": result,
                "duration_ms": round(duration_ms, 2),
            }

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Hook timed out after {hook.timeout}s"
            logger.warning("%s: %s", error_msg, hook.command)
            return {
                "success": False,
                "error": error_msg,
                "duration_ms": round(duration_ms, 2),
            }

        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Hooks must not crash the caller — return error dict
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Hook execution failed: %s - %s", hook.command, e)
            return {
                "success": False,
                "error": str(e),
                "duration_ms": round(duration_ms, 2),
            }

    async def _execute_internal(
        self,
        hook: HookDefinition,
        context: dict[str, Any],
    ) -> Any:
        """Internal execution logic.

        Args:
            hook: Hook definition
            context: Execution context

        Returns:
            Hook output

        """
        if hook.type == HookType.COMMAND:
            return await self._execute_command(hook.command, context)
        if hook.type == HookType.PYTHON:
            return await self._execute_python(hook.command, context)
        if hook.type == HookType.WEBHOOK:
            return await self._execute_webhook(hook.command, context)
        raise ValueError(f"Unknown hook type: {hook.type}")

    async def _execute_command(
        self,
        command: str,
        context: dict[str, Any],
    ) -> str:
        """Execute a shell command.

        Args:
            command: Command string with optional {var} placeholders
            context: Variables for substitution

        Returns:
            Command output

        """
        # Tokenize the TEMPLATE first, then substitute per token — a
        # context value containing spaces or quotes stays ONE argv
        # token instead of injecting extra arguments/flags.
        try:
            cmd_args = [token.format(**context) for token in shlex.split(command)]
        except KeyError as e:
            raise ValueError(f"Missing context variable for command: {e}") from e

        logger.debug("Executing command: %s", cmd_args)

        # Run command asynchronously (use exec to prevent shell injection)
        process = await asyncio.create_subprocess_exec(
            *cmd_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_output = stderr.decode().strip() or stdout.decode().strip()
            raise RuntimeError(
                f"Command failed with exit code {process.returncode}: {error_output}",
            )

        return stdout.decode().strip()

    async def _execute_python(
        self,
        command: str,
        context: dict[str, Any],
    ) -> Any:
        """Execute a Python function.

        Args:
            command: Either a handler ID or module.path:function format
            context: Context passed as kwargs to function

        Returns:
            Function return value

        """
        # Check if it's a registered handler ID
        if command in self._python_handlers:
            handler = self._python_handlers[command]
            return await self._call_handler(handler, context)

        # Otherwise, import module:function
        if ":" not in command:
            raise ValueError(f"Python hook must be 'module.path:function' format: {command}")

        module_path, func_name = command.rsplit(":", 1)

        # Security: only allow importing from attune.* modules
        _ALLOWED_MODULE_PREFIXES = ("attune.",)
        if not any(module_path.startswith(p) for p in _ALLOWED_MODULE_PREFIXES):
            raise ValueError(
                f"Module '{module_path}' not in allowed prefixes: "
                f"{_ALLOWED_MODULE_PREFIXES}. Register it in "
                f"_python_handlers instead."
            )

        try:
            module = importlib.import_module(module_path)
            handler = getattr(module, func_name)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Failed to import hook function: {command}") from e

        return await self._call_handler(handler, context)

    async def _call_handler(
        self,
        handler: Callable,
        context: dict[str, Any],
    ) -> Any:
        """Call a handler function (sync or async).

        Args:
            handler: Callable to invoke
            context: Context passed as kwargs

        Returns:
            Handler return value

        """
        if asyncio.iscoroutinefunction(handler):
            return await handler(**context)
        # Run sync function in thread pool
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: handler(**context))

    async def _execute_webhook(
        self,
        url: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a webhook call.

        Args:
            url: Webhook URL
            context: JSON payload to send

        Returns:
            Response data

        """
        import socket
        import urllib.parse

        from attune.monitoring.validators import _validate_webhook_url, resolve_pinned_ip

        url = _validate_webhook_url(url)
        # Pin the vetted IP so the request-time connection can't be
        # swapped to a private address by a second DNS resolution
        # (rebinding TOCTOU) — same guard as monitoring/notifications.
        hostname = urllib.parse.urlparse(url).hostname or ""
        pinned_ip = resolve_pinned_ip(hostname)

        try:
            import aiohttp
        except ImportError:
            raise ImportError("aiohttp required for webhook hooks: pip install aiohttp") from None

        logger.debug("Calling webhook: %s", url)

        pinned_family = socket.AF_INET6 if ":" in pinned_ip else socket.AF_INET

        class _PinnedResolver(aiohttp.abc.AbstractResolver):
            """Resolve every lookup to the pre-vetted IP.

            TLS still verifies against the original hostname (aiohttp
            passes it as server_hostname); only the connect target is
            pinned.
            """

            async def resolve(
                self, host: str, port: int = 0, family: int = socket.AF_INET
            ) -> list[dict[str, Any]]:
                return [
                    {
                        "hostname": host,
                        "host": pinned_ip,
                        "port": port,
                        "family": pinned_family,
                        "proto": 0,
                        "flags": 0,
                    }
                ]

            async def close(self) -> None:
                return None

        connector = aiohttp.TCPConnector(resolver=_PinnedResolver(), use_dns_cache=False)
        async with (
            aiohttp.ClientSession(connector=connector) as session,
            session.post(
                url,
                json=context,
                headers={"Content-Type": "application/json"},
            ) as response,
        ):
            if response.status >= 400:
                text = await response.text()
                raise RuntimeError(f"Webhook failed with status {response.status}: {text}")

            try:
                return await response.json()
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Graceful fallback when response isn't valid JSON
                return {"status": response.status, "text": await response.text()}


class HookExecutorSync:
    """Synchronous wrapper for HookExecutor.

    For use in contexts where async is not available.
    """

    def __init__(self, python_handlers: dict[str, Callable] | None = None):
        """Initialize synchronous hook executor wrapper.

        Args:
            python_handlers: Optional mapping of handler names to callables.
        """
        self._executor = HookExecutor(python_handlers)

    def execute(
        self,
        hook: HookDefinition,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a hook synchronously.

        Args:
            hook: Hook definition
            context: Execution context

        Returns:
            Execution result

        """
        return asyncio.run(self._executor.execute(hook, context))
