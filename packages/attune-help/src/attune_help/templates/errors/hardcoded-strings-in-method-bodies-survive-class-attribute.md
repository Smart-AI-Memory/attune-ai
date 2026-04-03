---
type: error
name: hardcoded-strings-in-method-bodies-survive-class-attribute
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: Hardcoded strings in method bodies survive class attribute
  renames

## Signature

Hardcoded strings in method bodies survive class attribute
  renames

## Root Cause

Changing `name = "deep-review-sdk"` to `"deep-review"` on the class didn't fix a hardcoded `"workflow": "deep-review-sdk"` string inside `execute()`. After renaming a class attribute, always grep for the old value across the entire source file to catch hardcoded duplicates in method bodies and metadata dicts.

## Resolution

1. Changing `name = "deep-review-sdk"` to `"deep-review"` on the class didn't fix a hardcoded `"workflow": "deep-review-sdk"` string inside `execute()`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Hardcoded strings in method bodies survive class attribute
  renames
