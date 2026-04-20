---
type: task
feature: mcp-server
depth: task
generated_at: 2026-04-20T01:19:54.658945+00:00
source_hash: cab70f0aeb1782a9a9523b0ae9f7a4efe73904a1b5f3f26ec70fc1f9dc7cd315
status: generated
---

# Work with MCP server

Use the MCP server when you need to integrate Attune AI workflows with Model Context Protocol (MCP) clients like Claude Desktop or other AI tools that support the MCP standard.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `src/attune/mcp/`
- Basic understanding of the Model Context Protocol specification

## Create a new MCP server instance

1. **Import the server factory function.**
   ```python
   from attune.mcp.server import create_server
   ```

2. **Create the server with optional configuration.**
   ```python
   server = create_server()
   # Or with custom workspace and user ID:
   server = create_server(workspace_root="/path/to/project", user_id="user123")
   ```

3. **Start the server for MCP communication.**
   The server provides tools for workflows, authentication, telemetry, help lookup, and memory management.

## Add custom tool definitions

1. **Locate the appropriate tool schema function.**
   - `get_workflow_tools()` for workflow execution tools
   - `get_utility_tools()` for auth, telemetry, and session management
   - `get_help_tools()` for contextual help and documentation
   - `get_memory_tools()` for memory store/retrieve operations

2. **Add your tool definition to the returned dictionary.**
   Follow the existing pattern with `description` and `input_schema` fields:
   ```python
   def get_utility_tools():
       return {
           'your_tool_name': {
               'description': 'Clear description of what the tool does',
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
       }
   ```

3. **Implement the tool handler in the appropriate mixin class.**
   Add the handler method to `WorkflowHandlersMixin`, `MemoryHandlersMixin`, or the main `EmpathyMCPServer` class.

## Configure prompts

1. **Add prompt definitions to the prompts dictionary.**
   Edit the return value of `get_prompts()` in `src/attune/mcp/tool_schemas.py`:
   ```python
   'your-prompt-name': {
       'name': 'your-prompt-name',
       'description': 'What this prompt does',
       'arguments': [
           {
               'name': 'required_param',
               'description': 'Parameter description',
               'required': True
           }
       ]
   }
   ```

2. **Implement prompt message generation.**
   The `get_prompt_messages()` function should handle your new prompt name and return formatted messages based on the arguments.

## Handle rate limiting

1. **Check if rate limiting is needed for your tool.**
   The `RateLimiter` class provides sliding-window rate limiting with configurable limits.

2. **Create a rate limiter instance.**
   ```python
   limiter = RateLimiter(max_calls=60, window_seconds=60.0)
   ```

3. **Check rate limits before tool execution.**
   ```python
   if not limiter.check(user_key):
       raise Exception("Rate limit exceeded")
   ```

## Verify the server works

1. **Run the server directly.**
   ```bash
   python -m attune.mcp.server
   ```

2. **Test tool availability.**
   The server should respond to MCP tool list requests with all configured tools from workflow, utility, help, and memory categories.

3. **Verify prompt functionality.**
   Test that prompts return properly formatted messages when called with required arguments.

The server successfully integrates with MCP clients when it responds to tool calls and prompt requests without errors.
