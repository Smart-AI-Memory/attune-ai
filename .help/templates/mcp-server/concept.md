---
feature: mcp-server
depth: concept
generated_at: 2026-04-04T02:25:50.285666+00:00
source_hash: 348722576514772ba6d54fddad36123bea1b0db23f2bf280ad6f23a2b54e679b
status: generated
---

# Mcp Server

## What

Model Context Protocol server and tool handlers

## Why

This feature provides mcp server functionality for the project.

## How

Key components:

- `MemoryHandlersMixin` — Mixin providing memory tool handlers for EmpathyMCPServer.

- `RateLimiter` — Simple sliding-window rate limiter.

- `EmpathyMCPServer` — MCP server for Attune AI workflows.

- `WorkflowHandlersMixin` — Mixin providing workflow tool handlers for EmpathyMCPServer.
