---
type: note
name: mcp-server
tags: [mcp, tools, server]
source: developer-guidance
---

# Note: MCP Server

## Context

The Attune AI MCP (Model Context Protocol) server bridges Claude and other AI clients to Attune's workflow system. It exposes tools for authentication, memory management, help system access, and workflow execution through a standardized protocol.

## Architecture

The MCP server uses a mixin-based design where `EmpathyMCPServer` composes functionality from specialized handler classes:

- **MemoryHandlersMixin** provides memory storage, retrieval, search, and deletion tools
- **WorkflowHandlersMixin** provides workflow execution tools
- **RateLimiter** implements sliding-window rate limiting for tool calls

The server exposes three types of MCP resources:

1. **Tools** — interactive functions like `auth_status`, `help_lookup`, and `memory_store`
2. **Prompts** — templated workflows like `security-scan` and `test-gen`
3. **Resources** — read-only data like workflow lists and telemetry

## Tool Categories

The server organizes its 15+ tools into logical groups:

- **Workflow tools** — execute Attune workflows and manage sessions
- **Utility tools** — authentication, telemetry, and session context
- **Help tools** — progressive documentation, template maintenance, and project help initialization
- **Memory tools** — cross-session data persistence and pattern matching

Each tool includes JSON schema validation and descriptive metadata for client discovery.

## Integration Point

Claude Desktop and Claude Code connect to the server via `.mcp.json` configuration files. The server runs as a subprocess, communicating over stdio using the MCP protocol for tool discovery, invocation, and result handling.
