---
feature: mcp-server
depth: concept
generated_at: 2026-04-13T16:56:40.511077+00:00
source_hash: cd9113c895b6740f8b406b613bcb2f3d3ed3fac586882f2d8ebc96e6107c1f5f
status: generated
---

# Mcp Server

## How it works

Model Context Protocol server that provides AI tools and workflow execution capabilities for Attune AI.

The main building blocks are:

- **`EmpathyMCPServer`** — Main server that handles MCP protocol communication and tool execution.
- **`MemoryHandlersMixin`** — Provides memory operations including store, retrieve, search, and forget functionality.
- **`WorkflowHandlersMixin`** — Handles workflow execution and management tools.
- **`RateLimiter`** — Controls request frequency using a sliding-window algorithm to prevent abuse.

Under the hood, this feature spans 8 source
files covering:

- Tool definitions for memory, workflow, utility, and help operations.
- Prompt templates and message handling for AI interactions.
- Rate limiting to control MCP tool call frequency.

## What connects to it

This feature relates to: mcp, tools, server.

Other parts of the codebase interact with
mcp server through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `EmpathyMCPServer` | Main server that handles MCP protocol communication and tool execution. | `src/attune/mcp/server.py` |
| `MemoryHandlersMixin` | Provides memory operations including store, retrieve, search, and forget functionality. | `src/attune/mcp/memory_handlers.py` |
| `WorkflowHandlersMixin` | Handles workflow execution and management tools. | `src/attune/mcp/workflow_handlers.py` |
| `RateLimiter` | Controls request frequency using a sliding-window algorithm to prevent abuse. | `src/attune/mcp/rate_limiter.py` |
