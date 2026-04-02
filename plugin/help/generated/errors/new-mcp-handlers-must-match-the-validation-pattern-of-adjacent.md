---
type: error
name: new-mcp-handlers-must-match-the-validation-pattern-of-adjacent
confidence: Verified
tags: [testing, security, claude-code]
source: .claude/CLAUDE.md
---

# Error: New MCP handlers must match the validation pattern of
  adjacent handlers

## Signature

New MCP handlers must match the validation pattern of
  adjacent handlers

## Root Cause

`_run_test_generation` was the only handler (out of 10) missing `_validate_file_path()` — easy to miss because the handler worked fine without it. When adding a new MCP tool handler, copy the validation block from the nearest similar handler, not just the workflow call pattern.

## Resolution

1. `_run_test_generation` was the only handler (out of 10) missing `_validate_file_path()` — easy to miss because the handler worked fine without it

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: New MCP handlers must match the validation pattern of
  adjacent handlers
- Task: Update test mocks and assertions
