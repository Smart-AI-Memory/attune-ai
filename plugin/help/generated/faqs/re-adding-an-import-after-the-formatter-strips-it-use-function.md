---
type: faq
name: re-adding-an-import-after-the-formatter-strips-it-use-function
tags: [imports, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about re-adding an import after the formatter strips it — use function-body usage as the anchor, not trust that "I'll import it first"?

## Answer

the edit-formatter cycle runs on every Edit, and ruff's F401 fix removes any import not currently referenced at module scope OR in a function body. The robust sequence when adding an import + new usage across edits: (1) add the *usage* in a function body first, (2) add the import in a follow-up edit — the name is now referenced so F401 leaves it alone.

## Related Topics
- **Error**: Detailed error: Re-adding an import after the formatter strips it —
  use function-body usage as the anchor, not trust that
  "I'll import it first"
