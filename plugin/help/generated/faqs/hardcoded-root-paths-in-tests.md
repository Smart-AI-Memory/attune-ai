---
type: faq
name: hardcoded-root-paths-in-tests
tags: [ci, testing]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Hardcoded `/root/` paths in tests?

## Answer



**Fix:**

- Avoid `/root/` in test fixtures — CI runners often execute as root, making the path accessible and triggering real I/O instead of the mocked error
- Use `tmp_path` instead

## Related Topics
- **Error**: Detailed error: Hardcoded `/root/` paths in tests
