---
type: task
feature: mcp-server
depth: task
generated_at: 2026-04-14T14:59:00.023869+00:00
source_hash: bcc1c0a657ed14e3ecc0ddf2aa190500d4decf1e455d572148863bce6b9d9c27
status: generated
---

# Work with mcp server

Use the MCP server when you need to integrate Attune AI workflows with Model Context Protocol-compatible clients like Claude Desktop or VS Code extensions.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/mcp/**

## Create a new MCP server instance

1. **Import the server factory function:**
   ```python
   from attune.mcp.server import create_server
   ```

2. **Create the server instance:**
   ```python
   server = create_server()
   ```

3. **Verify the server is ready:**
   Run `server.get_tool_list()` to confirm it returns available tools like `auth_status`, `help_lookup`, and workflow tools.

## Add new tools to the server

1. **Choose the appropriate tool category:**
   - Workflow tools: Add to `get_workflow_tools()` in `src/attune/mcp/tool_schemas.py`
   - Utility tools: Add to `get_utility_tools()` for auth, telemetry, and session management
   - Help tools: Add to `get_help_tools()` for documentation features
   - Memory tools: Add to `get_memory_tools()` for data persistence

2. **Define your tool schema:**
   ```python
   'your_tool_name': {
       'description': 'What your tool does',
       'input_schema': {
           'type': 'object',
           'properties': {
               'param_name': {
                   'type': 'string',
                   'description': 'Parameter description'
               }
           },
           'required': ['param_name']
       }
   }
   ```

3. **Implement the tool handler:**
   Add the handler method to the appropriate mixin class (`MemoryHandlersMixin` or `WorkflowHandlersMixin`) in the server implementation.

4. **Test the tool registration:**
   Run `server.get_tool_list()` and verify your new tool appears in the results.

## Add new prompts to the server

1. **Define the prompt in `get_prompts()`:**
   ```python
   'your-prompt-name': {
       'name': 'your-prompt-name',
       'description': 'What this prompt accomplishes',
       'arguments': [
           {
               'name': 'input_param',
               'description': 'Input parameter description',
               'required': True
           }
       ]
   }
   ```

2. **Test prompt availability:**
   Run `server.get_prompt_list()` to confirm your prompt is registered.

3. **Test prompt execution:**
   Call `server.get_prompt_messages('your-prompt-name', {'input_param': 'test_value'})` and verify it returns properly formatted messages.

## Configure rate limiting

1. **Set rate limits during server creation:**
   ```python
   # Default: 60 calls per 60 seconds
   server = create_server()

   # Or customize in the RateLimiter class
   rate_limiter = RateLimiter(max_calls=100, window_seconds=60.0)
   ```

2. **Verify rate limiting works:**
   Make rapid successive calls to any tool and confirm that after the limit, `RateLimiter.check()` returns `False`.

## Key files

- `src/attune/mcp/server.py` - Main server implementation and factory
- `src/attune/mcp/tool_schemas.py` - Tool definitions for all categories
- `src/attune/mcp/prompts.py` - Prompt handling and message formatting
- `src/attune/mcp/rate_limiter.py` - Request rate limiting
- `src/attune/mcp/memory.py` - Memory tool handlers
- `src/attune/mcp/workflow.py` - Workflow tool handlers

## Verify success

The MCP server is working correctly when:
- `create_server()` returns an `EmpathyMCPServer` instance without errors
- `server.get_tool_list()` returns all expected tools including utility, help, memory, and workflow tools
- Tool calls via `server.call_tool()` execute successfully and return proper responses
- Rate limiting prevents excessive calls after the configured threshold
