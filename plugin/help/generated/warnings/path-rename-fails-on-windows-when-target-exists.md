---
type: warning
name: path-rename-fails-on-windows-when-target-exists
confidence: Verified
tags: [ci, windows, macos, python]
source: .claude/CLAUDE.md
---

# Warning: `Path.rename()` fails on Windows when target exists

## Condition

On Linux/macOS, `Path.rename()` atomically overwrites the target

## Risk

On Windows, it raises `FileExistsError` if the target already exists

## Mitigation

1. Use `Path.replace()` instead — it works cross-platform

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `Path.rename()` fails on Windows when target exists
