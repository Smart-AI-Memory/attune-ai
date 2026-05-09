---
type: faq
name: uv-lock-can-drift-from-pyproject-toml-on-shared-branches
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about uv.lock can drift from pyproject.toml on shared branches?

## Answer

Saw this on origin/main — pyproject.toml had `attune-help>=0.5.1,<0.6` (cap added in PR #152) but uv.lock still showed `>=0.5.1` (no cap). The cap-adding PR didn't re-run `uv lock`, so the lockfile silently went out of sync.

**How to fix:**
- Always `uv lock --check` after pulling, and bundle uv.lock fixes with the next reasonable PR rather than treating them as noise

```
attune-help>=0.5.1,<0.6
```

## Related Topics
- **Error**: Detailed error: uv.lock can drift from pyproject.toml on shared branches
