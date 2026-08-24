---
name: mcp-server
source: content/features/mcp-server.md
tags:
- mcp
- tools
- server
type: task
---

# The Model Context Protocol server that exposes attune workflows, help, and memory as tools

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
