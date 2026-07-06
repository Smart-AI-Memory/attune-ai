"""Redis MCP tool definitions and handlers.

Provides 6 MCP tools for Redis Agent Memory Server
operations:

- ``redis_memory_store`` — store to AMS working memory
- ``redis_memory_retrieve`` — get from AMS working memory
- ``redis_memory_search`` — semantic search via long-term
- ``redis_memory_forget`` — delete long-term records by ID
- ``redis_memory_promote`` — promote working to long-term
- ``redis_health_check`` — AMS + Redis health status

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# =========================================================================
# Tool definitions (JSON Schema)
# =========================================================================

TOOL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "redis_memory_store": {
        "name": "redis_memory_store",
        "description": (
            "Store data in Redis Agent Memory Server working memory. "
            "Data is keyed and persisted per-session."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Storage key",
                },
                "value": {
                    "description": "Data to store (any JSON-compatible value)",
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID override (uses default if omitted)",
                },
            },
            "required": ["key", "value"],
        },
    },
    "redis_memory_retrieve": {
        "name": "redis_memory_retrieve",
        "description": ("Retrieve data from Redis Agent Memory Server working memory by key."),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Storage key to retrieve",
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID override (uses default if omitted)",
                },
            },
            "required": ["key"],
        },
    },
    "redis_memory_search": {
        "name": "redis_memory_search",
        "description": (
            "Semantic search over long-term memories in Redis Agent Memory Server. "
            "Uses vector similarity to find relevant past memories."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    "redis_memory_forget": {
        "name": "redis_memory_forget",
        "description": (
            "Delete specific long-term memories from Redis Agent Memory Server "
            "by record ID. IDs come from redis_memory_search results — the "
            "correction path when a stashed finding is wrong or stale."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Record IDs to delete (the `id` field from redis_memory_search results)"
                    ),
                },
            },
            "required": ["ids"],
        },
    },
    "redis_memory_promote": {
        "name": "redis_memory_promote",
        "description": (
            "Promote working memories to long-term storage in Redis Agent Memory Server. "
            "This triggers AMS to extract and persist important information."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session to promote (uses default if omitted)",
                },
            },
            "required": [],
        },
    },
    "redis_health_check": {
        "name": "redis_health_check",
        "description": ("Check Redis Agent Memory Server health and connection status."),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}


# =========================================================================
# Handler functions
# =========================================================================


def _get_backend(server: Any) -> Any:
    """Get or create AMSMemoryBackend from server state.

    Args:
        server: EmpathyMCPServer instance.

    Returns:
        AMSMemoryBackend instance.

    Raises:
        ImportError: If attune-redis is not installed.
    """
    if not hasattr(server, "_redis_backend") or server._redis_backend is None:
        from attune_redis.config import RedisPluginConfig
        from attune_redis.memory import AMSMemoryBackend

        config = RedisPluginConfig.from_env()
        server._redis_backend = AMSMemoryBackend(config=config)
    return server._redis_backend


async def handle_redis_memory_store(server: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Store data in AMS working memory.

    Args:
        server: MCP server instance.
        args: Tool arguments (key, value, session_id).

    Returns:
        Result dict with success status.
    """
    try:
        backend = _get_backend(server)
        key = args["key"]
        value = args["value"]
        session_id = args.get("session_id")

        result = backend.stash(key, value, agent_id=session_id)
        return {
            "success": result,
            "key": key,
            "source": "redis-ams",
        }
    except ImportError:
        return {
            "success": False,
            "error": "Redis support not installed. Run: pip install 'attune-ai[redis]'",
        }
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Graceful degradation for MCP tool errors
        logger.exception("redis_memory_store failed")
        return {"success": False, "error": str(e)}


