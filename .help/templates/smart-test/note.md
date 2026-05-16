---
type: note
name: smart-test-note
feature: smart-test
depth: note
generated_at: 2026-05-16T06:19:45.817118+00:00
source_hash: 2ed25e274258323117a16cf96fcb5bf0a40e45a9bb8c246d4abfdc74365cfabc
status: generated
---

# Note: smart-test internals

## How the feature is structured

Smart-test is implemented across two workflow packages:

- `src/attune/workflows/test_audit/` — the audit side: parses `coverage.json`, prioritizes modules by gap, and runs `TestAuditWorkflow`, which coordinates three Agent SDK subagents (`coverage-auditor`, `gap-analyzer`, `test-planner`).
- `src/attune/workflows/test_gen/` — the generation side: uses `ASTFunctionAnalyzer` to extract `FunctionSignature` and `ClassSignature` data from source, then writes pytest output via `TestGenerationWorkflow`, which drives its own three subagents (`function-identifier`, `test-designer`, `test-writer`).
- `src/attune/workflows/test_gen_parallel.py` — `ParallelTestGenerationWorkflow`, a higher-throughput variant that discovers low-coverage modules and processes them in configurable batches (default: 10 modules per batch, up to 200 modules).

## How the two sides compose

The audit and generation packages are designed to pipeline. `parse_coverage_json()` reads pytest-cov's `coverage.json` and returns a list of `ModuleCoverage` dataclasses. `prioritize_modules()` filters that list to modules below a coverage threshold (default: 50%) and sorts by gap size. `group_into_batches()` then groups the result by package path into up to five subsystem batches, which `TestGenerationWorkflow` or `ParallelTestGenerationWorkflow` consumes to drive test writing.

`ASTFunctionAnalyzer` sits at the boundary: it takes raw source and returns `FunctionSignature` and `ClassSignature` records that carry parameter types, return types, raised exceptions, async status, and cyclomatic complexity. `generate_test_for_function()` and `generate_test_for_class()` consume those records to produce executable pytest output.

## Audit orchestration

`TestAuditWorkflow` uses the system prompt in `AUDIT_SYSTEM_PROMPT` to instruct a coverage-analyst agent to review module prioritization, then `PLAN_SYSTEM_PROMPT` to group modules into logical batches. Each batch is rendered with `BATCH_TASK_TEMPLATE`, which embeds source path, missing line summary, coverage target, and test class stubs in a structured XML prompt.

The final report from `_TASK_PROMPT_TEMPLATE` has four sections: **Summary** (health score 0–100), **Coverage**, **Test Gaps**, and **Suggestions** (prioritized, with effort estimates).

## Source files

- `src/attune/workflows/test_audit/`
- `src/attune/workflows/test_gen/`
- `src/attune/workflows/test_gen_parallel.py`

**Tags:** `tests`, `coverage`, `generation`
