---
type: error
name: mypy-437-errors-was-stale-actual-count-was-2
confidence: Verified
tags: [git, python]
source: .claude/CLAUDE.md
---

# Error: MyPy "437 errors" was stale — actual count was 2

## Signature

437 pre-existing errors

## Root Cause

The pre-commit comment said "437 pre-existing errors" but running mypy with the configured settings found only 2 unused `type: ignore` comments. Always re-run the tool before assuming old error counts are still accurate — they may have been fixed as a side effect of other refactors.

## Resolution

1. Always re-run the tool before assuming old error counts are still accurate — they may have been fixed as a side effect of other refactors

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: MyPy "437 errors" was stale — actual count was 2
