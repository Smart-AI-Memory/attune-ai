"""Redis MCP tool definitions and handlers.

Provides 6 MCP tools for Redis Agent Memory Server
operations:

- ``redis_memory_store`` — store to AMS working memory
- ``redis_memory_retrieve`` — get from AMS working memory
- ``redis_memory_search`` — semantic search via long-term
- ``redis_memory_forget`` — delete long-term records by ID
- ``redis_memory_promote`` — promote working to long-term
- ``redis_health_check`` — AMS + Redis health status

Plus 5 conditional ``session_memory_*`` tools (registered only when
``attune.memory.session_stash`` is importable) that carry the full
session-stash contract — PII/secrets sanitization before write,
cwd soft-priority, and the 30-day working TTL — over MCP for
sandboxed clients (cross-provider-memory-transport R4/D3):

- ``session_memory_capture`` — sanitized finding capture
- ``session_memory_recall`` — semantic recall of stashed findings
- ``session_memory_recent`` — query-less recency recall
- ``session_memory_forget`` — precise deletion by record ID
- ``session_memory_status`` — caller-scoped backend status

The ``redis_memory_*`` tools remain generic working-memory
operations with frozen schemas (D6); finding capture must use
``session_memory_capture``, never raw ``redis_memory_store`` (CR-2).

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# redis + agent-memory-client are CORE attune-ai dependencies, so an
# ImportError here means a broken or partial environment — never a
# missing extra. Do NOT point users at an extras install: the [redis]
# extra was an empty alias (deleted 2026-07-17, #1418) and suggesting
# it was the #758 no-op-remediation trap.
_REDIS_MISSING_ERROR = (
    "Redis client libraries are not importable. They ship with attune-ai "
    "core, so this indicates a broken or partial install. "
    "Fix: pip install --force-reinstall attune-ai  "
    "(in a uv-managed dev checkout: uv sync)"
)

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


# Session-memory adapters (cross-provider-memory-transport T2). Kept in a
# SEPARATE dict so the 6 redis_memory_* schemas above stay frozen (D6) and
# registration can be conditional on attune core being importable.
_SESSION_RECALL_MAX = 20

SESSION_MEMORY_TOOL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "session_memory_capture": {
        "name": "session_memory_capture",
        "description": (
            "Capture a cross-session finding through the session-stash "
            "contract: PII/secrets sanitization before write, cwd tagging "
            "for scoped recall, and a 30-day working TTL. Use this for "
            "findings — never raw redis_memory_store."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The finding text (truncated to 500 chars)",
                },
                "type": {
                    "type": "string",
                    "enum": ["decision", "pattern", "bug", "reference", "note"],
                    "description": "Entry kind (default: note)",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Free-form tags for filtering",
                },
                "session_id": {
                    "type": "string",
                    "description": "Originating session id (default: mcp)",
                },
                "cwd": {
                    "type": "string",
                    "description": ("Project root for cwd-scoped recall (default: workspace root)"),
                },
            },
            "required": ["content"],
        },
    },
    "session_memory_recall": {
        "name": "session_memory_recall",
        "description": (
            "Semantic recall over stashed cross-session findings. "
            "Same-cwd findings rank first when cwd is given."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language recall query",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Max results (default 5, max 20)",
                    "default": 5,
                },
                "cwd": {
                    "type": "string",
                    "description": "Prefer entries from this project root",
                },
            },
            "required": ["query"],
        },
    },
    "session_memory_recent": {
        "name": "session_memory_recent",
        "description": ("Query-less recall of the most recently stashed findings (newest first)."),
        "input_schema": {
            "type": "object",
            "properties": {
                "top_k": {
                    "type": "integer",
                    "description": "Max results (default 5, max 20)",
                    "default": 5,
                },
                "cwd": {
                    "type": "string",
                    "description": "Prefer entries from this project root",
                },
            },
            "required": [],
        },
    },
    "session_memory_forget": {
        "name": "session_memory_forget",
        "description": (
            "Delete stashed findings by record ID (the `id` field from "
            "session_memory_recall/recent results) — the correction path "
            "when a finding is wrong or stale."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Record IDs to delete",
                },
                "cwd": {
                    "type": "string",
                    "description": "Project root recorded on the feedback event",
                },
            },
            "required": ["ids"],
        },
    },
    "session_memory_status": {
        "name": "session_memory_status",
        "description": (
            "Caller-scoped session-memory status: resolved backend, "
            "reachability for THIS caller, and a stable failure reason "
            "when writes would not succeed."
        ),
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
            "error": _REDIS_MISSING_ERROR,
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
            "error": _REDIS_MISSING_ERROR,
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
            "error": _REDIS_MISSING_ERROR,
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
            "error": _REDIS_MISSING_ERROR,
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
            "error": _REDIS_MISSING_ERROR,
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
            "error": _REDIS_MISSING_ERROR,
        }
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Graceful degradation for MCP tool errors
        logger.exception("redis_health_check failed")
        return {"success": False, "error": str(e)}


# =========================================================================
# Session-memory handlers (delegate to attune.memory.session_stash)
# =========================================================================


def _session_stash() -> Any:
    """Import the session_stash module (raises ImportError when absent)."""
    from attune.memory import session_stash

    return session_stash


def _stash_failure_reason(session_stash: Any) -> str:
    """Map a False write result to a stable machine-readable code (CR-5).

    Prefers the caller-scoped ``backend_status()`` reason (e.g.
    ``no_backend``, ``file_write_denied``); falls back to the generic
    ``write_failed`` when status reports healthy but the write still
    failed (e.g. sanitizer unavailable or a backend error).
    """
    try:
        status = session_stash.backend_status()
    except Exception:  # noqa: BLE001
        # INTENTIONAL: reason derivation is best-effort diagnostics.
        return "write_failed"
    reason = status.get("reason") if isinstance(status, dict) else None
    return str(reason) if reason else "write_failed"


def _clamp_top_k(args: dict[str, Any]) -> int:
    """Bound recall result counts (R4: results bounded)."""
    try:
        top_k = int(args.get("top_k", 5))
    except (TypeError, ValueError):
        return 5
    return max(1, min(top_k, _SESSION_RECALL_MAX))


async def handle_session_memory_capture(server: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Capture a finding through the sanitizing session-stash contract.

    Args:
        server: MCP server instance (supplies the default cwd).
        args: Tool arguments (content, type, tags, session_id, cwd).

    Returns:
        ``{ok: true, id: ...}`` on a durable write, else
        ``{ok: false, reason: <stable_code>}`` — a False Python result
        is never reported as success (R1/CR-5).
    """
    try:
        session_stash = _session_stash()
        cwd = args.get("cwd") or getattr(server, "_workspace_root", None) or ""
        try:
            entry = session_stash.SessionStashEntry.create(
                session_id=str(args.get("session_id") or "mcp"),
                cwd=str(cwd),
                type=str(args.get("type") or "note"),
                content=args.get("content", ""),
                tags=args.get("tags"),
            )
        except ValueError as exc:
            return {
                "ok": False,
                "reason": "invalid_entry",
                "error": str(exc),
                "source": "session-stash",
            }
        if session_stash.stash_entry(entry):
            return {
                "ok": True,
                "id": entry.id,
                "type": entry.type,
                "source": "session-stash",
            }
        return {
            "ok": False,
            "reason": _stash_failure_reason(session_stash),
            "source": "session-stash",
        }
    except ImportError:
        return {"ok": False, "reason": "session_stash_unavailable", "source": "session-stash"}
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Graceful degradation for MCP tool errors
        logger.exception("session_memory_capture failed")
        return {"ok": False, "reason": "internal_error", "error": str(e)}


