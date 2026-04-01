---
type: faq
name: windows-ci-runners-are-3x-slower-than-ubuntu-macos
tags: [ci, testing, windows, macos]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about windows CI runners are ~3x slower than Ubuntu/macOS?

## Answer

A 16k+ test suite that finishes in ~15min on macOS and ~17min on Ubuntu needs ~45min+ on Windows. Remember to update `test_timeout_values_are_reasonable` when changing the upper bound.

**How to fix:**
- Set `timeout-minutes` high enough (60) or the Windows matrix will always time out

```
timeout-minutes
```

## Related Topics
- **Error**: Detailed error: Windows CI runners are ~3x slower than Ubuntu/macOS
