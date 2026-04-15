---
type: note
feature: mcp-server
depth: note
generated_at: 2026-04-14T15:01:16.966204+00:00
source_hash: bcc1c0a657ed14e3ecc0ddf2aa190500d4decf1e455d572148863bce6b9d9c27
status: generated
---

# Note: mcp server

## Context

The Attune AI MCP (Model Context Protocol) server provides AI assistants with access to workflows, memory storage, authentication management, and contextual help through a standardized protocol interface.

## Implementation architecture

The MCP server centers on the `EmpathyMCPServer` class, which aggregates functionality through mixin classes:

- **MemoryHandlersMixin** — Memory store/retrieve/search/forget operations with security classification
- **WorkflowHandlersMixin** — Workflow execution and management tools
- **RateLimiter** — Sliding-window rate limiting for tool calls (default: 60 calls per 60 seconds)

The server exposes four categories of tools:

1. **Workflow tools** — Execute Attune AI workflows
2. **Utility tools** — Authentication status, telemetry stats, interaction level management, session context
3. **Help tools** — Progressive documentation lookup, template maintenance, project-local help bootstrapping
4. **Memory tools** — Cross-session data persistence with pattern matching

## Protocol integration

The server implements standard MCP interfaces for tools, prompts, and resources:

- **Tools** — 15 tools across workflow execution, memory management, authentication, and help
- **Prompts** — Three built-in prompts: `security-scan`, `test-gen`, and `cost-report`
- **Resources** — Three endpoints: workflows list, auth config, and telemetry data

The `create_server()` function initializes an `EmpathyMCPServer` instance, while `main()` serves as the CLI entry point. Rate limiting prevents tool abuse, with certain tools (memory, auth, telemetry) excluded from voice interfaces via `_VOICE_SKIP_TOOLS`.

## Source files

- `src/attune/mcp/**`

**Tags:** `mcp`, `tools`, `server`
