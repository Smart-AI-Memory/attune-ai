---
type: error
name: changing-user-facing-output-strings-cascades-through-test
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Error: Changing user-facing output strings cascades through test
  assertions

## Signature

Changing user-facing output strings cascades through test
  assertions

## Root Cause

Replacing "Workflow completed" with voice layer personality messaging broke 6 assertions across 4 test classes. When changing any user-facing output string in a shared path (like `_print_workflow_result`), grep the entire test suite for the old string before considering the change done. This is broader than just error messages — any output text change.

## Resolution

1. Replacing "Workflow completed" with voice layer personality messaging broke 6 assertions across 4 test classes

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Changing user-facing output strings cascades through test
  assertions
- Task: Update test mocks and assertions
