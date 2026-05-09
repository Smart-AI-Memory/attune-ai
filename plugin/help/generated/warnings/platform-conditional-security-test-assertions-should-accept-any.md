---
type: warning
name: platform-conditional-security-test-assertions-should-accept-any
confidence: Verified
tags: [testing, security, windows]
source: .claude/CLAUDE.md
---

# Warning: Platform-conditional security-test assertions
  should accept any rejecting rule, not a specific
  error substring

## Condition

attune-author's `test_author_docs_rejects_output_parent_in_system_dir` hard-coded `"system directory" in result["error"]`

## Risk

attune-author's `test_author_docs_rejects_output_parent_in_system_dir` hard-coded `"system directory" in result["error"]`

## Mitigation

1. widen the assertion to `"system directory" in err or "outside allowed directory" in err` and document in the docstring why either rule is acceptable

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Platform-conditional security-test assertions
  should accept any rejecting rule, not a specific
  error substring
