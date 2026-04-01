---
type: faq
name: untracked-scripts-break-ci-when-tests-import-them
tags: [ci, testing, imports, git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: Why do I get `ModuleNotFoundError` (untracked scripts break CI when tests import them)?

## Answer

The `test_sync_agents_skills.py` test imported from `scripts/sync_agents_skills.py` which existed locally but was never committed. CI failed with `ModuleNotFoundError` on all 12 platforms.

**How to fix:**
- Always `git status` scripts referenced by tests before pushing

```
test_sync_agents_skills.py
```

## Related Topics
- **Error**: Detailed error: Untracked scripts break CI when tests import them
