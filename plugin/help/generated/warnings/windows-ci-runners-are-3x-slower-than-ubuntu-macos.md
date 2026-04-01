---
type: warning
name: windows-ci-runners-are-3x-slower-than-ubuntu-macos
confidence: Verified
tags: [ci, testing, windows, macos]
source: .claude/CLAUDE.md
---

# Warning: Windows CI runners are ~3x slower than Ubuntu/macOS

## Condition

A 16k+ test suite that finishes in ~15min on macOS and ~17min on Ubuntu needs ~45min+ on Windows

## Risk

Set `timeout-minutes` high enough (60) or the Windows matrix will always time out

## Mitigation

1. Set `timeout-minutes` high enough (60) or the Windows matrix will always time out

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Windows CI runners are ~3x slower than Ubuntu/macOS
