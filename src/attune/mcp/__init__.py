"""Attune AI MCP Server.

Model Context Protocol integration for Claude Code.
Exposes Empathy workflows, agents, and telemetry as MCP tools.
"""

from attune import __version__

__all__ = ["EmpathyMCPServer", "create_server"]

from attune.mcp.server import EmpathyMCPServer, create_server
