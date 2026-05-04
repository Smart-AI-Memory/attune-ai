---
type: task
feature: mcp-server
depth: task
generated_at: 2026-05-04T02:29:51.286450+00:00
source_hash: f7f2360f6ad84733ba187b2e644d9b01ac30e15d2ae8fe8567af6dfb064ee44b
status: generated
---

# Work with MCP server

Use the MCP server when you need to implement or modify Model Context Protocol tool handlers for Attune AI workflows.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `src/attune/mcp/`
- Understanding of MCP (Model Context Protocol) concepts

## Steps

1. **Identify the server component to modify**

   Determine which part of the MCP server handles your use case:
   - **Prompts**: Use `src/attune/mcp/prompts.py` for prompt templates
   - **Tools**: Use `src/attune/mcp/tool_schemas.py` for tool definitions
   - **Server core**: Use `src/attune/mcp/server.py` for server lifecycle
   - **Memory handlers**: Use `src/attune/mcp/memory_handlers.py` for memory operations
   - **Rate limiting**: Use `src/attune/mcp/rate_limiter.py` for call throttling

2. **Review the existing implementation**

   Open the relevant file and examine:
   - The function signature and docstring
   - Input parameters and return types
   - Error handling patterns
   - Integration with other components

3. **Create your MCP server instance**

   If working with a new server instance:
   ```python
   from attune.mcp.server import create_server
   server = create_server()
   ```

4. **Modify the appropriate handler**

   Make your changes following the established patterns:
   - Tool functions return `dict[str, Any]` with structured responses
   - Use the rate limiter for external API calls
   - Follow the naming convention for new tools
   - Include proper error handling with meaningful messages

5. **Test your changes**

   Run the MCP server tests to verify your implementation:
   ```bash
   pytest -k "mcp" --verbose
   ```

## Verify success

Your implementation is working when:
- The MCP server starts without errors using `main()`
- Your tool appears in the tool list from `get_tool_list()`
- Tool calls return the expected response format
- Rate limiting prevents excessive API usage
- All existing tests continue to pass
