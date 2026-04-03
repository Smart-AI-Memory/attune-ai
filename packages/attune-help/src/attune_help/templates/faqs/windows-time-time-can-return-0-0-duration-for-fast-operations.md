---
type: faq
name: windows-time-time-can-return-0-0-duration-for-fast-operations
tags: [testing, windows]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about windows time.time() can return 0.0 duration for fast operations?

## Answer

On Windows 3.10-3.12, `time.time()` has ~15ms resolution. Tests asserting `execution_time > 0` fail when the operation completes within one tick.

**How to fix:**
- Use `time.perf_counter()` for sub-millisecond timing, or assert `>= 0` if the operation may be instant

```
time.time()
```

## Related Topics
- **Error**: Detailed error: Windows `time.time()` can return 0.0 duration for fast
  operations
