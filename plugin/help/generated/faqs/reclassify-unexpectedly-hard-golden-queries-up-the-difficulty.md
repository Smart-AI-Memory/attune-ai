---
type: faq
name: reclassify-unexpectedly-hard-golden-queries-up-the-difficulty
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about reclassify "unexpectedly hard" golden queries up the difficulty ladder instead of silencing them?

## Answer

When a golden query you labeled `medium` fails and the failure mode is the same as your known-hard cases (keyword collision with other features), relabel to `hard` rather than dropping the query or relaxing the assertion. This keeps the difficulty bucket honest for benchmarking.

**How to fix:**
- Use `pytest.mark.xfail(strict=False)` gated on `difficulty == "hard"` so hard queries document the gap without breaking CI and automatically turn into XPASS if a retriever upgrade starts passing them

```
pytest.mark.xfail(strict=False)
```

## Related Topics
- **Error**: Detailed error: Reclassify "unexpectedly hard" golden queries up the
  difficulty ladder instead of silencing them
