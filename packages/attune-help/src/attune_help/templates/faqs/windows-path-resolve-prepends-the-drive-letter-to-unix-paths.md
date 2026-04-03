---
type: faq
name: windows-path-resolve-prepends-the-drive-letter-to-unix-paths
tags: [testing, security, windows, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about windows Path.resolve() prepends the drive letter to Unix paths?

## Answer

`Path("/code").resolve()` on Windows returns `D:\code`, not `/code`. Tests that assert exact path strings passed through `_validate_file_path` fail on Windows CI.

**How to fix:**
- patch `_validate_file_path` in tests that verify handler logic (not path validation) so paths pass through unchanged

```
Path("/code").resolve()
```

## Related Topics
- **Error**: Detailed error: Windows `Path.resolve()` prepends the drive letter to Unix
  paths
