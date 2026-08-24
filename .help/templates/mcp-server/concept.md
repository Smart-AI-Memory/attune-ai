---
type: concept
name: mcp-server-concept
feature: mcp-server
depth: concept
generated_at: 2026-08-24T13:13:51.843371+00:00
source_hash: e6370b6c61134866408d30c64611640a3ac5184dc9d37f7e676a5f7ad176e69c
status: generated
---

# The Model Context Protocol server that exposes attune workflows, help, and memory as tools

## Overview

The MCP server is attune's **Model Context Protocol** implementation —
it exposes attune's workflows, help system, and memory as structured
**tools**, **resources**, and **prompts** that an MCP client (Claude
Code) can call. The server class is **`AttuneMCPServer`**; it speaks
MCP over **stdio** and is launched with `python -m attune.mcp.server`.

It is how every other attune feature reaches a conversation: the
`code_review`, `security_audit`, `memory_store`, `help_lookup`, … tools
you call in Claude Code are registered and dispatched here. This page
documents the **server itself** — its architecture, how to run and
register it, and the tool/resource/prompt surface — not each individual
tool (those belong to their own features).

You reach it these ways:

- **registration** — a `.mcp.json` entry runs `python -m
  attune.mcp.server` (the plugin ships one); Claude Code connects over
  stdio;
- the Python API — `from attune.mcp import create_server,
  AttuneMCPServer`, for embedding or testing the server.

## Concepts

### `AttuneMCPServer` and its mixins

`AttuneMCPServer(MemoryHandlersMixin, WorkflowHandlersMixin)` is the
core server. The mixins supply handler groups: `WorkflowHandlersMixin`
runs the analysis workflows, `MemoryHandlersMixin` handles
cross-session memory. A `RateLimiter` guards against tool-call floods.
`create_server()` builds a ready instance.

### The tool surface — 41 built-in tools in 5 categories

At startup the server merges five built-in tool-schema groups (from
`attune.mcp.tool_schemas`) into one registry, then lets installed
plugins register more (`_register_plugin_tools` — e.g. attune-redis
adds its `redis_*` tools), so `server.tools` can hold more than these
41:

| Category | Function | Count | Examples |
|----------|----------|-------|----------|
| Workflow | `get_workflow_tools()` | 21 | `code_review`, `security_audit`, `test_generation`, `release_notes`, `rag_knowledge_query` |
| Utility | `get_utility_tools()` | 7 | `auth_status`, `telemetry_stats`, `attune_set_level`, `context_get` |
| Help | `get_help_tools()` | 5 | `help_lookup`, `help_update`, `help_status` |
| Memory | `get_memory_tools()` | 4 | `memory_store`, `memory_retrieve`, `memory_search` |
| Personal memory | `get_personal_memory_tools()` | 4 | `personal_memory_capture`, `personal_memory_recall` |

A `_build_dispatch_table()` maps each tool name to the handler method
that runs it; `call_tool(name, arguments)` is the async dispatch entry.

### Resources and prompts

Beyond tools, the server publishes three **resources** (read-only
data) and three **prompts** (reusable prompt templates):

| Kind | Names |
|------|-------|
| Resources | `attune://workflows`, `attune://auth/config`, `attune://telemetry` |
| Prompts | `security-scan`, `test-gen`, `cost-report` |

`get_resource_list()` and `get_prompt_list()` return them.

### Rate limiting

A sliding-window `RateLimiter(max_calls=60, window_seconds=60.0)`
caps tool calls — by default **60 calls per 60-second window** — so a
runaway client can't flood the server.

### Transport and launch

The server runs over **stdio**: `main()` calls
`asyncio.run(_run_stdio())`. Launch it with `python -m
attune.mcp.server`. It logs to a temp file (`attune-mcp.log`) and loads
`.env` so an `ANTHROPIC_API_KEY` is available to tools that need it
(e.g. the help polish pass).
