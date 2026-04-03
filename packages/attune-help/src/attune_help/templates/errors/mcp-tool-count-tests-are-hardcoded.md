---
type: error
name: mcp-tool-count-tests-are-hardcoded
confidence: Verified
tags: [testing, claude-code]
source: .claude/CLAUDE.md
---

# Error: MCP tool count tests are hardcoded

## Signature

MCP tool count tests are hardcoded

## Root Cause

When adding new MCP tools to `server.py`, grep tests for the old tool count (e.g., `assert len(tools) == 22`). The assertion in `test_mcp_memory_tools.py` is the main one but others may exist. Also check workflow description assertions if descriptions were changed.

## Resolution

1. When adding new MCP tools to `server.py`, grep tests for the old tool count (e.g., `assert len(tools) == 22`)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
