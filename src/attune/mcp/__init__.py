"""Attune AI MCP Server.

Model Context Protocol integration for Claude Code.
Exposes Attune workflows, agents, and telemetry as MCP tools.
"""

from typing import Any

from attune import __version__
from attune.mcp.server import AttuneMCPServer, create_server

__all__ = ["AttuneMCPServer", "EmpathyMCPServer", "create_server"]


def __getattr__(name: str) -> Any:
    """Serve the retired ``EmpathyMCPServer`` name with a deprecation warning."""
    if name == "EmpathyMCPServer":
        # Delegates to attune.mcp.server.__getattr__, which emits the
        # DeprecationWarning (alias removed in 15.0.0).
        from attune.mcp import server

        return server.EmpathyMCPServer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
