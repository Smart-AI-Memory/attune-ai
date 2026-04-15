---
type: concept
feature: mcp-server
depth: concept
generated_at: 2026-04-14T14:58:41.206381+00:00
source_hash: bcc1c0a657ed14e3ecc0ddf2aa190500d4decf1e455d572148863bce6b9d9c27
status: generated
---

# Mcp Server

## How it works

The MCP server is Attune AI's implementation of the Model Context Protocol, exposing workflow tools, memory storage, authentication utilities, and contextual help through a standardized interface that AI models can interact with directly.

At its core, `EmpathyMCPServer` orchestrates five distinct tool categories: workflow execution (code review, security scans), memory operations (store/retrieve patterns across sessions), authentication management (status checks, tier recommendations), session utilities (interaction levels, context variables), and progressive help lookup. The server uses mixins to organize these capabilities—`MemoryHandlersMixin` handles memory operations while `WorkflowHandlersMixin` manages workflow tools.

A `RateLimiter` with sliding-window tracking prevents abuse by limiting tool calls to 60 per minute by default. The server also exposes MCP resources (workflow lists, auth config, telemetry) and prompts (security-scan, test-gen, cost-report) that clients can discover and invoke.

## Core components

- **`EmpathyMCPServer`** — Main server class that coordinates tool dispatch, prompt handling, and resource access
- **`MemoryHandlersMixin`** — Implements memory_store, memory_retrieve, memory_search, and memory_forget tools with classification levels
- **`WorkflowHandlersMixin`** — Exposes workflow execution tools for code analysis and security scanning
- **`RateLimiter`** — Sliding-window rate limiter that tracks calls per key over a 60-second window

## Tool categories

The server exposes 19 distinct tools across five functional areas:

**Memory tools** enable persistent storage with `memory_store` (supports PUBLIC/INTERNAL/SENSITIVE classifications), `memory_retrieve` for key-based lookup, `memory_search` for pattern matching, and `memory_forget` for cleanup.

**Utility tools** handle authentication (`auth_status`, `auth_recommend`), telemetry (`telemetry_stats`), session management (`attune_get_level`, `attune_set_level`), and context variables (`context_get`, `context_set`).

**Help tools** provide contextual assistance through `help_lookup` (progressive depth escalation), `help_maintain` (stale template detection), `help_init` (project bootstrapping), `help_status` (staleness reports), and `help_update` (template regeneration).

**Workflow tools** expose the core Attune AI capabilities for code review, security scanning, test generation, and cost analysis.

## Integration points

The server connects to Attune's broader ecosystem through the workspace root for file operations, user ID for personalization, and optional memory module integration. Voice interfaces can skip certain tools (memory, auth, telemetry) using the `_VOICE_SKIP_TOOLS` configuration. The `create_server()` factory function initializes a configured instance, while `main()` serves as the CLI entry point for standalone deployment.
