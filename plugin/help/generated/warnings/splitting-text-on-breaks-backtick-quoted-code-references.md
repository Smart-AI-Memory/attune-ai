---
type: warning
name: splitting-text-on-breaks-backtick-quoted-code-references
confidence: Verified
tags: [python]
source: CLAUDE.md Lessons Learned
---

# Warning: Splitting text on `.` breaks backtick-quoted code references

## Condition

Naive `re.split(r"\.", text)` splits `Path.read_text()` into `Path` and `read_text()`

## Risk

Ignoring this guidance may cause: Splitting text on `.` breaks backtick-quoted code references

## Mitigation

1. replace dots inside backticks with a placeholder before splitting, then restore

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Splitting text on `.` breaks backtick-quoted code references
