---
type: concept
feature: mcp-server
depth: concept
generated_at: 2026-04-23T03:29:41.895753+00:00
source_hash: b71ff35b50438d054b14e05338981f037a9df8ed86e5607100baa4a370832188
status: generated
---

# MCP Server

## What it is

The MCP server is Attune's implementation of the Model Context Protocol, enabling AI assistants to access Attune's tools, memory systems, and contextual help through a standardized interface.

## Core architecture

The server is built around `EmpathyMCPServer`, which combines several specialized mixins to provide different categories of functionality:

- **Memory operations** — Store and retrieve cross-session patterns, decisions, and troubleshooting findings through personal and project memory systems
- **Workflow execution** — Run Attune's automated workflows for code review, security audits, and other development tasks
- **Contextual help** — Access progressive documentation that adapts depth based on user experience and context
- **Session management** — Track interaction levels, authentication status, and telemetry data

The `RateLimiter` prevents tool abuse by applying sliding-window limits to MCP calls, ensuring stable performance under high usage.

## Tool categories

The server exposes four main tool groups:

| Category | Tools | Purpose |
|----------|-------|---------|
| **Workflow** | Execution tools | Run automated development workflows |
| **Utility** | `auth_status`, `telemetry_stats`, `attune_set_level` | Manage authentication, view metrics, configure interaction modes |
| **Help** | `help_lookup`, `help_maintain`, `help_init` | Access contextual documentation and manage help systems |
| **Memory** | `memory_store`, `personal_memory_capture`, `memory_search` | Store and retrieve knowledge across sessions |

## How assistants connect

AI assistants interact with the server through the Model Context Protocol. The server provides prompts, tools, and resources that assistants can discover and use without knowing Attune's internal implementation details.

The protocol handles authentication, rate limiting, and error responses automatically, so assistants can focus on helping users with their development tasks rather than managing connection details.
