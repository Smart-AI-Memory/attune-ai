---
type: error
name: path-rename-fails-on-windows-when-target-exists
confidence: Verified
tags: [ci, windows, macos, python]
source: .claude/CLAUDE.md
---

# Error: `Path.rename()` fails on Windows when target exists

## Signature

FileExistsError

## Root Cause

On Linux/macOS, `Path.rename()` atomically overwrites the target. On Windows, it raises `FileExistsError` if the target already exists. Use `Path.replace()` instead — it works cross-platform. This caused 2 Windows-only CI failures in `help/session.py` where the atomic-write pattern wrote to `.json.tmp` then renamed to `.json`.

## Resolution

1. Use `Path.replace()` instead — it works cross-platform

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `Path.rename()` fails on Windows when target exists
