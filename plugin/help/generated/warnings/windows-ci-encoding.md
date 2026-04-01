---
type: warning
name: windows-ci-encoding
confidence: Verified
tags: [ci, windows, python]
source: .claude/CLAUDE.md
---

# Warning: Windows CI encoding

## Condition

Always use `encoding="utf-8"` on `Path.read_text()` calls

## Risk

Windows defaults to `cp1252` which fails on any file containing non-ASCII bytes

## Mitigation

1. Always use `encoding="utf-8"` on `Path.read_text()` calls

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Windows CI encoding
