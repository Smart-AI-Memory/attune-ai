---
type: warning
name: b904-raise-x-from-e-is-not-auto-fixable-by-ruff
confidence: Verified
tags: [python]
source: .claude/CLAUDE.md
---

# Warning: B904 (`raise X from e`) is not auto-fixable by ruff

## Condition

Despite `ruff check --fix`, B904 violations require manual edits

## Risk

Ignoring this guidance may cause: B904 (`raise X from e`) is not auto-fixable by ruff

## Mitigation

1. Use `from e` when the exception variable is captured, `from None` when suppressing the original

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: B904 (`raise X from e`) is not auto-fixable by ruff
