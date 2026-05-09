---
type: faq
name: re-export-accessibility-tests-are-scattered-across-batch-files
tags: [testing]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about re-export accessibility tests are scattered across batch files?

## Answer

Tests like `test_format_code_review_report_accessible` appear in SDK agent tests, workflow tests, and coverage batch files. A single re-export removal can cascade through 5+ test files.

```
test_format_code_review_report_accessible
```

## Related Topics
- **Error**: Detailed error: Re-export accessibility tests are scattered across batch files
