---
type: error
name: wizards-call-workflows-internally-they-are-not-duplicates
confidence: Verified
tags: [git, packaging]
source: .claude/CLAUDE.md
---

# Error: Wizards call workflows internally — they are not duplicates

## Signature

Wizards call workflows internally — they are not duplicates

## Root Cause

`attune wizard run` = interactive guided UX; `attune workflow run` = non-interactive multi-stage pipeline. `WizardInternalWorkflow` is the bridge. The website must explain this distinction or users assume overlap.

## Resolution

1. `attune wizard run` = interactive guided UX; `attune workflow run` = non-interactive multi-stage pipeline

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Wizards call workflows internally — they are not duplicates
