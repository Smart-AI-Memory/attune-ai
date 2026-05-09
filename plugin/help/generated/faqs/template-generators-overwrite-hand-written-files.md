---
type: faq
name: template-generators-overwrite-hand-written-files
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about template generators overwrite hand-written files?

## Answer

The `generate_concept_templates.py` auto-discovery creates bland stubs that overwrite rich hand-written concept files. The `_CONCEPTS` curated list only protects system concepts, not `tool-*` skill concepts.

**How to fix:**
- check if the existing file has `auto-discovered` in its tags before overwriting — if not, it was hand-written and should be preserved

```
generate_concept_templates.py
```

## Related Topics
- **Error**: Detailed error: Template generators overwrite hand-written files
