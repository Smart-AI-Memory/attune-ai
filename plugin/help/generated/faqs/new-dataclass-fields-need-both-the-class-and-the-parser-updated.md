---
type: faq
name: new-dataclass-fields-need-both-the-class-and-the-parser-updated
tags: [python]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about new dataclass fields need both the class AND the parser updated?

## Answer

Adding a field (e.g. `local_python`) to a dataclass only updates the in-memory model.

**How to fix:**
- Always grep for the parser function when adding a new dataclass field

```
local_python
```

## Related Topics
- **Error**: Detailed error: New dataclass fields need both the class AND the parser updated
