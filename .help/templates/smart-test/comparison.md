---
type: comparison
name: smart-test-comparison
feature: smart-test
depth: comparison
generated_at: 2026-05-16T06:19:45.819669+00:00
source_hash: 2ed25e274258323117a16cf96fcb5bf0a40e45a9bb8c246d4abfdc74365cfabc
status: generated
---

# Smart Test vs Fix Test: Choosing the right testing tool

## Overview

Both smart-test and fix-test work on your test suite, but they solve opposite problems. Smart-test finds code that has no tests and writes them. Fix-test takes tests that already exist but are broken and repairs them. Running them together covers the full testing lifecycle — but picking the wrong one for your situation wastes time.

## Feature comparison

| Capability | smart-test | fix-test |
|---|---|---|
| **Primary job** | Finds untested code and generates pytest tests | Diagnoses failing tests and applies targeted fixes |
| **Starting condition** | Code exists; tests are absent or thin | Tests exist; they are failing |
| **Coverage analysis** | Yes — parses `coverage.json`, ranks modules by gap size and risk | No — works from pytest tracebacks, not coverage data |
| **AST-based code analysis** | Yes — `ASTFunctionAnalyzer` extracts function signatures, async status, raises, decorators, and complexity | No |
| **Output** | New `.py` test files with assertions, edge cases, parametrized inputs, and error-path tests | Repaired existing test files |
| **Parallelism** | `ParallelTestGenerationWorkflow` can process up to 200 low-coverage modules in configurable batches | Sequential: diagnose → fix → re-run, up to 3 retry attempts per test |
| **Retry / self-healing** | No — generates once; you review | Yes — reruns after each fix, reports what still needs manual attention |
| **Root-cause classification** | No | Yes — import errors, mock mismatches, assertion drift, type errors, missing fixtures, environment issues |
| **Best scale** | Bootstrapping coverage across a whole codebase or auditing a new module | Repairing a specific failing test or a broken CI pipeline |
| **Runs on** | Your Claude subscription — no extra API key | Your Claude subscription — no extra API key |

## How each tool works internally

**smart-test** runs two coordinated workflows:

1. `TestAuditWorkflow` — three subagents (`coverage-auditor`, `gap-analyzer`, `test-planner`) parse `coverage.json` via `parse_coverage_json()`, rank modules using `prioritize_modules()` (default threshold: 50% coverage), group them into subsystem batches with `group_into_batches()`, and produce a structured audit report.
2. `TestGenerationWorkflow` (or `ParallelTestGenerationWorkflow` for large codebases) — three subagents (`function-identifier`, `test-designer`, `test-writer`) analyze each module's AST, then write pytest functions with assertions, boundary values, and `@pytest.mark.parametrize` blocks.

**fix-test** runs a tighter loop: run the failing test, classify the traceback into a known root-cause category, apply a fix, re-run, and repeat up to three times. It does not generate new coverage — it restores tests that a refactor or dependency upgrade broke.

## Tradeoffs to know before you choose

- **smart-test is broader but not self-healing.** It can generate tests for 200 modules in parallel, but it won't automatically fix a test it generates that fails. Review generated tests before committing them.
- **fix-test is precise but narrow.** It excels at the tedious read-traceback → edit → re-run loop, but it can't tell you what's untested — only what's broken.
- **Coverage threshold matters for smart-test.** `prioritize_modules()` filters out modules already above 50% coverage by default. If your codebase is mostly well-covered, smart-test may produce a smaller report than you expect — that's by design, not a bug.
- **For legacy codebases with no tests at all,** smart-test is the clear starting point. Fix-test has nothing to work with until tests exist.

## Use smart-test when…

- You've written new public functions or modules and want tests before they ship.
- Your coverage has dropped below the 80% threshold and you need to find exactly what's missing.
- You're bootstrapping a test suite for a legacy codebase with little or no coverage.
- You want to verify that error paths and boundary conditions are exercised before a release.
- You need to generate tests across many modules at once — `ParallelTestGenerationWorkflow` handles batches of up to 200 modules.

## Use fix-test when…

- `pytest` is showing failures after a refactor, dependency upgrade, or large migration.
- CI is broken on tests you didn't intentionally change.
- You want the read-traceback → edit → re-run loop automated with automatic retry.
- You already have tests — they're just wrong after the code moved.

**If you're unsure:** check whether tests *exist* for the code in question. If they don't, start with smart-test. If they do but they're red, start with fix-test.

## Source files

- `src/attune/workflows/test_gen/**`
- `src/attune/workflows/test_audit/**`
- `src/attune/workflows/test_gen_parallel.py`

**Tags:** `tests`, `coverage`, `generation`
