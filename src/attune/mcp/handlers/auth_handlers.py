"""Authentication handler functions for Attune AI MCP Server.

Handles auth status queries and auth mode recommendations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from attune.mcp.server import EmpathyMCPServer

logger = logging.getLogger(__name__)


async def get_auth_status(server: EmpathyMCPServer) -> dict[str, Any]:
    """Get authentication strategy status."""
    from attune.models import AuthStrategy

    strategy = AuthStrategy.load()

    return {
        "success": True,
        "subscription_tier": strategy.subscription_tier.value,
        "default_mode": strategy.default_mode.value,
        "setup_completed": strategy.setup_completed,
    }


async def get_auth_recommend(server: EmpathyMCPServer, args: dict[str, Any]) -> dict[str, Any]:
    """Get authentication recommendation."""
    from pathlib import Path

    from attune.models import (
        count_lines_of_code,
        get_auth_strategy,
        get_module_size_category,
    )

    file_path = Path(args["file_path"])
    lines = count_lines_of_code(file_path)
    category = get_module_size_category(lines)

    strategy = get_auth_strategy()
    recommended = strategy.get_recommended_mode(lines)

    return {
        "success": True,
        "file_path": str(file_path),
        "lines_of_code": lines,
        "category": category,
        "recommended_mode": recommended.value,
    }
