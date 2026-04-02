---
type: warning
name: mypy-437-errors-was-stale-actual-count-was-2
confidence: Verified
tags: [git, python]
source: .claude/CLAUDE.md
---

# Warning: MyPy "437 errors" was stale — actual count was 2

## Condition

The pre-commit comment said "437 pre-existing errors" but running mypy with the configured settings found only 2 unused `type: ignore` comments

## Risk

The pre-commit comment said "437 pre-existing errors" but running mypy with the configured settings found only 2 unused `type: ignore` comments

## Mitigation

1. Always re-run the tool before assuming old error counts are still accurate — they may have been fixed as a side effect of other refactors

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: MyPy "437 errors" was stale — actual count was 2
