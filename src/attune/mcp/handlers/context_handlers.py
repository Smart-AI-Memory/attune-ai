"""Context and attune level handler functions for Attune AI MCP Server.

Handles session context get/set and attune interaction level get/set.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from attune.mcp.server import EmpathyMCPServer

logger = logging.getLogger(__name__)


async def handle_context_get(server: EmpathyMCPServer, args: dict[str, Any]) -> dict[str, Any]:
    """Get session context value.

    Args:
        server: MCP server instance
        args: Must contain key

    """
    key = args["key"]
    value = server._context.get(key)
    return {
        "success": True,
        "key": key,
        "value": value,
        "found": value is not None,
    }


async def handle_context_set(server: EmpathyMCPServer, args: dict[str, Any]) -> dict[str, Any]:
    """Set session context value.

    Args:
        server: MCP server instance
        args: Must contain key and value

    """
    key = args["key"]
    value = args["value"]
    server._context[key] = value
    return {
        "success": True,
        "key": key,
        "value": value,
    }


async def handle_attune_get_level(server: EmpathyMCPServer) -> dict[str, Any]:
    """Get current interaction level."""
    level_names = {
        1: "Reactive",
        2: "Guided",
        3: "Proactive",
        4: "Anticipatory",
        5: "Systems",
    }
    return {
        "success": True,
        "level": server._attune_level,
        "name": level_names.get(server._attune_level, "Unknown"),
        "description": {
            1: "Respond when asked. Minimal proactive guidance.",
            2: "Collaborative exploration with clarifying questions.",
            3: "Act before being asked. Suggest improvements.",
            4: "Predict future needs. Prepare for likely next steps.",
            5: "Build structures that help at scale.",
        }.get(server._attune_level, ""),
    }


async def handle_attune_set_level(server: EmpathyMCPServer, args: dict[str, Any]) -> dict[str, Any]:
    """Set interaction level for this session.

    Args:
        server: MCP server instance
        args: Must contain level (integer 1-5)

    """
    level = args.get("level")
    if not isinstance(level, int) or level < 1 or level > 5:
        return {
            "success": False,
            "error": "Level must be an integer between 1 and 5",
        }

    previous = server._attune_level
    server._attune_level = level

    level_names = {
        1: "Reactive",
        2: "Guided",
        3: "Proactive",
        4: "Anticipatory",
        5: "Systems",
    }

    return {
        "success": True,
        "previous_level": previous,
        "current_level": level,
        "name": level_names[level],
    }
