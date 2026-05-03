---
confidence: Verified
name: splitting-text-on-breaks-backtick-quoted-code-references
source: CLAUDE.md Lessons Learned
summary: This template documents a bug where naive text splitting on periods inadvertently
  fragments backtick-quoted code references, and provides a solution using placeholder
  substitution to preserve the references during splitting.
tags:
- python
type: error
---

# Error: Splitting Text on `.` Breaks Backtick-Quoted Code References

## Signature

Splitting text on `.` breaks backtick-quoted code references.

## Root Cause

A naive `re.split(r"\.", text)` call splits dot-qualified identifiers such as `` `Path.read_text()` `` into separate tokens — `Path` and `read_text()` — destroying the reference.

## Resolution

Before splitting, replace dots inside backtick-quoted spans with a placeholder (e.g., `\x00`), perform the split, then restore the original dots in each resulting token:

1. Substitute dots within backtick pairs: `` `Path.read_text()` `` → `` `Path\x00read_text()` ``
2. Split the modified text on literal `.`.
3. Restore the placeholder in each token: `\x00` → `.`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned).

## Related Topics

None generated yet.
