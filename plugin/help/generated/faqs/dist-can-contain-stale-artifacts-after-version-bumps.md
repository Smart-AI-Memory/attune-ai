---
type: faq
name: dist-can-contain-stale-artifacts-after-version-bumps
tags: [packaging]
source: CLAUDE.md Lessons Learned
---

# FAQ: What should I know about dist/ can contain stale artifacts after version bumps?

## Answer

The `dist/` directory is not automatically rebuilt when `pyproject.toml` version changes. Publishing stale artifacts uploads the old version to PyPI.

**How to fix:**
- Always run `rm -rf dist/ && uv run python -m build` before publishing and verify `ls dist/` shows the correct version

```
 directory is not automatically rebuilt when
```

## Related Topics
- **Error**: Detailed error: dist/ can contain stale artifacts after version bumps
