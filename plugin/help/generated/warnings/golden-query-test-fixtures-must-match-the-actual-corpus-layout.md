---
type: warning
name: golden-query-test-fixtures-must-match-the-actual-corpus-layout
confidence: Verified
tags: [testing, security, imports]
source: .claude/CLAUDE.md
---

# Warning: Golden-query test fixtures must match the actual
  corpus layout, not an assumed one

## Condition

When writing a `queries.yaml` file for retrieval regression tests, cross-check every `expected_in_top_3` path against the installed corpus directory before running the benchmark

## Risk

A naive golden set that assumes one concept file per CLI feature will fail with `MISSING` errors until patched

## Mitigation

1. When writing a `queries.yaml` file for retrieval regression tests, cross-check every `expected_in_top_3` path against the installed corpus directory before running the benchmark

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Golden-query test fixtures must match the actual
  corpus layout, not an assumed one
