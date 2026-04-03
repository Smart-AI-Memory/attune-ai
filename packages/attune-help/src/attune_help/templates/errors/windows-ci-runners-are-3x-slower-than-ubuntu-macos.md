---
type: error
name: windows-ci-runners-are-3x-slower-than-ubuntu-macos
confidence: Verified
tags: [ci, testing, windows, macos]
source: .claude/CLAUDE.md
---

# Error: Windows CI runners are ~3x slower than Ubuntu/macOS

## Signature

Windows CI runners are ~3x slower than Ubuntu/macOS

## Root Cause

A 16k+ test suite that finishes in ~15min on macOS and ~17min on Ubuntu needs ~45min+ on Windows. Set `timeout-minutes` high enough (60) or the Windows matrix will always time out. Remember to update `test_timeout_values_are_reasonable` when changing the upper bound.

## Resolution

1. Set `timeout-minutes` high enough (60) or the Windows matrix will always time out

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Windows CI runners are ~3x slower than Ubuntu/macOS
- Task: Update test mocks and assertions
