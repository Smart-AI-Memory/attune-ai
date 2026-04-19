---
type: faq
feature: mcp-server
depth: faq
generated_at: 2026-04-19T18:49:24.767780+00:00
source_hash: 4d53983ae8928abce86e5e58e1d186acd20ca65e85b505d31acc051216daed33
status: generated
---

# MCP Server FAQ

## What is the MCP server?

The MCP server implements the Model Context Protocol to connect Claude Code with Attune AI workflows, memory, and help tools.

## When should I use it?

You need the MCP server when using Claude Code with Attune AI features like workflow execution, contextual help, memory storage, or authentication management.

## How do I start the MCP server?

Call `create_server()` from `src/attune/mcp/server.py` to get an `EmpathyMCPServer` instance, then run it according to your MCP client's requirements.

## What tools does it provide?

The server provides workflow tools, utility tools (auth, telemetry, session management), help tools (progressive documentation), and memory tools (store/retrieve/search/forget).

## How do I configure it for Claude Code?

Create a `.mcp.json` file in your project root pointing to `uv run python -m attune.mcp.server` to ensure proper package resolution.

## Why isn't Claude Code connecting to my MCP server?

Check that `.mcp.json` exists, uses `uv run` (not bare `python`), and that the attune package is installed. Restart Claude Code after fixing configuration issues.

## How do I debug MCP server issues?

Run `pytest -k "mcp" -v` to test the components, then manually start the server with `uv run python -m attune.mcp.server` to see startup errors.

## Where are the source files?

- `src/attune/mcp/**`

**Tags:** `mcp`, `tools`, `server`
