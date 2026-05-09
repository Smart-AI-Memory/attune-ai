---
type: warning
name: reclassify-unexpectedly-hard-golden-queries-up-the-difficulty
confidence: Verified
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# Warning: Reclassify "unexpectedly hard" golden queries up the
  difficulty ladder instead of silencing them

## Condition

When a golden query you labeled `medium` fails and the failure mode is the same as your known-hard cases (keyword collision with other features), relabel to `hard` rather than dropping the query or relaxing the assertion

## Risk

When a golden query you labeled `medium` fails and the failure mode is the same as your known-hard cases (keyword collision with other features), relabel to `hard` rather than dropping the query or relaxing the assertion

## Mitigation

1. Use `pytest.mark.xfail(strict=False)` gated on `difficulty == "hard"` so hard queries document the gap without breaking CI and automatically turn into XPASS if a retriever upgrade starts passing them

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Reclassify "unexpectedly hard" golden queries up the
  difficulty ladder instead of silencing them
