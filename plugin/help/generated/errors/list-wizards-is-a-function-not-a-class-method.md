---
type: error
name: list-wizards-is-a-function-not-a-class-method
confidence: Verified
tags: [imports]
source: .claude/CLAUDE.md
---

# Error: `list_wizards()` is a function, not a class method

## Signature

`list_wizards()` is a function, not a class method

## Root Cause

The wizard registry exposes `from attune.wizards import list_wizards` as a module-level function, not `WizardRegistry().list_wizards()`. The class `WizardRegistry` is not exported from `attune.wizards`.

## Resolution

1. The wizard registry exposes `from attune.wizards import list_wizards` as a module-level function, not `WizardRegistry().list_wizards()`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
