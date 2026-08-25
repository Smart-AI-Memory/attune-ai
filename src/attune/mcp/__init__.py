"""Attune AI MCP Server.

Model Context Protocol integration for Claude Code.
Exposes Attune workflows, agents, and telemetry as MCP tools.
"""

from attune import __version__
from attune.mcp.server import AttuneMCPServer, create_server

__all__ = ["AttuneMCPServer", "create_server"]
