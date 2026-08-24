---
feature: mcp-server
summary: The Model Context Protocol server that exposes attune workflows, help, and memory as tools
tags: [mcp, tools, server]
source_globs:
  - src/attune/mcp/**
nav:
  help: mcp-server
  mkdocs:
    how-to: how-to/mcp-server
    architecture: architecture/mcp-server
    reference: reference/mcp-server
---

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

## Comparison

The MCP server is the **delivery surface** for attune's tools, not a
workflow itself:

| | mcp-server | A workflow (e.g. security-audit) | ops-dashboard |
|--|-----------|----------------------------------|---------------|
| Role | Exposes tools/resources/prompts to an MCP client | One analysis the server can run | Local web UI for running workflows |
| Transport | MCP over stdio | n/a (invoked via a tool/CLI) | HTTP |
| Entry | `python -m attune.mcp.server` + `.mcp.json` | `attune workflow run <slug>` / its MCP tool | `python -m attune.ops` |

The server is how the *conversational* surface reaches every feature;
the CLI (`attune workflow run`) and the ops dashboard are the other two
front doors.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| Tools don't appear in Claude Code | The `.mcp.json` entry is missing or the command can't launch | Add/repair the `mcpServers` entry; confirm `python -m attune.mcp.server` runs | high |
| `RuntimeWarning: coroutine 'AttuneMCPServer.call_tool' was never awaited` | `call_tool` invoked without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| Tool calls start getting rejected under load | The rate limiter tripped (60 calls / 60 s) | Slow the call rate, or construct with a higher `max_calls` | medium |
| A tool returns a "path/argument required" error | The tool's own input contract wasn't met | See that tool's feature page; the server just dispatches | medium |
| Can't tell why the connection failed | Logs aren't on stdout (stdio is the protocol channel) | Read `<tmp>/attune/attune-mcp.log` | low |

### Risk areas

- **`call_tool` is async.** Dispatching without `await` is the common
  mistake when driving the server from Python.
- **stdio is the protocol channel.** Don't print to stdout from a
  handler — logs go to the temp log file, not the console.
- **The server dispatches; tools own their contracts.** A tool-level
  error (bad args) is the tool's, not the server's.

### Diagnosis order

1. Confirm the server launches: `python -m attune.mcp.server`.
2. Confirm registration: the `.mcp.json` `mcpServers` entry.
3. From Python, `create_server().tools` / `get_resource_list()` to
   confirm the surface.
4. For a connection problem, read `<tmp>/attune/attune-mcp.log`.
5. For a single tool failing, consult that tool's feature page.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic source
> of truth fed by four channels — unmatched user queries, telemetry
> error-frequency, GitHub issues, and these author-curated seeds —
> merged, deduplicated, and frequency-ranked by the FAQ Generator (see
> doc-stack D3, and the help-docs-single-source spec's decisions.md D6).
> This section is **not** projected verbatim as the FAQ; it contributes
> the feature's author-curated seed questions.

- **Q:** What is the MCP server?
  **A:** `AttuneMCPServer` — attune's Model Context Protocol server. It
  exposes attune's workflows, help, and memory as MCP tools/resources/
  prompts to a client like Claude Code, over stdio.
- **Q:** How do I run it / make the tools show up?
  **A:** Register `python -m attune.mcp.server` in `.mcp.json` (the
  plugin ships one). Run it directly with the same command for testing.
- **Q:** How many tools does it expose?
  **A:** 41 built-in — across workflow (21), utility (7), help (5),
  memory (4), and personal-memory (4) categories — plus any registered
  by installed plugins (e.g. attune-redis's five `redis_*` tools), and
  3 resources and 3 prompts.
- **Q:** Is `call_tool` async?
  **A:** Yes — `await` it. `create_server()`, `get_resource_list()`,
  and `get_prompt_list()` are synchronous.
- **Q:** Why don't I see server output in my terminal?
  **A:** stdio is the MCP protocol channel; logs go to
  `<tmp>/attune/attune-mcp.log`.

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `create_server` and `AttuneMCPServer` from `attune.mcp`; the
  tool-schema group functions live in `attune.mcp.tool_schemas`.
  Handler methods and the dispatch table are internal.
- **`await` `call_tool`.** It's the one async entry; the inspection
  helpers are sync.
- **Read the log file to debug.** stdout is reserved for the protocol.
- **Tool contracts live with their features.** This page covers the
  server; each tool's inputs are documented on its own feature page.

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
