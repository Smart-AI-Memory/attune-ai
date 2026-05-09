---
type: faq
name: golden-query-test-fixtures-must-match-the-actual-corpus-layout
tags: [testing, security, imports]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about golden-query test fixtures must match the actual corpus layout, not an assumed one?

## Answer

When writing a `queries.yaml` file for retrieval regression tests, cross-check every `expected_in_top_3` path against the installed corpus directory before running the benchmark. attune-help 0.5.1 has 43 `concepts/` files but no `concepts/tool-brainstorm.md` (and no brainstorm templates at all).

```
queries.yaml
```

## Related Topics
- **Error**: Detailed error: Golden-query test fixtures must match the actual
  corpus layout, not an assumed one
