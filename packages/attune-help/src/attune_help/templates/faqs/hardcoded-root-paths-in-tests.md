---
type: faq
name: hardcoded-root-paths-in-tests
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about hardcoded /root/ paths in tests?

## Answer



**How to fix:**
- Avoid `/root/` in test fixtures — CI runners often execute as root, making the path accessible and triggering real I/O instead of the mocked error
- Use `tmp_path` instead

## Related Topics
- **Error**: Detailed error: Hardcoded `/root/` paths in tests
