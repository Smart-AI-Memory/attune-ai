---
type: concept
feature: mcp-server
depth: concept
generated_at: 2026-04-20T01:19:41.402959+00:00
source_hash: cab70f0aeb1782a9a9523b0ae9f7a4efe73904a1e5f3f26ec70fc1f9dc7cd315
status: generated
---

# MCP Server

## What it is

The MCP Server is Attune AI's implementation of the Model Context Protocol, providing structured access to workflows, memory, help documentation, and authentication through a standardized tool interface.

## Core architecture

The server uses a mixin-based design where `EmpathyMCPServer` combines specialized handler classes:

- **`MemoryHandlersMixin`** — Persistent storage and retrieval across sessions
- **`WorkflowHandlersMixin`** — Execution of Attune AI workflows
- **`RateLimiter`** — Sliding-window throttling for tool calls

The server exposes three MCP primitives:
- **Tools** — 15 callable functions for workflows, memory, help, and utilities
- **Prompts** — 3 templates for security scanning, test generation, and cost reporting
- **Resources** — 3 data endpoints for workflow lists, auth config, and telemetry

## Tool categories

| Category | Tools | Purpose |
|----------|-------|---------|
| **Workflow** | Execution tools | Run Attune AI workflows with auth and telemetry |
| **Memory** | `memory_store`, `memory_retrieve`, `memory_search`, `memory_forget` | Cross-session data persistence |
| **Help** | `help_lookup`, `help_maintain`, `help_init`, `help_status`, `help_update` | Progressive documentation system |
| **Utility** | `auth_status`, `telemetry_stats`, session context tools | Authentication and metrics |

## Rate limiting

Tool calls are throttled using a 60-calls-per-minute sliding window. The `RateLimiter` tracks calls by key and rejects requests that exceed the threshold, preventing API abuse while allowing normal usage patterns.

## Entry points

The server can be created programmatically via `create_server()` or launched as a standalone process via `main()`. Both methods initialize the workspace root and user context from environment variables or defaults.
