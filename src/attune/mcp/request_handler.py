"""Request handling for Attune AI MCP Server.

Routes incoming MCP JSON-RPC requests to the appropriate server methods.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from attune.mcp.server import EmpathyMCPServer

logger = logging.getLogger(__name__)


async def handle_request(server: EmpathyMCPServer, request: dict[str, Any]) -> dict[str, Any]:
    """Handle an MCP request.

    Args:
        server: MCP server instance
        request: MCP request

    Returns:
        MCP response

    """
    method = request.get("method")
    params = request.get("params", {})

    if method == "tools/list":
        return {"tools": server.get_tool_list()}
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        result = await server.call_tool(tool_name, arguments)
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    if method == "resources/list":
        return {"resources": server.get_resource_list()}
    if method == "prompts/list":
        return {"prompts": server.get_prompt_list()}
    if method == "prompts/get":
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})
        try:
            messages = server.get_prompt_messages(prompt_name, arguments)
            return {"messages": messages}
        except ValueError as e:
            return {"error": {"code": -32602, "message": str(e)}}
    else:
        return {"error": {"code": -32601, "message": f"Method not found: {method}"}}
