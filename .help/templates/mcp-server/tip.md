---
type: tip
feature: mcp-server
depth: tip
generated_at: 2026-04-19T18:49:46.340603+00:00
source_hash: 4d53983ae8928abce86e5e58e1d186acd20ca65e85b505d31acc051216daed33
status: generated
---

# Tip: Use EmpathyMCPServer for tool registration, not direct schemas

Register tools through the `EmpathyMCPServer` class instead of calling schema functions directly. The server handles rate limiting, workspace context, and user identification automatically.

Tools are rate-limited with a sliding window (60 calls per minute by default) to prevent runaway automation. Direct schema access bypasses this protection and can overwhelm downstream services or APIs.

**Tags:** `mcp`, `tools`, `server`
