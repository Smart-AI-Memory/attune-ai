---
type: faq
name: naive-suffix-strip-stemming-fails-on-english-doubling-consonant
source: .claude/CLAUDE.md
---

# FAQ: Why does naive suffix-strip stemming fails on English doubling-consonant words?

## Answer

A simple stemmer that strips suffixes like `-ing`, `-ion`, `-ate`, `-s` correctly matches most singular/plural and verb-form pairs ("bugs"/"bug", "orchestrate"/ "orchestrator"). But words with doubled consonants before the suffix break: "planning" strips to "planni" (8 − 3 = 5 chars ≥ min), not "plan".

```
concepts/tool-planning.md
```

## Related Topics
- **Error**: Detailed error: Naive suffix-strip stemming fails on English
  doubling-consonant words
