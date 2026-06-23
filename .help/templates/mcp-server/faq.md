---
type: faq
name: mcp-server-faq
feature: mcp-server
depth: faq
status: manual
---

# MCP Server FAQ

## What is the MCP server?

`EmpathyMCPServer` — attune's Model Context Protocol server. It exposes
attune's workflows, help, and memory as MCP **tools**, **resources**,
and **prompts** to a client like Claude Code, speaking MCP over stdio.
It's how the conversational surface reaches every attune feature.

## How do I run it / make the tools show up?

Register `python -m attune.mcp.server` in `.mcp.json` (the plugin ships
one). The plugin entry uses `uvx --from attune-ai python -m
attune.mcp.server`; a local checkout uses `uv run python -m
attune.mcp.server`. Run the same command directly to test the server.

## How many tools does it expose?

41 built-in tools, across five categories — workflow (21), utility (7),
help (5), memory (4), and personal-memory (4) — plus 3 resources
(`attune://workflows`, `attune://auth/config`, `attune://telemetry`)
and 3 prompts (`security-scan`, `test-gen`, `cost-report`). Installed
plugins can register more (e.g. attune-redis adds five `redis_*`
tools), so `server.tools` may hold more than 41.

## Is `call_tool` async?

Yes — `await EmpathyMCPServer.call_tool(name, arguments)`. The
inspection helpers `create_server()`, `get_resource_list()`, and
`get_prompt_list()` are synchronous.

## How do I inspect the server from Python?

```python
from attune.mcp import create_server

server = create_server()
print(len(server.tools), "tools")
print([r["uri"] for r in server.get_resource_list()])
print([p["name"] for p in server.get_prompt_list()])
```

## What if the server isn't responding?

Confirm `.mcp.json` exists and its command launches (`python -m
attune.mcp.server`). stdout is the MCP protocol channel, so logs go to
`<tmp>/attune/attune-mcp.log` — read that to debug a connection.

## Where is the server code?

`src/attune/mcp/server.py` (the `EmpathyMCPServer` class). Tool
*schemas* live in `src/attune/mcp/tool_schemas.py` (the five
`get_*_tools` groups + `get_resources` + `get_prompts`); *handlers*
live in `memory_handlers.py` / `workflow_handlers.py`; rate limiting is
in `rate_limiter.py`.

**Tags:** `mcp`, `tools`, `server`
