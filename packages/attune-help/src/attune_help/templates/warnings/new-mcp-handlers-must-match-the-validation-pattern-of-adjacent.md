---
type: warning
name: new-mcp-handlers-must-match-the-validation-pattern-of-adjacent
confidence: Verified
tags: [testing, security, claude-code]
source: .claude/CLAUDE.md
---

# Warning: New MCP handlers must match the validation pattern of
  adjacent handlers

## Condition

`_run_test_generation` was the only handler (out of 10) missing `_validate_file_path()` — easy to miss because the handler worked fine without it

## Risk

`_run_test_generation` was the only handler (out of 10) missing `_validate_file_path()` — easy to miss because the handler worked fine without it

## Mitigation

1. `_run_test_generation` was the only handler (out of 10) missing `_validate_file_path()` — easy to miss because the handler worked fine without it

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: New MCP handlers must match the validation pattern of
  adjacent handlers
