---
type: concept
feature: mcp-server
depth: concept
generated_at: 2026-06-22T10:00:48.764701+00:00
source_hash: 9e36c58165bf28d2d017a183ce57a5f54f8bf32c3d68cd05d5d762a3eb741ae4
status: generated
---

# MCP Server

The Attune AI MCP Server is a Model Context Protocol implementation that exposes AI workflows, help documentation, memory systems, and utility functions as structured tools for AI clients.

## Server architecture

The server uses a modular design where handler mixins provide different categories of functionality to the main `EmpathyMCPServer` class:

- **`EmpathyMCPServer`** — Core MCP protocol implementation that coordinates prompts, tools, and resources
- **`MemoryHandlersMixin`** — Cross-session memory storage and retrieval for decisions, patterns, and troubleshooting findings
- **`WorkflowHandlersMixin`** — Execution interface for Attune AI automation workflows
- **`RateLimiter`** — Sliding-window protection against excessive tool calls

## Tool categories

The server exposes five distinct tool groups through MCP:

| Category | Tools | Purpose |
|----------|-------|---------|
| **Workflow execution** | `get_workflow_tools()` | Run code reviews, security audits, refactoring, and other AI-assisted workflows |
| **Documentation system** | `get_help_tools()` | Progressive help lookup, template maintenance, and project help initialization |
| **Session utilities** | `get_utility_tools()` | Authentication status, telemetry stats, interaction level control, context management |
| **Personal memory** | `get_personal_memory_tools()` | Store and recall decisions across sessions in `~/.attune/memory/` |
| **Structured memory** | `get_memory_tools()` | Pattern storage and cross-agent coordination through the attune-ai memory module |

## Protocol compliance

The server implements standard MCP resource types:

- **Workflows resource** (`attune://workflows`) — JSON list of available automation workflows
- **Authentication config** (`attune://auth/config`) — Current auth strategy and subscription tier
- **Telemetry data** (`attune://telemetry`) — Cost tracking and performance metrics

Rate limiting protects against tool abuse with configurable call windows, defaulting to 60 calls per 60-second window.
