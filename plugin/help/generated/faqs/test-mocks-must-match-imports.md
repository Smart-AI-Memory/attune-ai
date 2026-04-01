---
type: faq
name: test-mocks-must-match-imports
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about test mocks must match imports?

## Answer

When a function changes its import path, all test mocks must be updated to match or side effects are silently ignored and assertions fail.

## Related Topics
- **Error**: Detailed error: Test mocks must match imports