async def handle_session_memory_recall(server: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Semantic recall over stashed findings.

    Args:
        server: MCP server instance (unused; uniform signature).
        args: Tool arguments (query, top_k, cwd).

    Returns:
        Result dict with ranked records (empty when degraded).
    """
    try:
        session_stash = _session_stash()
        results = session_stash.recall_entries(
            str(args.get("query", "")),
            top_k=_clamp_top_k(args),
            cwd=args.get("cwd"),
        )
        return {
            "ok": True,
            "results": results,
            "count": len(results),
            "source": "session-stash",
        }
    except ImportError:
        return {"ok": False, "reason": "session_stash_unavailable", "source": "session-stash"}
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Graceful degradation for MCP tool errors
        logger.exception("session_memory_recall failed")
        return {"ok": False, "reason": "internal_error", "error": str(e)}


async def handle_session_memory_recent(server: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Query-less recency recall of stashed findings.

    Args:
        server: MCP server instance (unused; uniform signature).
        args: Tool arguments (top_k, cwd).

    Returns:
        Result dict with newest-first records (empty when degraded).
    """
    try:
        session_stash = _session_stash()
        results = session_stash.recent_entries(
            top_k=_clamp_top_k(args),
            cwd=args.get("cwd"),
        )
        return {
            "ok": True,
            "results": results,
            "count": len(results),
            "source": "session-stash",
        }
    except ImportError:
        return {"ok": False, "reason": "session_stash_unavailable", "source": "session-stash"}
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Graceful degradation for MCP tool errors
        logger.exception("session_memory_recent failed")
        return {"ok": False, "reason": "internal_error", "error": str(e)}


async def handle_session_memory_forget(server: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Delete stashed findings by record ID.

    Args:
        server: MCP server instance (unused; uniform signature).
        args: Tool arguments (ids, cwd).

    Returns:
        Result dict with requested/deleted counts; ``ok`` is False with a
        stable reason when nothing could be deleted for a non-empty request.
    """
    try:
        session_stash = _session_stash()
        ids = args.get("ids")
        if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
            return {
                "ok": False,
                "reason": "invalid_entry",
                "error": "ids must be a list of record-ID strings",
                "source": "session-stash",
            }
        deleted = session_stash.forget_entries(
            ids,
            source="mcp_forget",
            cwd=args.get("cwd"),
        )
        result: dict[str, Any] = {
            "ok": deleted > 0 or not ids,
            "requested": len(ids),
            "deleted": deleted,
            "source": "session-stash",
        }
        if not result["ok"]:
            result["reason"] = _stash_failure_reason(session_stash)
            if result["reason"] == "write_failed":
                result["reason"] = "not_found"
        return result
    except ImportError:
        return {"ok": False, "reason": "session_stash_unavailable", "source": "session-stash"}
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Graceful degradation for MCP tool errors
        logger.exception("session_memory_forget failed")
        return {"ok": False, "reason": "internal_error", "error": str(e)}


async def handle_session_memory_status(server: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Caller-scoped session-memory status.

    Reports ``transport: "mcp"`` at this layer (the adapter executes
    host-side); the underlying Python-layer transport moves to
    ``backend_transport`` (cross-provider-memory-transport D4).

    Args:
        server: MCP server instance (unused; uniform signature).
        args: Tool arguments (none).

    Returns:
        The ``backend_status()`` dict with the MCP layering applied.
    """
    try:
        session_stash = _session_stash()
        status = dict(session_stash.backend_status())
        status["backend_transport"] = status.get("transport")
        status["transport"] = "mcp"
        status["source"] = "session-stash"
        return status
    except ImportError:
        return {
            "ok": False,
            "reason": "session_stash_unavailable",
            "transport": "mcp",
            "source": "session-stash",
        }
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Graceful degradation for MCP tool errors
        logger.exception("session_memory_status failed")
        return {"ok": False, "reason": "internal_error", "error": str(e)}


SESSION_MEMORY_TOOL_HANDLERS: dict[str, Any] = {
    "session_memory_capture": handle_session_memory_capture,
    "session_memory_recall": handle_session_memory_recall,
    "session_memory_recent": handle_session_memory_recent,
    "session_memory_forget": handle_session_memory_forget,
    "session_memory_status": handle_session_memory_status,
}


def _session_memory_available() -> bool:
    """True when attune core's session_stash can back the adapters."""
    try:
        _session_stash()
    except ImportError:
        return False
    return True


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

    registered = len(TOOL_DEFINITIONS)
    # Session-memory adapters need attune core's session_stash; skip them
    # cleanly in a partial environment rather than registering tools that
    # can only fail (cross-provider-memory-transport T2).
    if _session_memory_available():
        server.tools.update(SESSION_MEMORY_TOOL_DEFINITIONS)
        server._plugin_handlers.update(SESSION_MEMORY_TOOL_HANDLERS)
        registered += len(SESSION_MEMORY_TOOL_DEFINITIONS)
    else:
        logger.warning(
            "attune-redis: session_memory_* tools skipped (attune.memory.session_stash not importable)"
        )

    logger.info(
        "attune-redis: registered %d MCP tools",
        registered,
    )


__all__ = [
    "SESSION_MEMORY_TOOL_DEFINITIONS",
    "SESSION_MEMORY_TOOL_HANDLERS",
    "TOOL_DEFINITIONS",
    "TOOL_HANDLERS",
    "register_tools",
]
