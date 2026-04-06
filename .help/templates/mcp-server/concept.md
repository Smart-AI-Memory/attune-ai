---
feature: mcp-server
depth: concept
generated_at: 2026-04-06T04:29:53.503162+00:00
source_hash: 64f150abed667e764233b86a01bfe7000bb8f4d6507efcca218ef09579d9f90e
status: generated
---

# Mcp Server

## How it works

Model Context Protocol server that provides AI assistants with access to Attune AI workflows, memory management, and contextual help.

The main building blocks are:

- **`MemoryHandlersMixin`** — Provides memory storage, retrieval, search, and forgetting capabilities.
- **`RateLimiter`** — Controls the frequency of MCP tool calls using a sliding-window algorithm.
- **`EmpathyMCPServer`** — Central server that handles MCP protocol communication and tool execution.
- **`WorkflowHandlersMixin`** — Enables workflow execution through MCP tool interfaces.

Under the hood, this feature spans 19 source
files covering:

- Tool definitions for workflow execution, authentication, telemetry, and session management.
- Prompt templates and message handling for AI interactions.
- Resource definitions for MCP protocol compliance.

## What connects to it

This feature relates to: mcp, tools, server.

Other parts of the codebase interact with
mcp server through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `MemoryHandlersMixin` | Provides memory storage, retrieval, search, and forgetting capabilities. | `src/attune/mcp/memory_handlers.py` |
| `RateLimiter` | Controls the frequency of MCP tool calls using a sliding-window algorithm. | `src/attune/mcp/rate_limiter.py` |
| `EmpathyMCPServer` | Central server that handles MCP protocol communication and tool execution. | `src/attune/mcp/server.py` |
| `WorkflowHandlersMixin` | Enables workflow execution through MCP tool interfaces. | `src/attune/mcp/workflow_handlers.py` |
