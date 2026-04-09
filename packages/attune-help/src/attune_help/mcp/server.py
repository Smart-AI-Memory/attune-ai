"""attune-help MCP server.

Exposes the attune-help library as MCP tools for Claude
Code and other MCP clients. Uses the official MCP Python
SDK (mcp.server.Server) for protocol compliance.

Run with:
    python -m attune_help.mcp.server
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from attune_help import __version__
from attune_help.mcp.handlers import AttuneHelpHandlers
from attune_help.mcp.tool_schemas import get_tools

logger = logging.getLogger(__name__)


class AttuneHelpMCPServer:
    """MCP server for attune-help.

    Wraps AttuneHelpHandlers and exposes 6 tools through
    the MCP stdio transport.
    """

    def __init__(self, workspace_root: str | None = None) -> None:
        """Initialize the server.

        Args:
            workspace_root: Root directory for path containment.
                Defaults to the current working directory.
        """
        self._workspace_root = workspace_root or os.getcwd()
        self._handlers = AttuneHelpHandlers(self._workspace_root)
        self._tools = get_tools()
        self._dispatch = self._build_dispatch()
        logger.info(
            "AttuneHelpMCPServer initialized " "(workspace=%s, tools=%d, version=%s)",
            self._workspace_root,
            len(self._tools),
            __version__,
        )

    def _build_dispatch(self) -> dict[str, Any]:
        """Build tool name -> async handler mapping."""
        return {
            "lookup_topic": self._handlers.lookup_topic,
            "lookup_list": self._handlers.lookup_list,
            "lookup_warn": self._handlers.lookup_warn,
            "lookup_preamble": self._handlers.lookup_preamble,
            "lookup_reset": self._handlers.lookup_reset,
            "lookup_status": self._handlers.lookup_status,
        }

    @property
    def tools(self) -> dict[str, dict[str, Any]]:
        """Tool schema registry."""
        return self._tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Dispatch a tool call to the registered handler.

        Args:
            tool_name: Name of the tool to invoke.
            arguments: Tool arguments dict.

        Returns:
            Handler result dict (always includes 'success' key).
        """
        handler = self._dispatch.get(tool_name)
        if handler is None:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
            }

        try:
            return await handler(arguments)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: catch-all so the server stays alive
            # across individual tool failures; the error is
            # returned to the client instead of crashing stdio.
            logger.exception("Tool execution failed: %s", tool_name)
            return {
                "success": False,
                "error": f"Tool execution failed: {type(e).__name__}: {e}",
            }


# -- MCP SDK wiring --------------------------------------------------
# The Server instance and decorators below delegate to the singleton
# AttuneHelpMCPServer above. Keeping the SDK glue separate makes the
# application class testable without an MCP transport.

_mcp_server = Server("attune-help")
_app: AttuneHelpMCPServer | None = None


def _get_app() -> AttuneHelpMCPServer:
    """Lazily create the server singleton."""
    global _app  # noqa: PLW0603
    if _app is None:
        _app = AttuneHelpMCPServer()
    return _app


@_mcp_server.list_tools()
async def _handle_list_tools() -> list[Tool]:
    """Return all registered tools to the MCP client."""
    app = _get_app()
    return [
        Tool(
            name=name,
            description=defn.get("description", ""),
            inputSchema=defn.get(
                "input_schema",
                {"type": "object", "properties": {}},
            ),
        )
        for name, defn in app.tools.items()
    ]


@_mcp_server.call_tool()
async def _handle_call_tool(
    name: str,
    arguments: dict[str, Any] | None = None,
) -> list[TextContent]:
    """Dispatch a tool call from the MCP client."""
    app = _get_app()
    result = await app.call_tool(name, arguments or {})
    return [
        TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str),
        ),
    ]


# -- Public helpers --------------------------------------------------


def create_server() -> AttuneHelpMCPServer:
    """Create and return a fresh AttuneHelpMCPServer."""
    return AttuneHelpMCPServer()


async def _run_stdio() -> None:
    """Run the MCP server over stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await _mcp_server.run(
            read_stream,
            write_stream,
            _mcp_server.create_initialization_options(),
        )


def main() -> None:
    """Entry point for the attune-help MCP server."""
    log_dir = Path(tempfile.gettempdir()) / "attune-help"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(str(log_dir / "attune-help-mcp.log")),
        ],
    )

    try:
        asyncio.run(_run_stdio())
    except KeyboardInterrupt:
        logger.info("attune-help MCP Server stopped")
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: log and exit non-zero so the launcher
        # surfaces the failure
        logger.exception("Server crashed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
