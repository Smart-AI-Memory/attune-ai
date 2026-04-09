---
feature: mcp-server
depth: concept
generated_at: 2026-04-06T16:05:31.926227+00:00
source_hash: 21be20fb9764e6dedd2f0f21394d99f48796b3f52102798ef7192d0abc6487ff
status: generated
---

# Mcp Server

## How it works

Model Context Protocol server and tool handlers.

The main building blocks are:

- **`MemoryHandlersMixin`** — Mixin providing memory tool handlers for EmpathyMCPServer.
- **`RateLimiter`** — Simple sliding-window rate limiter.
- **`EmpathyMCPServer`** — MCP server for Attune AI workflows.
- **`WorkflowHandlersMixin`** — Mixin providing workflow tool handlers for EmpathyMCPServer.

Under the hood, this feature spans 19 source
files covering:

- Memory tool handlers for the MCP server.
- Prompt handling for Attune AI MCP Server.
- In-process rate limiter for MCP tool calls.

## What connects to it

This feature relates to: mcp, tools, server.

Other parts of the codebase interact with
mcp server through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `MemoryHandlersMixin` | Mixin providing memory tool handlers for EmpathyMCPServer. | `src/attune/mcp/memory_handlers.py` |
| `RateLimiter` | Simple sliding-window rate limiter. | `src/attune/mcp/rate_limiter.py` |
| `EmpathyMCPServer` | MCP server for Attune AI workflows. | `src/attune/mcp/server.py` |
| `WorkflowHandlersMixin` | Mixin providing workflow tool handlers for EmpathyMCPServer. | `src/attune/mcp/workflow_handlers.py` |
