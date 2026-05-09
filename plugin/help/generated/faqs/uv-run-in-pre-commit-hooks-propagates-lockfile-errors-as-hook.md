---
type: faq
name: uv-run-in-pre-commit-hooks-propagates-lockfile-errors-as-hook
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: Why does uv run in pre-commit hooks propagates lockfile errors as hook failures that look unrelated?

## Answer

The `check-docs-freshness` hook uses `uv run python scripts/check_docs_freshness.py`. When the lockfile has an unresolvable dep (e.g.

```
check-docs-freshness
```

## Related Topics
- **Error**: Detailed error: `uv run` in pre-commit hooks propagates lockfile
  errors as hook failures that look unrelated
