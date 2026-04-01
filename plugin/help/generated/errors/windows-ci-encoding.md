---
type: error
name: windows-ci-encoding
confidence: Verified
tags: [ci, windows, python]
source: .claude/CLAUDE.md
---

# Error: Windows CI encoding

## Signature

Windows CI encoding

## Root Cause

Always use `encoding="utf-8"` on `Path.read_text()` calls. Windows defaults to `cp1252` which fails on any file containing non-ASCII bytes.

## Resolution

1. Always use `encoding="utf-8"` on `Path.read_text()` calls

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Windows CI encoding
