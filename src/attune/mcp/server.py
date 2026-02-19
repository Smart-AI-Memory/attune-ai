"""Attune AI MCP Server Implementation.

Exposes Empathy workflows as MCP tools for Claude Code integration.
"""

import asyncio
import json
import logging
import sys
from typing import Any

from .handlers.auth_handlers import get_auth_recommend, get_auth_status
from .handlers.context_handlers import (
    handle_attune_get_level,
    handle_attune_set_level,
    handle_context_get,
    handle_context_set,
)
from .handlers.memory_handlers import (
    handle_memory_forget,
    handle_memory_retrieve,
    handle_memory_search,
    handle_memory_store,
)
from .handlers.telemetry_handlers import get_dashboard_status, get_telemetry_stats
from .handlers.workflow_handlers import (
    run_bug_predict,
    run_code_review,
    run_performance_audit,
    run_release_prep,
    run_security_audit,
    run_test_generation,
)
from .prompts import get_prompt_list as _get_prompt_list
from .prompts import get_prompt_messages as _get_prompt_messages
from .request_handler import handle_request
from .tool_definitions import (
    PROMPT_DEFINITIONS,
    RESOURCE_DEFINITIONS,
    TOOL_DEFINITIONS,
)

# MCP server will be implemented using stdio transport
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool name -> handler function mapping
# ---------------------------------------------------------------------------

_TOOL_HANDLER_MAP: dict[str, Any] = {
    "security_audit": run_security_audit,
    "bug_predict": run_bug_predict,
    "code_review": run_code_review,
    "test_generation": run_test_generation,
    "performance_audit": run_performance_audit,
    "release_prep": run_release_prep,
    "auth_status": get_auth_status,
    "auth_recommend": get_auth_recommend,
    "telemetry_stats": get_telemetry_stats,
    "dashboard_status": get_dashboard_status,
    "memory_store": handle_memory_store,
    "memory_retrieve": handle_memory_retrieve,
    "memory_search": handle_memory_search,
    "memory_forget": handle_memory_forget,
    "attune_get_level": handle_attune_get_level,
    "attune_set_level": handle_attune_set_level,
    "context_get": handle_context_get,
    "context_set": handle_context_set,
}

# Tools that take no arguments (only server)
_NO_ARGS_TOOLS = {"attune_get_level", "dashboard_status", "auth_status"}


class EmpathyMCPServer:
    """MCP server for Attune AI workflows.

    Exposes workflows, agent dashboard, and telemetry as MCP tools
    that can be invoked from Claude Code.
    """

    def __init__(self):
        """Initialize the MCP server."""
        self.tools = dict(TOOL_DEFINITIONS)
        self.resources = dict(RESOURCE_DEFINITIONS)
        self.prompts = dict(PROMPT_DEFINITIONS)
        self._memory = None
        self._attune_level = 3  # Default: Level3Proactive
        self._context: dict[str, str] = {}

        # Check for updates (non-blocking, cached per session)
        try:
            from .version_check import check_for_updates

            check_for_updates()
        except Exception:  # noqa: BLE001
            pass  # INTENTIONAL: Version check is best-effort

    def get_prompt_list(self) -> list[dict[str, Any]]:
        """Get list of available prompts.

        Returns:
            List of prompt definitions
        """
        return _get_prompt_list(self.prompts)

    def get_prompt_messages(
        self, prompt_name: str, arguments: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Get messages for a specific prompt.

        Args:
            prompt_name: Name of the prompt to retrieve
            arguments: Prompt arguments provided by the caller

        Returns:
            List of messages for the prompt

        Raises:
            ValueError: If prompt_name is not found
        """
        return _get_prompt_messages(self.prompts, prompt_name, arguments)

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        handler = _TOOL_HANDLER_MAP.get(tool_name)
        if not handler:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        try:
            if tool_name in _NO_ARGS_TOOLS:
                return await handler(self)
            return await handler(self, arguments)
        except Exception as e:
            logger.exception(f"Tool execution failed: {tool_name}")
            return {"success": False, "error": str(e)}

    def get_tool_list(self) -> list[dict[str, Any]]:
        """Get list of available tools.

        Returns:
            List of tool definitions
        """
        return list(self.tools.values())

    def get_resource_list(self) -> list[dict[str, Any]]:
        """Get list of available resources.

        Returns:
            List of resource definitions
        """
        return list(self.resources.values())


async def main_loop():
    """Main MCP server loop using stdio transport."""
    server = EmpathyMCPServer()

    logger.info("Empathy MCP Server started")
    logger.info(f"Registered {len(server.tools)} tools")

    while True:
        try:
            # Read request from stdin (JSON-RPC format)
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break

            request = json.loads(line)
            response = await handle_request(server, request)

            # Write response to stdout
            print(json.dumps(response), flush=True)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            error_response = {"error": {"code": -32700, "message": "Parse error"}}
            print(json.dumps(error_response), flush=True)
        except Exception as e:
            logger.exception("Error handling request")
            error_response = {"error": {"code": -32603, "message": str(e)}}
            print(json.dumps(error_response), flush=True)


def create_server() -> EmpathyMCPServer:
    """Create and return an Empathy MCP server instance.

    Returns:
        Configured MCP server
    """
    return EmpathyMCPServer()


def main():
    """Entry point for MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("/tmp/attune-mcp.log")],  # nosec B108
    )

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("Empathy MCP Server stopped")


if __name__ == "__main__":
    main()
