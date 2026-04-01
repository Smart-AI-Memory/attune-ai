---
type: warning
name: hardcoded-strings-in-method-bodies-survive-class-attribute
confidence: Verified
source: .claude/CLAUDE.md
---

# Warning: Hardcoded strings in method bodies survive class attribute
  renames

## Condition

Changing `name = "deep-review-sdk"` to `"deep-review"` on the class didn't fix a hardcoded `"workflow": "deep-review-sdk"` string inside `execute()`

## Risk

Ignoring this guidance may cause: Hardcoded strings in method bodies survive class attribute
  renames

## Mitigation

1. Changing `name = "deep-review-sdk"` to `"deep-review"` on the class didn't fix a hardcoded `"workflow": "deep-review-sdk"` string inside `execute()`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Hardcoded strings in method bodies survive class attribute
  renames
