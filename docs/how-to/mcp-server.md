# Mcp Server

## Quickstart

Register the server with Claude Code via `.mcp.json` (the plugin ships
this) so the tools appear in your conversation:

```json
{
  "mcpServers": {
    "attune-ai": {
      "command": "uv",
      "args": ["run", "python", "-m", "attune.mcp.server"]
    }
  }
}
```

Once connected, the built-in tools (`code_review`, `help_lookup`,
`memory_store`, …) — plus any registered by installed plugins — are
callable from the conversation. To run the server directly for testing:

```bash
python -m attune.mcp.server
```

## Tasks

### Inspect the server's surface from Python

**Goal:** see the registered tools, resources, and prompts without a
client.

**Steps:**

```python
from attune.mcp import create_server

server = create_server()
print(len(server.tools), "tools")
print([r["uri"] for r in server.get_resource_list()])
print([p["name"] for p in server.get_prompt_list()])
```

**Verify:** `create_server()` returns a ready `AttuneMCPServer`.
`server.tools` is the merged registry — the 41 built-in tools plus any
registered by installed plugins (e.g. attune-redis adds five `redis_*`
tools), so the printed count is ≥ 41. `get_resource_list()` returns the
three `attune://…` resources; `get_prompt_list()` returns
`security-scan` / `test-gen` / `cost-report`.

### Call a tool programmatically

**Goal:** dispatch a tool the way the MCP client would.

**Steps:**

```python
import asyncio

from attune.mcp import create_server


async def main() -> None:
    server = create_server()
    result = await server.call_tool("auth_status", {})
    print(result)


asyncio.run(main())
```

**Verify:** `call_tool(name, arguments)` is a coroutine — `await` it.
It looks the handler up in the dispatch table and returns the tool's
result dict. Rate limiting applies (60 calls / 60 s by default).

### Register the server with a client

**Goal:** make the tools available in Claude Code.

**Steps:** add an `mcpServers` entry that runs `python -m
attune.mcp.server` (see Quickstart). The plugin's bundled `.mcp.json`
uses `uvx --from attune-ai python -m attune.mcp.server`; a local
checkout uses `uv run python -m attune.mcp.server`.

**Verify:** after connecting, the attune tools appear in the client.
Server logs land in `<tmp>/attune/attune-mcp.log` if you need to
debug the connection.

## Reference

The public surface is `create_server` and `AttuneMCPServer`, exported
from `attune.mcp`.

### `attune.mcp`

| Symbol | Purpose |
|--------|---------|
| `create_server() -> AttuneMCPServer` | Build a ready server instance. |
| `AttuneMCPServer(...)` | The MCP server (composes `MemoryHandlersMixin` + `WorkflowHandlersMixin`). |

### `AttuneMCPServer` — selected members

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
| Python | `create_server()` / `AttuneMCPServer`. |

<!-- attune-generated: source_hash=e6370b6c61134866408d30c64611640a3ac5184dc9d37f7e676a5f7ad176e69c feature=mcp-server kind=how-to generated_at=2026-08-24 -->
