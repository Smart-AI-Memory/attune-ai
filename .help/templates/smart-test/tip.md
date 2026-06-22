---
type: tip
name: smart-test-tip
feature: smart-test
depth: tip
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: b1325f36412cbd67b36481e0f150de834b91392f8fa17c843f8aecd357d18b07
status: generated
---

# Tip: Target modules below 50% coverage first

When you run `/smart-test`, specify the module you care about most rather than pointing it at the entire codebase. `prioritize_modules()` already filters out anything above the 50% coverage threshold and ranks the rest by a priority score — so the first items in the gap report are the ones that matter most.

**Why it's memorable:** A focused target means the three subagents (function-identifier, test-designer, test-writer) spend their cycles on your riskiest code, not on modules that are already well-covered.

**The tradeoff:** You may miss low-priority gaps in other modules. Run a broader audit with `TestAuditWorkflow` afterward to catch anything the scoped run skipped — but only after the high-risk gaps are closed.

## Source files

- `src/attune/workflows/test_audit/**`
- `src/attune/workflows/test_gen/**`
- `src/attune/workflows/test_gen_parallel.py`

**Tags:** `tests`, `coverage`, `generation`
