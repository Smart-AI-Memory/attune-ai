"""Redis plugin for the Attune AI framework.

Registers the AMS memory backend and Redis-specific
workflows via the plugin entry-point system.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging

from attune.plugins import BasePlugin, BaseWorkflow, PluginMetadata

logger = logging.getLogger(__name__)


class RedisPlugin(BasePlugin):
    """Redis Agent Memory Server plugin.

    Provides:
    - AMSMemoryBackend implementing MemoryBackend protocol
    - Pub/sub signaling via direct redis-py
    - Redis-specific workflows (Phase 3)
    """

    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata.

        Returns:
            PluginMetadata with Redis plugin details.
        """
        return PluginMetadata(
            name="Attune Redis",
            version="0.1.0",
            domain="redis",
            description=(
                "Redis Agent Memory Server integration. "
                "Provides AMS-backed working memory, "
                "semantic search, and pub/sub signaling."
            ),
            author="Smart AI Memory, LLC",
            license="Apache-2.0",
            requires_core_version="3.5.0",
            dependencies=[
                "agent-memory-client>=0.14.0",
                "redis>=5.0.0",
            ],
        )

    def register_workflows(self) -> dict[str, type[BaseWorkflow]]:
        """Register Redis-specific workflows.

        Returns empty dict for now — workflows will be
        added in Phase 3 (cache planning, key schema
        design, Redis performance debugging).

        Returns:
            Empty dict (Phase 3 placeholder).
        """
        return {}

    def register_mcp_tools(self, server: object) -> None:
        """Register Redis-specific MCP tools.

        Adds 5 tools for AMS operations (store, retrieve,
        search, promote, health check).

        Args:
            server: EmpathyMCPServer instance.
        """
        try:
            from attune_redis.mcp_tools import register_tools

            register_tools(server)
        except ImportError:
            logger.debug("attune-redis: MCP tools not registered (missing deps)")
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: MCP registration is best-effort
            logger.warning("attune-redis: MCP tool registration failed: %s", e)

    def on_activate(self) -> None:
        """Validate plugin dependencies on activation."""
        try:
            import agent_memory_client  # noqa: F401

            logger.info("attune-redis: agent-memory-client available")
        except ImportError:
            logger.warning(
                "attune-redis: agent-memory-client not importable — it is a "
                "core attune-ai dependency, so this means a broken or "
                "partial install. Fix: pip install --force-reinstall attune-ai"
            )


__all__ = ["RedisPlugin"]
