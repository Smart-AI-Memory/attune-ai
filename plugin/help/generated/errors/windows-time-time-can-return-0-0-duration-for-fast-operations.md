---
type: error
name: windows-time-time-can-return-0-0-duration-for-fast-operations
confidence: Verified
tags: [testing, windows]
source: .claude/CLAUDE.md
---

# Error: Windows `time.time()` can return 0.0 duration for fast
  operations

## Signature

Windows `time.time()` can return 0.0 duration for fast
  operations

## Root Cause

On Windows 3.10-3.12, `time.time()` has ~15ms resolution. Tests asserting `execution_time > 0` fail when the operation completes within one tick. Use `time.perf_counter()` for sub-millisecond timing, or assert `>= 0` if the operation may be instant.

## Resolution

1. Use `time.perf_counter()` for sub-millisecond timing, or assert `>= 0` if the operation may be instant

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Windows `time.time()` can return 0.0 duration for fast
  operations
- Task: Update test mocks and assertions
