---
type: error
name: custom-mcp-stdio-loop-fails-claude-code-handshake
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Custom MCP stdio loop fails Claude Code handshake

## Signature

Custom MCP stdio loop fails Claude Code handshake

## Root Cause

A hand-rolled JSON-RPC `main_loop()` reading `sys.stdin` line by line does not implement the MCP initialization sequence (capability negotiation, `initialize` method). Claude Code's MCP client expects the standard protocol and silently drops the connection.

## Resolution

1. use the official `mcp.server.Server` + `mcp.server.stdio.stdio_server` which handles the full handshake

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Custom MCP stdio loop fails Claude Code handshake
