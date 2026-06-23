# Mcp Server

## Reference

The public surface is `create_server` and `EmpathyMCPServer`, exported
from `attune.mcp`.

### `attune.mcp`

| Symbol | Purpose |
|--------|---------|
| `create_server() -> EmpathyMCPServer` | Build a ready server instance. |
| `EmpathyMCPServer(...)` | The MCP server (composes `MemoryHandlersMixin` + `WorkflowHandlersMixin`). |

### `EmpathyMCPServer` — selected members

| Member | Purpose |
|--------|---------|
| `call_tool(tool_name, arguments) -> dict` | **Async.** Dispatch a tool by name and return its result. |
| `tools` | The merged tool registry — 41 built-in tools plus any plugin-registered tools. |
| `resources` | The registered resources. |
| `get_resource_list() -> list[dict]` | The three `attune://…` resources. |
| `get_prompt_list() -> list[dict]` | The three prompt templates. |
| `get_prompt_messages(name, arguments)` | Render a prompt's messages. |

### Tool-schema groups — `attune.mcp.tool_schemas`

| Function | Count |
|----------|-------|
| `get_workflow_tools()` | 21 |
| `get_utility_tools()` | 7 |
| `get_help_tools()` | 5 |
| `get_memory_tools()` | 4 |
| `get_personal_memory_tools()` | 4 |
| `get_resources()` | 3 resources |
| `get_prompts()` | 3 prompts |

### Launch

| Surface | Invocation |
|---------|------------|
| Client registration | `.mcp.json` → `python -m attune.mcp.server` (plugin uses `uvx --from attune-ai …`). |
| Direct | `python -m attune.mcp.server` (stdio). |
| Python | `create_server()` / `EmpathyMCPServer`. |

<!-- attune-generated: source_hash=08e50eacebc45c71e34c3de6ca5e70b0eed13373bff884ee18bc5f88124ac95f feature=mcp-server kind=reference generated_at=2026-06-23 -->
