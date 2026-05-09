---
type: error
name: re-adding-an-import-after-the-formatter-strips-it-use-function
confidence: Verified
tags: [imports, python]
source: .claude/CLAUDE.md
---

# Error: Re-adding an import after the formatter strips it —
  use function-body usage as the anchor, not trust that
  "I'll import it first"

## Signature

Re-adding an import after the formatter strips it —
  use function-body usage as the anchor, not trust that
  "I'll import it first"

## Root Cause

the edit-formatter cycle runs on every Edit, and ruff's F401 fix removes any import not currently referenced at module scope OR in a function body. The robust sequence when adding an import + new usage across edits: (1) add the *usage* in a function body first, (2) add the import in a follow-up edit — the name is now referenced so F401 leaves it alone. This extends the existing "Formatter strips imports" lesson with the concrete workaround: add usage first, import second, never the other way around.

## Resolution

1. the edit-formatter cycle runs on every Edit, and ruff's F401 fix removes any import not currently referenced at module scope OR in a function body

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Re-adding an import after the formatter strips it —
  use function-body usage as the anchor, not trust that
  "I'll import it first"
