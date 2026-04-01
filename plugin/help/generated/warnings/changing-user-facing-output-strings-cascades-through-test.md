---
type: warning
name: changing-user-facing-output-strings-cascades-through-test
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Warning: Changing user-facing output strings cascades through test
  assertions

## Condition

Replacing "Workflow completed" with voice layer personality messaging broke 6 assertions across 4 test classes

## Risk

This is broader than just error messages — any output text change

## Mitigation

1. Replacing "Workflow completed" with voice layer personality messaging broke 6 assertions across 4 test classes

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Changing user-facing output strings cascades through test
  assertions
