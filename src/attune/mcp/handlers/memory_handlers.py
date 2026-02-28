"""Memory handler functions for Attune AI MCP Server.

Handles memory operations: store, retrieve, search, and forget.
Includes lazy initialization of the UnifiedMemory instance.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from attune.mcp.server import EmpathyMCPServer

logger = logging.getLogger(__name__)


def get_memory(server: EmpathyMCPServer) -> Any:
    """Lazily initialize and return UnifiedMemory instance.

    Args:
        server: MCP server instance holding memory state

    Returns:
        UnifiedMemory instance

    Raises:
        ImportError: If attune memory module is not available

    """
    if server._memory is None:
        from attune.memory import UnifiedMemory

        server._memory = UnifiedMemory(
            user_id="mcp-session",
            environment="development",
        )
    return server._memory


async def handle_memory_store(server: EmpathyMCPServer, args: dict[str, Any]) -> dict[str, Any]:
    """Store data in attune-ai memory.

    Args:
        server: MCP server instance
        args: Must contain key and value; optional classification and pattern_type

    """
    try:
        memory = get_memory(server)
        key = args["key"]
        value = args["value"]
        classification = args.get("classification", "PUBLIC")
        pattern_type = args.get("pattern_type")

        # Use short-term stash for simple key-value storage
        memory.stash(
            key,
            {
                "value": value,
                "classification": classification,
                "pattern_type": pattern_type,
            },
        )

        # If pattern_type is specified, also persist as a long-term pattern
        result: dict[str, Any] = {"success": True, "key": key, "classification": classification}
        if pattern_type:
            try:
                persist_result = memory.persist_pattern(
                    content=value,
                    pattern_type=pattern_type,
                )
                result["pattern_id"] = persist_result.get("pattern_id")
            except Exception as e:
                # INTENTIONAL: Pattern persistence is best-effort
                logger.warning(f"Pattern persistence failed: {e}")

        return result

    except ImportError as e:
        logger.error(f"Memory module not available: {e}")
        return {
            "success": False,
            "error": "attune-ai memory module not installed. Run: pip install attune-ai",
        }
    except Exception as e:
        logger.exception("memory_store failed")
        return {"success": False, "error": str(e)}


async def handle_memory_retrieve(server: EmpathyMCPServer, args: dict[str, Any]) -> dict[str, Any]:
    """Retrieve data from attune-ai memory.

    Args:
        server: MCP server instance
        args: Must contain key (key or pattern_id)

    """
    try:
        memory = get_memory(server)
        key = args["key"]

        # Try short-term first
        data = memory.retrieve(key)
        if data is not None:
            return {"success": True, "key": key, "data": data, "source": "short_term"}

        # Try long-term pattern recall
        try:
            pattern = memory.recall_pattern(key)
            if pattern:
                return {"success": True, "key": key, "data": pattern, "source": "long_term"}
        except Exception:
            # INTENTIONAL: Pattern recall may fail for non-pattern keys
            pass

        return {"success": True, "key": key, "data": None, "message": "Key not found"}

    except ImportError as e:
        logger.error(f"Memory module not available: {e}")
        return {
            "success": False,
            "error": "attune-ai memory module not installed. Run: pip install attune-ai",
        }
    except Exception as e:
        logger.exception("memory_retrieve failed")
        return {"success": False, "error": str(e)}


async def handle_memory_search(server: EmpathyMCPServer, args: dict[str, Any]) -> dict[str, Any]:
    """Search attune-ai memory for patterns.

    Args:
        server: MCP server instance
        args: Must contain query; optional pattern_type filter

    """
    try:
        memory = get_memory(server)
        query = args["query"]
        pattern_type = args.get("pattern_type")

        # Search through available patterns
        results = []
        if hasattr(memory, "search_patterns"):
            results = memory.search_patterns(query, pattern_type=pattern_type)
        elif hasattr(memory, "list_patterns"):
            all_patterns = memory.list_patterns()
            results = [
                p
                for p in all_patterns
                if query.lower() in str(p).lower()
                and (pattern_type is None or p.get("pattern_type") == pattern_type)
            ]

        return {"success": True, "query": query, "results": results, "count": len(results)}

    except ImportError as e:
        logger.error(f"Memory module not available: {e}")
        return {
            "success": False,
            "error": "attune-ai memory module not installed. Run: pip install attune-ai",
        }
    except Exception as e:
        logger.exception("memory_search failed")
        return {"success": False, "error": str(e)}


async def handle_memory_forget(server: EmpathyMCPServer, args: dict[str, Any]) -> dict[str, Any]:
    """Remove data from attune-ai memory.

    Args:
        server: MCP server instance
        args: Must contain key; optional scope (session/persistent/all)

    """
    try:
        memory = get_memory(server)
        key = args["key"]
        scope = args.get("scope", "all")

        removed_from = []

        if scope in ("session", "all"):
            try:
                memory.stash(key, None)  # Clear short-term
                removed_from.append("session")
            except Exception as e:
                # INTENTIONAL: Short-term removal is best-effort
                logger.debug(f"Short-term removal failed for {key}: {e}")

        if scope in ("persistent", "all"):
            try:
                if hasattr(memory, "delete_pattern"):
                    memory.delete_pattern(key)
                    removed_from.append("persistent")
            except Exception as e:
                # INTENTIONAL: Long-term removal is best-effort
                logger.debug(f"Long-term removal failed for {key}: {e}")

        return {"success": True, "key": key, "removed_from": removed_from}

    except ImportError as e:
        logger.error(f"Memory module not available: {e}")
        return {
            "success": False,
            "error": "attune-ai memory module not installed. Run: pip install attune-ai",
        }
    except Exception as e:
        logger.exception("memory_forget failed")
        return {"success": False, "error": str(e)}
