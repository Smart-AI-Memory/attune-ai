---
type: faq
name: mypy-437-errors-was-stale-actual-count-was-2
tags: [git, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about myPy "437 errors" was stale — actual count was 2?

## Answer

The pre-commit comment said "437 pre-existing errors" but running mypy with the configured settings found only 2 unused `type: ignore` comments.

**How to fix:**
- Always re-run the tool before assuming old error counts are still accurate — they may have been fixed as a side effect of other refactors

```
type: ignore
```

## Related Topics
- **Error**: Detailed error: MyPy "437 errors" was stale — actual count was 2