async def handle_redis_memory_retrieve(server: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Retrieve data from AMS working memory.

    Args:
        server: MCP server instance.
        args: Tool arguments (key, session_id).

    Returns:
        Result dict with value or None.
    """
    try:
        backend = _get_backend(server)
        key = args["key"]
        session_id = args.get("session_id")

        value = backend.retrieve(key, agent_id=session_id)
        return {
            "success": True,
            "key": key,
            "value": value,
            "found": value is not None,
            "source": "redis-ams",
        }
    except ImportError:
        return {
            "success": False,
            "error": "Redis support not installed. Run: pip install 'attune-ai[redis]'",
        }
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Graceful degradation for MCP tool errors
        logger.exception("redis_memory_retrieve failed")
        return {"success": False, "error": str(e)}


async def handle_redis_memory_search(server: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Semantic search over long-term AMS memories.

    Args:
        server: MCP server instance.
        args: Tool arguments (query, limit).

    Returns:
        Result dict with list of matching memories.
    """
    try:
        backend = _get_backend(server)
        query = args["query"]
        limit = args.get("limit", 10)

        results = backend.search(query, limit=limit)
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
            "source": "redis-ams",
        }
    except ImportError:
        return {
            "success": False,
            "error": "Redis support not installed. Run: pip install 'attune-ai[redis]'",
        }
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Graceful degradation for MCP tool errors
        logger.exception("redis_memory_search failed")
        return {"success": False, "error": str(e)}


async def handle_redis_memory_promote(server: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Promote working memories to long-term storage.

    Args:
        server: MCP server instance.
        args: Tool arguments (session_id).

    Returns:
        Result dict with success status.
    """
    try:
        backend = _get_backend(server)
        session_id = args.get("session_id")

        result = backend.promote(session_id=session_id)
        return {
            "success": result,
            "source": "redis-ams",
        }
    except ImportError:
        return {
            "success": False,
            "error": "Redis support not installed. Run: pip install 'attune-ai[redis]'",
        }
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Graceful degradation for MCP tool errors
        logger.exception("redis_memory_promote failed")
        return {"success": False, "error": str(e)}


async def handle_redis_memory_forget(server: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Delete long-term AMS memories by record ID.

    Args:
        server: MCP server instance.
        args: Tool arguments (ids: list of record IDs).

    Returns:
        Result dict with deleted count.
    """
    try:
        backend = _get_backend(server)
        ids = args["ids"]
        if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
            return {"success": False, "error": "ids must be a list of record-ID strings"}

        deleted = backend.forget(ids)
        return {
            "success": deleted > 0 or not ids,
            "requested": len(ids),
            "deleted": deleted,
            "source": "redis-ams",
        }
    except ImportError:
        return {
            "success": False,
            "error": "Redis support not installed. Run: pip install 'attune-ai[redis]'",
        }
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Graceful degradation for MCP tool errors
        logger.exception("redis_memory_forget failed")
        return {"success": False, "error": str(e)}


async def handle_redis_health_check(server: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Check AMS health and connection status.

    Args:
        server: MCP server instance.
        args: Tool arguments (none required).

    Returns:
        Result dict with health info.
    """
    try:
        backend = _get_backend(server)
        connected = backend.is_connected()
        stats = backend.get_stats()
        return {
            "success": True,
            "connected": connected,
            "stats": stats,
            "source": "redis-ams",
        }
    except ImportError:
        return {
            "success": False,
            "error": "Redis support not installed. Run: pip install 'attune-ai[redis]'",
        }
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Graceful degradation for MCP tool errors
        logger.exception("redis_health_check failed")
        return {"success": False, "error": str(e)}


# Handler dispatch table
TOOL_HANDLERS: dict[str, Any] = {
    "redis_memory_store": handle_redis_memory_store,
    "redis_memory_retrieve": handle_redis_memory_retrieve,
    "redis_memory_search": handle_redis_memory_search,
    "redis_memory_forget": handle_redis_memory_forget,
    "redis_memory_promote": handle_redis_memory_promote,
    "redis_health_check": handle_redis_health_check,
}


def register_tools(server: Any) -> None:
    """Register Redis MCP tools on the server.

    Adds tool definitions and wires handler dispatch.

    Args:
        server: EmpathyMCPServer instance.
    """
    server.tools.update(TOOL_DEFINITIONS)

    # Store handler table for dispatch
    if not hasattr(server, "_plugin_handlers"):
        server._plugin_handlers = {}
    server._plugin_handlers.update(TOOL_HANDLERS)

    logger.info(
        "attune-redis: registered %d MCP tools",
        len(TOOL_DEFINITIONS),
    )


__all__ = [
    "TOOL_DEFINITIONS",
    "TOOL_HANDLERS",
    "register_tools",
]
