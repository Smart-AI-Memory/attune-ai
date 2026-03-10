# Simplify Sweep Plan

**Created:** 2026-03-04
**Owner:** Patrick Roebuck
**Status:** Planned
**Method:** `/simplify` on each file, commit per batch

---

## Strategy

Run `/simplify` on the 11 highest-complexity files in
dependency-safe order. Files with no downstream dependents
go first so later files can build on any extracted utilities.

### Ordering Rationale

1. **Leaf nodes first** — files nothing else imports from
   avoid cascading test failures.
2. **High branch density first** — files with the most
   branches per line benefit most from flattening.
3. **Good test coverage required** — every candidate has
   existing tests so `/simplify` changes can be verified
   immediately.
4. **Group by subsystem** — batch related files together
   (telemetry, memory, workflows) to catch cross-file
   reuse opportunities within the same commit.

---

## Execution Batches

### Batch 1: Telemetry subsystem (leaf nodes, highest complexity)

These three files form a dependency chain
(`storage.py` <- `usage_tracker.py` <- `telemetry_commands.py`)
so simplify bottom-up.

| Order | File | Lines | Branches | Tests | Reason |
|-------|------|-------|----------|-------|--------|
| 1 | `src/attune/models/telemetry/storage.py` | 577 | 87 | 102 | Highest branch density (0.15/line). Leaf — no deps on other candidates. Strong test coverage. |
| 2 | `src/attune/telemetry/usage_tracker.py` | 844 | 88 | 52 | Most branches overall. Depends on storage.py. Just wired to MCP server — clean now while fresh. |
| 3 | `src/attune/cli_commands/telemetry_commands.py` | 551 | 71 | 66 | CLI layer on top of the above two. Likely boilerplate that can shrink after they're simplified. |

**Commit after batch:** `refactor: simplify telemetry subsystem`
**Verify:** `pytest tests/unit/telemetry/ tests/unit/models/telemetry/ tests/unit/cli_commands/ -x`

---

### Batch 2: Memory subsystem

Independent of Batch 1. Two files, no cross-deps.

| Order | File | Lines | Branches | Tests | Reason |
|-------|------|-------|----------|-------|--------|
| 4 | `src/attune/memory/summary_index.py` | 583 | 73 | 18 | Fewer tests but self-contained. Good candidate for early-return flattening. |
| 5 | `src/attune/memory/redis_bootstrap.py` | 569 | 76 | 99 | High branches for a bootstrap module. Strong tests. Depends on cost_tracker but not other candidates. |

**Commit after batch:** `refactor: simplify memory subsystem`
**Verify:** `pytest tests/unit/memory/ -x`

---

### Batch 3: Core workflows (high user impact)

These are the user-facing workflow engines.

| Order | File | Lines | Branches | Tests | Reason |
|-------|------|-------|----------|-------|--------|
| 6 | `src/attune/workflows/code_review_pipeline.py` | 734 | 63 | 68 | Core workflow, no deps on other candidates. |
| 7 | `src/attune/workflows/doc_audit/checks.py` | 904 | 80 | 64 | 2nd largest file. Likely has repetitive check functions. |
| 8 | `src/attune/workflows/suggestions.py` | 843 | 59 | 44 | Large but lower branch density — may be mostly content. |

**Commit after batch:** `refactor: simplify core workflow files`
**Verify:** `pytest tests/unit/workflows/ -x`

---

### Batch 4: Supporting modules

| Order | File | Lines | Branches | Tests | Reason |
|-------|------|-------|----------|-------|--------|
| 9 | `src/attune/cost_tracker.py` | 634 | 55 | 59 | Most-changed file recently (8 commits). Stabilize it. |
| 10 | `src/attune/project_index/index.py` | 676 | 55 | 43 | 31 functions in one class — likely splitting opportunity. |
| 11 | `src/attune/workflows/test_gen/workflow.py` | 676 | 66 | 1879* | High branch count. *Test count inflated — `workflow.py` name matches many test files. Real coverage is the test_gen-specific tests. |

**Commit after batch:** `refactor: simplify cost tracker, project index, test gen`
**Verify:** `pytest tests/unit/test_cost_tracker.py tests/unit/project_index/ tests/unit/workflows/test_gen/ -x`

---

## Execution Protocol

For each file in order:

1. **Run** `/simplify` targeting the file
2. **Review** the three agent findings (reuse, quality,
   efficiency)
3. **Apply** fixes directly
4. **Run** the file's test suite to confirm no regressions
5. **Mark** the file complete in this plan

After each batch:

1. **Run** the batch verification command
2. **Commit** with the batch message
3. **Push** to remote

---

## Risk Mitigation

- Each batch is independent — if one batch creates issues,
  skip it and continue with the next
- Every file has existing tests — no blind refactoring
- `/simplify` uses three parallel review agents (reuse,
  quality, efficiency) which cross-check each other
- Commit per batch allows easy revert if CI fails

---

## What `/simplify` Checks

For reference, the three review agents look for:

**Reuse:** Existing utilities that could replace new code,
duplicated functionality, inline logic that matches existing
helpers.

**Quality:** Redundant state, parameter sprawl, copy-paste
with variation, leaky abstractions, stringly-typed code.

**Efficiency:** Unnecessary work, missed concurrency,
hot-path bloat, TOCTOU anti-patterns, memory leaks,
overly broad operations.

---

## Completion Tracker

| # | File | Status |
|---|------|--------|
| 1 | models/telemetry/storage.py | pending |
| 2 | telemetry/usage_tracker.py | pending |
| 3 | cli_commands/telemetry_commands.py | pending |
| 4 | memory/summary_index.py | pending |
| 5 | memory/redis_bootstrap.py | pending |
| 6 | workflows/code_review_pipeline.py | pending |
| 7 | workflows/doc_audit/checks.py | pending |
| 8 | workflows/suggestions.py | pending |
| 9 | cost_tracker.py | pending |
| 10 | project_index/index.py | pending |
| 11 | workflows/test_gen/workflow.py | pending |
