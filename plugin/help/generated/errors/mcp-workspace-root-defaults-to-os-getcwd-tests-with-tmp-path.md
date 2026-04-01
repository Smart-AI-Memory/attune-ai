---
type: error
name: mcp-workspace-root-defaults-to-os-getcwd-tests-with-tmp-path
confidence: Verified
tags: [testing, claude-code]
source: .claude/CLAUDE.md
---

# Error: MCP `workspace_root` defaults to `os.getcwd()` — tests with
  `tmp_path` fail

## Signature

MCP `workspace_root` defaults to `os.getcwd()` — tests with
  `tmp_path` fail

## Root Cause

Tests that create files in `tmp_path` and pass them to MCP handlers will get "outside allowed directory" errors because the server defaults to the repo root.

## Resolution

1. pass `workspace_root=str(tmp_path)` when constructing the server in tests

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: MCP `workspace_root` defaults to `os.getcwd()` — tests with
  `tmp_path` fail
- Task: Update test mocks and assertions
