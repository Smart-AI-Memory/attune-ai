---
type: faq
name: todo-counts-are-inflated-by-docstrings-and-prompt-strings
tags: [testing]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about TODO counts are inflated by docstrings and prompt strings describing TODO markers?

## Answer

a grep-based count of `TODO|FIXME` in attune-ai reported 54 items but triage showed only 1 real blocker. The inflation came from docstring text like "Generated Python test code as a string with TODO markers", prompt instructions like "Complete ALL TODOs with:", and example-output strings inside test generators.

```
TODO|FIXME
```

## Related Topics
- **Error**: Detailed error: TODO counts are inflated by docstrings and
  prompt strings describing TODO markers
