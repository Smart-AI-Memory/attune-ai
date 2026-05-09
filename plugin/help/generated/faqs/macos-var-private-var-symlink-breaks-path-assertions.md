---
type: faq
name: macos-var-private-var-symlink-breaks-path-assertions
tags: [testing, security, windows, macos, python]
source: .claude/CLAUDE.md
---

# FAQ: Why does macOS /var → /private/var symlink breaks path assertions?

## Answer

`_validate_file_path()` calls `Path.resolve()`, which follows the macOS symlink from `/var/folders/...` to `/private/var/folders/...`. Tests using `tempfile.NamedTemporaryFile` get unresolved paths from `f.name` but resolved paths from validated code.

**How to fix:**
- assert against `str(Path(f.name).resolve())` instead of `f.name`

```
_validate_file_path()
```

## Related Topics
- **Error**: Detailed error: macOS `/var` → `/private/var` symlink breaks path assertions
