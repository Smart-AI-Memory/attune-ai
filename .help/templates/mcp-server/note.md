---
type: note
feature: mcp-server
depth: note
generated_at: 2026-04-20T01:22:10.978597+00:00
source_hash: cab70f0aeb1782a9a9523b0ae9f7a4efe73904a1e5f3f26ec70fc1f9dc7cd315
status: generated
---

# Note: MCP server

## Context

Attune AI's Model Context Protocol (MCP) server provides Claude Code with access to workflows, memory, help system, authentication, and telemetry through a structured tool interface. The server implements the MCP specification to expose Attune's capabilities as callable tools within Claude environments.

## Architecture

The MCP server uses a mixin-based design around the core `EmpathyMCPServer` class:

- **EmpathyMCPServer** — Main server implementation handling MCP protocol, tool routing, and rate limiting
- **MemoryHandlersMixin** — Provides memory store/retrieve/search/forget tools for cross-session data persistence
- **WorkflowHandlersMixin** — Exposes workflow execution tools for running Attune AI automation

The server exposes five tool categories:
1. **Workflow tools** — Execute Attune workflows directly from Claude
2. **Utility tools** — Authentication status, telemetry stats, session context management
3. **Help tools** — Progressive documentation lookup, template maintenance, project bootstrapping
4. **Memory tools** — Persistent storage for patterns, preferences, and cross-agent coordination
5. **Rate limiting** — Sliding-window limiter preventing API abuse

## Integration patterns

Claude Code discovers the server through `.mcp.json` configuration files in project roots. The server must run as `uv run python -m attune.mcp.server` to ensure correct package resolution and avoid Python environment conflicts that prevent tool availability.

Rate limiting applies per-tool with a default 60 calls per 60-second window. Voice interfaces skip memory and session tools (defined in `_VOICE_SKIP_TOOLS`) to avoid interrupting conversational flow.

## Source files

- `src/attune/mcp/server.py` — Core server and entry point
- `src/attune/mcp/memory_handlers.py` — Memory tool implementations
- `src/attune/mcp/workflow_handlers.py` — Workflow tool implementations
- `src/attune/mcp/prompts.py` — MCP prompt definitions
- `src/attune/mcp/tool_schemas.py` — Tool schema definitions
- `src/attune/mcp/rate_limiter.py` — Rate limiting implementation
