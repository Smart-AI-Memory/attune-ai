---
confidence: Verified
name: splitting-text-on-breaks-backtick-quoted-code-references
source: CLAUDE.md Lessons Learned
summary: This template documents how naive dot-splitting algorithms corrupt backtick-quoted
  code references and provides a mitigation strategy using placeholder substitution
  to preserve inline code spans during text tokenization.
tags:
- python
type: warning
---

# Warning: Splitting on `.` Breaks Backtick-Quoted Code References

## Condition

Using a naive `re.split(r"\.", text)` call will incorrectly split backtick-quoted identifiers that contain dots. For example, `` `Path.read_text()` `` gets split into two fragments — `` `Path `` and `` read_text()` `` — rather than being treated as a single token.

## Risk

Splitting on `.` without accounting for backtick-quoted code references corrupts inline code spans, producing malformed tokens that break downstream parsing, rendering, or text analysis.

## Mitigation

Before splitting, replace dots inside backtick-quoted spans with a placeholder string, perform the split, then restore the original dots. For example:

```python
import re

PLACEHOLDER = "\x00DOT\x00"

def safe_split_on_dot(text: str) -> list[str]:
    # Temporarily replace dots inside backtick spans
    protected = re.sub(
        r"`[^`]*`",
        lambda m: m.group(0).replace(".", PLACEHOLDER),
        text,
    )
    parts = protected.split(".")
    # Restore original dots within each part
    return [part.replace(PLACEHOLDER, ".") for part in parts]
```

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned).

## Related Topics

- [Error: Splitting on `.` breaks backtick-quoted code references](error-splitting-on-dot-breaks-backtick-quoted-code-references.md)
