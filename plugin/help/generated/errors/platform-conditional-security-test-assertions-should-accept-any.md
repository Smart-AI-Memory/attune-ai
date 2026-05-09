---
type: error
name: platform-conditional-security-test-assertions-should-accept-any
confidence: Verified
tags: [testing, security, windows]
source: .claude/CLAUDE.md
---

# Error: Platform-conditional security-test assertions
  should accept any rejecting rule, not a specific
  error substring

## Signature

error

## Root Cause

attune-author's `test_author_docs_rejects_output_parent_in_system_dir` hard-coded `"system directory" in result["error"]`. On Unix, the Unix-anchored `_DANGEROUS_PREFIXES` list (`/etc`, `/sys`, `/proc`, …) fires and produces that substring. On Windows, `/etc/…` is neither a system dir nor under the workspace — the containment rule fires instead, returning `"outside allowed directory"`. Both rejections satisfy the same security contract: the write must not land.

## Resolution

1. widen the assertion to `"system directory" in err or "outside allowed directory" in err` and document in the docstring why either rule is acceptable

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Platform-conditional security-test assertions
  should accept any rejecting rule, not a specific
  error substring
- Task: Update test mocks and assertions
