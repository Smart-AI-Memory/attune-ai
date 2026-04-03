---
type: error
name: splitting-text-on-breaks-backtick-quoted-code-references
confidence: Verified
tags: [python]
source: CLAUDE.md Lessons Learned
---

# Error: Splitting text on `.` breaks backtick-quoted code references

## Signature

Splitting text on `.` breaks backtick-quoted code references

## Root Cause

Naive `re.split(r"\.", text)` splits `Path.read_text()` into `Path` and `read_text()`.

## Resolution

1. replace dots inside backticks with a placeholder before splitting, then restore

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
