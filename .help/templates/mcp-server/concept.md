---
type: concept
feature: mcp-server
depth: concept
generated_at: 2026-04-19T18:47:37.031498+00:00
source_hash: 4d53983ae8928abce86e5e58e1d186acd20ca65e85b505d31acc051216daed33
status: generated
---

# MCP Server

An MCP (Model Context Protocol) server that exposes Attune AI's workflow, memory, and help system capabilities as standardized tools, prompts, and resources.

## Core architecture

The server is built around `EmpathyMCPServer`, which aggregates specialized mixins to provide different categories of functionality:

- **Memory operations** — Store, retrieve, search, and forget data across sessions through `MemoryHandlersMixin`
- **Workflow execution** — Access to Attune's workflow engine and utility functions via `WorkflowHandlersMixin`
- **Help system** — Contextual documentation lookup, template maintenance, and progressive depth support
- **Rate limiting** — In-process sliding-window rate limiter to prevent tool call abuse

## Tool categories

The server exposes four distinct tool groups:

| Category | Tools | Purpose |
|----------|-------|---------|
| **Workflow** | Execution and management tools | Run Attune workflows and access workflow metadata |
| **Utility** | `auth_status`, `telemetry_stats`, `attune_get_level`, `context_set` | Authentication management, telemetry, session context |
| **Help** | `help_lookup`, `help_maintain`, `help_init`, `help_status` | Progressive documentation with auto-advancing depth |
| **Memory** | `memory_store`, `memory_retrieve`, `memory_search`, `memory_forget` | Cross-session data persistence with security classification |

## Prompt and resource access

Beyond tools, the server provides:

- **Prompts** — Pre-configured workflows like `security-scan`, `test-gen`, and `cost-report` with structured arguments
- **Resources** — Live data endpoints for workflows list, auth configuration, and telemetry metrics

## Rate limiting design

The `RateLimiter` class implements a sliding-window approach with configurable limits (default: 60 calls per 60 seconds). It tracks calls per key, allowing different rate limits for different users or tool types without shared state between server instances.

## Entry point

The `create_server()` function instantiates a configured `EmpathyMCPServer` with workspace detection and user identification. The `main()` function serves as the MCP server entry point for command-line usage.
