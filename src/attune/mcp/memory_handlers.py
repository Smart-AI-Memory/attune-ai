"""Memory tool handlers for the MCP server.

Extracted from server.py to keep file sizes under 1000 lines.
Provides lazy-init memory access and CRUD operations for
short-term stash and long-term pattern storage.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_MEMORY_NOT_INSTALLED = "attune-ai memory module not installed. " "Run: pip install attune-ai"


class MemoryHandlersMixin:
    """Mixin providing memory tool handlers for EmpathyMCPServer.

    Expects the host class to have a ``_memory`` attribute
    (initialised to ``None``).
    """

    _memory: Any  # Set by host __init__

    # ------------------------------------------------------------------
    # Lazy initialiser
    # ------------------------------------------------------------------

    def _get_memory(self) -> Any:
        """Lazily initialize and return UnifiedMemory instance.

        Returns:
            UnifiedMemory instance

        Raises:
            ImportError: If attune memory module is not available

        """
        if self._memory is None:
            from attune.memory import UnifiedMemory

            self._memory = UnifiedMemory(
                user_id="mcp-session",
                environment="development",
            )
        return self._memory

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    async def _handle_memory_store(self, args: dict[str, Any]) -> dict[str, Any]:
        """Store data in attune-ai memory.

        Args:
            args: Must contain key and value; optional classification
                  and pattern_type.

        Returns:
            Dict with success status and stored key metadata.

        """
        try:
            memory = self._get_memory()
            key = args["key"]
            value = args["value"]
            classification = args.get("classification", "PUBLIC")
            pattern_type = args.get("pattern_type")

            memory.stash(
                key,
                {
                    "value": value,
                    "classification": classification,
                    "pattern_type": pattern_type,
                },
            )

            result: dict[str, Any] = {
                "success": True,
                "key": key,
                "classification": classification,
            }
            if pattern_type:
                try:
                    persist_result = memory.persist_pattern(
                        content=value,
                        pattern_type=pattern_type,
                    )
                    result["pattern_id"] = persist_result.get("pattern_id")
                except Exception as e:  # noqa: BLE001
                    # INTENTIONAL: Pattern persistence is best-effort
                    logger.warning(f"Pattern persistence failed: {e}")

            return result

        except ImportError as e:
            logger.error(f"Memory module not available: {e}")
            return {
                "success": False,
                "error": _MEMORY_NOT_INSTALLED,
            }
        except Exception as e:  # noqa: BLE001
            logger.exception("memory_store failed")
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    async def _handle_memory_retrieve(self, args: dict[str, Any]) -> dict[str, Any]:
        """Retrieve data from attune-ai memory.

        Args:
            args: Must contain key (key or pattern_id).

        Returns:
            Dict with success status, data, and source indicator.

        """
        try:
            memory = self._get_memory()
            key = args["key"]

            data = memory.retrieve(key)
            if data is not None:
                return {"success": True, "key": key, "data": data, "source": "short_term"}

            try:
                pattern = memory.recall_pattern(key)
                if pattern:
                    return {"success": True, "key": key, "data": pattern, "source": "long_term"}
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Pattern recall may fail for non-pattern keys
                pass

            return {"success": True, "key": key, "data": None, "message": "Key not found"}

        except ImportError as e:
            logger.error(f"Memory module not available: {e}")
            return {
                "success": False,
                "error": _MEMORY_NOT_INSTALLED,
            }
        except Exception as e:  # noqa: BLE001
            logger.exception("memory_retrieve failed")
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def _handle_memory_search(self, args: dict[str, Any]) -> dict[str, Any]:
        """Search attune-ai memory for patterns.

        Args:
            args: Must contain query; optional pattern_type filter.

        Returns:
            Dict with success status, results list, and count.

        """
        try:
            memory = self._get_memory()
            query = args["query"]
            pattern_type = args.get("pattern_type")

            results = []
            if hasattr(memory, "search_patterns"):
                results = memory.search_patterns(query, pattern_type=pattern_type)
            elif hasattr(memory, "list_patterns"):
                all_patterns = memory.list_patterns()
                query_lower = query.lower()
                results = [
                    p
                    for p in all_patterns
                    if (
                        query_lower in p.get("content", "").lower()
                        or query_lower in p.get("pattern_type", "").lower()
                        or query_lower in p.get("key", "").lower()
                    )
                    and (pattern_type is None or p.get("pattern_type") == pattern_type)
                ]

            return {"success": True, "query": query, "results": results, "count": len(results)}

        except ImportError as e:
            logger.error(f"Memory module not available: {e}")
            return {
                "success": False,
                "error": _MEMORY_NOT_INSTALLED,
            }
        except Exception as e:  # noqa: BLE001
            logger.exception("memory_search failed")
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Forget
    # ------------------------------------------------------------------

    async def _handle_memory_forget(self, args: dict[str, Any]) -> dict[str, Any]:
        """Remove data from attune-ai memory.

        Args:
            args: Must contain key; optional scope (session/persistent/all).

        Returns:
            Dict with success status and list of scopes removed from.

        """
        try:
            memory = self._get_memory()
            key = args["key"]
            scope = args.get("scope", "all")

            removed_from = []

            if scope in ("session", "all"):
                try:
                    memory.stash(key, None)
                    removed_from.append("session")
                except Exception as e:  # noqa: BLE001
                    # INTENTIONAL: Short-term removal is best-effort
                    logger.debug(f"Short-term removal failed for {key}: {e}")

            if scope in ("persistent", "all"):
                try:
                    if hasattr(memory, "delete_pattern"):
                        memory.delete_pattern(key)
                        removed_from.append("persistent")
                except Exception as e:  # noqa: BLE001
                    # INTENTIONAL: Long-term removal is best-effort
                    logger.debug(f"Long-term removal failed for {key}: {e}")

            return {"success": True, "key": key, "removed_from": removed_from}

        except ImportError as e:
            logger.error(f"Memory module not available: {e}")
            return {
                "success": False,
                "error": _MEMORY_NOT_INSTALLED,
            }
        except Exception as e:  # noqa: BLE001
            logger.exception("memory_forget failed")
            return {"success": False, "error": str(e)}
