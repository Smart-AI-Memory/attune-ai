---
type: task
feature: mcp-server
depth: task
generated_at: 2026-04-23T03:29:54.748094+00:00
source_hash: b71ff35b50438d054b14e05338981f037a9df8ed86e5607100baa4a370832188
status: generated
---

# Work with MCP server

Use the MCP server when you need to integrate Attune AI capabilities into applications that support the Model Context Protocol.

## Prerequisites

- Access to the project source code
- Python environment with MCP dependencies installed
- Familiarity with the files under `src/attune/mcp/`

## Configure the server

1. **Create a server instance.**
   Use `create_server()` to initialize an `EmpathyMCPServer` with your workspace root and user ID:
   ```python
   from attune.mcp.server import create_server
   server = create_server()
   ```

2. **Set workspace and user context.**
   Initialize the server with specific workspace and user parameters if needed:
   ```python
   server = EmpathyMCPServer(
       workspace_root="/path/to/project",
       user_id="your-user-id"
   )
   ```

3. **Start the server.**
   Run `main()` to launch the MCP server entry point, or integrate the server instance into your MCP-compatible application.

## Add custom prompts

1. **Define your prompt structure.**
   Add entries to the prompts dictionary following the existing format with name, description, and messages template.

2. **Register the prompt.**
   Ensure your prompt appears in `get_prompt_list()` output and is accessible via `get_prompt_messages()`.

3. **Test prompt retrieval.**
   Verify your prompt works by calling:
   ```python
   messages = server.get_prompt_messages("your-prompt-name", {"arg": "value"})
   ```

## Extend tool capabilities

1. **Choose the appropriate tool category.**
   Add new tools to the relevant schema function:
   - `get_workflow_tools()` for workflow execution
   - `get_utility_tools()` for auth, telemetry, and sessions
   - `get_help_tools()` for documentation and help
   - `get_memory_tools()` for data persistence

2. **Define the tool schema.**
   Follow the existing pattern with description, input_schema (JSON Schema), and required fields.

3. **Implement the tool handler.**
   Add the corresponding method to handle tool calls in the appropriate mixin class or main server.

4. **Test tool integration.**
   Verify your tool appears in `get_tool_list()` and responds correctly to `call_tool()`.

## Verify your changes

Run the MCP server and confirm:
- All expected tools appear in the tool list
- Prompts are accessible and render correctly
- Tool calls execute without errors
- Rate limiting works as expected for high-frequency operations

Your MCP server integration is complete when client applications can successfully connect and use all registered tools and prompts.
