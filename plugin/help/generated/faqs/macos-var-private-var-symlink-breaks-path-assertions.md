---
name: macos-var-private-var-symlink-breaks-path-assertions
source: .claude/CLAUDE.md
summary: This developer help template explains why path assertions fail on macOS when
  comparing temporary file paths, because `Path.resolve()` follows the `/var` to `/private/var`
  symlink while `tempfile.NamedTemporaryFile` does not, and provides a solution to
  resolve both paths before comparison.
tags:
- testing
- security
- windows
- macos
- python
type: faq
---

# FAQ: Why Does the macOS `/var` → `/private/var` Symlink Break Path Assertions?

## Answer

`_validate_file_path()` calls `Path.resolve()`, which follows the macOS symlink from `/var/folders/...` to `/private/var/folders/...`. This creates a mismatch in tests: `tempfile.NamedTemporaryFile` returns the **unresolved** path via `f.name`, while the validation code returns the **resolved** path — causing path assertions to fail.

**Fix:**

Compare against the resolved path by wrapping `f.name` with `Path.resolve()`:

```python
assert result == str(Path(f.name).resolve())
```

## Related Topics

- **Error:** macOS `/var` → `/private/var` symlink breaks path assertions
