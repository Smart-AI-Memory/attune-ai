---
type: warning
name: re-adding-an-import-after-the-formatter-strips-it-use-function
confidence: Verified
tags: [imports, python]
source: .claude/CLAUDE.md
---

# Warning: Re-adding an import after the formatter strips it —
  use function-body usage as the anchor, not trust that
  "I'll import it first"

## Condition

the edit-formatter cycle runs on every Edit, and ruff's F401 fix removes any import not currently referenced at module scope OR in a function body

## Risk

Ignoring this guidance may cause: Re-adding an import after the formatter strips it —
  use function-body usage as the anchor, not trust that
  "I'll import it first"

## Mitigation

1. the edit-formatter cycle runs on every Edit, and ruff's F401 fix removes any import not currently referenced at module scope OR in a function body

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Re-adding an import after the formatter strips it —
  use function-body usage as the anchor, not trust that
  "I'll import it first"
