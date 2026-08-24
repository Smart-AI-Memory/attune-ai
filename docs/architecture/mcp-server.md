# Mcp Server

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

## Design & extension

### Design decisions

- **Mixins by domain.** `AttuneMCPServer` composes
  `WorkflowHandlersMixin` and `MemoryHandlersMixin` so handler groups
  stay cohesive and the server class stays a thin coordinator.
- **Schemas separate from handlers.** Tool *schemas* live in
  `tool_schemas.py` (the five `get_*_tools` groups + resources +
  prompts); *handlers* live in the mixins; a dispatch table binds name
  → handler. Adding a tool touches both, deliberately.
- **stdio transport.** The server speaks MCP over stdio (the standard
  local-client channel), so stdout is the protocol and logs go to a
  file.
- **Rate-limited by default.** A 60-call/60-second sliding window
  protects against runaway clients without per-tool configuration.

### Extension points

- **Add a tool:** add its schema to the right `get_*_tools` group in
  `tool_schemas.py`, add a handler method, and register it in
  `_build_dispatch_table()`.
- **Add a resource or prompt:** extend `get_resources()` /
  `get_prompts()`.
- **Tune rate limiting:** construct the server's `RateLimiter` with a
  different `max_calls` / `window_seconds`.
- **Embed the server:** `create_server()` returns an instance you can
  drive directly (e.g. in tests via `await call_tool(...)`).

<!-- attune-generated: source_hash=e6370b6c61134866408d30c64611640a3ac5184dc9d37f7e676a5f7ad176e69c feature=mcp-server kind=architecture generated_at=2026-08-24 -->
