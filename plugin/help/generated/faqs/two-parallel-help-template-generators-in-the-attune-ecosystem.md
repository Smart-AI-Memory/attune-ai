---
type: faq
name: two-parallel-help-template-generators-in-the-attune-ecosystem
tags: [security]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about two parallel help-template generators in the attune ecosystem drift silently?

## Answer

`src/attune/help/generator.py` (attune-ai's built-in) produces only the 3 core depths (concept/task/reference). `attune_author.generator` (attune-author's, invoked by `scripts/regenerate_help.py` or the new `--all-kinds` CLI flag) produces 11 kinds (adds error/faq/note/quickstart/tip/warning/comparison/ troubleshooting).

```
src/attune/help/generator.py
```

## Related Topics
- **Error**: Detailed error: Two parallel help-template generators in the attune
  ecosystem drift silently
