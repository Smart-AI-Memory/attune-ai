---
type: faq
name: smart-test-faq
feature: smart-test
depth: faq
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: b1325f36412cbd67b36481e0f150de834b91392f8fa17c843f8aecd357d18b07
status: generated
---

# Smart Test FAQ

## What does smart-test do?

It finds untested code in your Python project and generates pytest tests to cover it — including edge cases, error paths, and boundary values.

## When should I use it?

Use smart-test when you want to catch coverage gaps before they become tech debt: after writing new modules, when coverage drops below your threshold, before a release, or to bootstrap tests for legacy code that has none.

If you need to fix tests that are already written but failing, use fix-test instead.

## What kinds of gaps does it find?

Smart-test identifies untested public functions, uncovered branches (`if`/`else` paths), exception handlers that are never triggered, boundary values (empty inputs, `None`, zero, max-length), and input combinations that would need `@pytest.mark.parametrize` coverage.

## What does it generate?

It produces a coverage gap report ranked by risk, working pytest functions with assertions, boundary and `None`-handling tests, exception tests, and parametrized test cases for input combinations.

## Do I need an API key or extra budget?

No. Smart-test runs on your existing Claude subscription.

## Will it generate tests for my entire codebase at once?

Not by default. If you don't specify a target, it asks which module to focus on and whether you want gap analysis, test generation, or both. If you include the path upfront — for example, `/smart-test src/auth/` — it skips the questions and runs immediately.

## How does it decide which modules to prioritize?

It parses your `coverage.json` output (produced by pytest-cov), scores each module by coverage percentage and statement count, and filters out modules above a minimum threshold (default 50%). Modules are then grouped by subsystem for batch processing.

## What gets skipped automatically?

Directories like `.git`, `__pycache__`, `venv`, `migrations`, `build`, `dist`, and similar non-source paths are excluded by default. You don't need to configure this.

## Where is the source code for this feature?

- `src/attune/workflows/test_audit/` — coverage parsing, prioritization, and audit workflow
- `src/attune/workflows/test_gen/` — test generation workflow and AST analysis
- `src/attune/workflows/test_gen_parallel.py` — parallel generation across multiple modules

## How do I debug smart-test if something goes wrong?

Run `pytest -k "smart-test" -v` first to check whether the underlying tests pass. If they do but your output looks wrong, verify that your `coverage.json` file exists and contains a top-level `files` key — `parse_coverage_json()` raises a `ValueError` if that key is missing or malformed.

**Tags:** `testing`, `coverage`, `generation`
