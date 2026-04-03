---
type: error
name: b904-raise-x-from-e-is-not-auto-fixable-by-ruff
confidence: Verified
tags: [python]
source: .claude/CLAUDE.md
---

# Error: B904 (`raise X from e`) is not auto-fixable by ruff

## Signature

B904 (`raise X from e`) is not auto-fixable by ruff

## Root Cause

Despite `ruff check --fix`, B904 violations require manual edits. Use `from e` when the exception variable is captured, `from None` when suppressing the original. After fixing all violations, remove B904 from the ruff ignore list to enforce going forward.

## Resolution

1. Use `from e` when the exception variable is captured, `from None` when suppressing the original

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: B904 (`raise X from e`) is not auto-fixable by ruff
