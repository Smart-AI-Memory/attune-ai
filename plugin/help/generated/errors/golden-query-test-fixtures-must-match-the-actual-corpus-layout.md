---
type: error
name: golden-query-test-fixtures-must-match-the-actual-corpus-layout
confidence: Verified
tags: [testing, security, imports]
source: .claude/CLAUDE.md
---

# Error: Golden-query test fixtures must match the actual
  corpus layout, not an assumed one

## Signature

Golden-query test fixtures must match the actual
  corpus layout, not an assumed one

## Root Cause

When writing a `queries.yaml` file for retrieval regression tests, cross-check every `expected_in_top_3` path against the installed corpus directory before running the benchmark. attune-help 0.5.1 has 43 `concepts/` files but no `concepts/tool-brainstorm.md` (and no brainstorm templates at all). A naive golden set that assumes one concept file per CLI feature will fail with `MISSING` errors until patched. Pre-validate with: `python3 -c "import yaml; from pathlib import Path; base=Path('<corpus>/templates'); data=yaml.safe_load (open('queries.yaml')); [print(f'MISSING {q[\"id\"]}: {p}') for q in data['queries'] for p in q.get ('expected_in_top_3',[]) if not (base/p).is_file()]"`

## Resolution

1. When writing a `queries.yaml` file for retrieval regression tests, cross-check every `expected_in_top_3` path against the installed corpus directory before running the benchmark

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
