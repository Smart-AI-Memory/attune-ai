---
type: faq
name: mcp-workspace-root-defaults-to-os-getcwd-tests-with-tmp-path
tags: [testing, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: Why does MCP workspace_root defaults to os.getcwd() — tests with tmp_path fail?

## Answer

Tests that create files in `tmp_path` and pass them to MCP handlers will get "outside allowed directory" errors because the server defaults to the repo root.

**How to fix:**
- pass `workspace_root=str(tmp_path)` when constructing the server in tests

```
workspace_root=str(tmp_path)
```

## Related Topics
- **Error**: Detailed error: MCP `workspace_root` defaults to `os.getcwd()` — tests with
  `tmp_path` fail
