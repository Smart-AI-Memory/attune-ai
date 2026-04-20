---
type: faq
feature: mcp-server
depth: faq
generated_at: 2026-04-20T01:21:43.968634+00:00
source_hash: cab70f0aeb1782a9a9523b0ae9f7a4efe73904a1e5f3f26ec70fc1f9dc7cd315
status: generated
---

# MCP server FAQ

## What is the MCP server?

The Model Context Protocol server that provides tools, prompts, and resources to Claude Code and other MCP clients. It handles authentication, telemetry, memory operations, help lookup, and workflow execution.

## When do I need to use it?

You use the MCP server whenever you work with Attune AI features through Claude Code. The server runs automatically when you have a `.mcp.json` file in your project root - you don't need to start it manually.

## What tools does it provide?

The server provides several categories of tools:

- **Help tools**: `help_lookup`, `help_maintain`, `help_init` for contextual documentation
- **Memory tools**: `memory_store`, `memory_retrieve`, `memory_search`, `memory_forget` for persistent data
- **Utility tools**: `auth_status`, `telemetry_stats`, `attune_get_level` for configuration and monitoring
- **Workflow tools**: Access to all available Attune workflows

## How do I start the server manually?

Run `uv run python -m attune.mcp.server` from your project directory. This is mainly useful for testing - Claude Code normally starts it automatically.

## What if the server isn't responding?

Check that your `.mcp.json` file exists and uses `uv run` instead of bare `python`. See the troubleshooting guide for MCP server issues for the complete diagnosis flow.

## Where is the server code?

The main implementation is in `src/attune/mcp/server.py`. Tool definitions are spread across several modules:
- Memory tools: `src/attune/mcp/memory.py`
- Prompt handling: `src/attune/mcp/prompts.py`
- Rate limiting: `src/attune/mcp/server.py`

**Tags:** `mcp`, `tools`, `server`
