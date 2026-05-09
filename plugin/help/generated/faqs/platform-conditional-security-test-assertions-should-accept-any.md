---
type: faq
name: platform-conditional-security-test-assertions-should-accept-any
tags: [testing, security, windows]
source: .claude/CLAUDE.md
---

# FAQ: Why does platform-conditional security-test assertions should accept any rejecting rule, not a specific error substring?

## Answer

attune-author's `test_author_docs_rejects_output_parent_in_system_dir` hard-coded `"system directory" in result["error"]`. On Unix, the Unix-anchored `_DANGEROUS_PREFIXES` list (`/etc`, `/sys`, `/proc`, …) fires and produces that substring.

**How to fix:**
- widen the assertion to `"system directory" in err or "outside allowed directory" in err` and document in the docstring why either rule is acceptable

```
test_author_docs_rejects_output_parent_in_system_dir
```

## Related Topics
- **Error**: Detailed error: Platform-conditional security-test assertions
  should accept any rejecting rule, not a specific
  error substring
