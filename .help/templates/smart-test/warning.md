---
type: warning
name: smart-test-warning
feature: smart-test
depth: warning
generated_at: 2026-05-16T06:19:45.805234+00:00
source_hash: 2ed25e274258323117a16cf96fcb5bf0a40e45a9bb8c246d4abfdc74365cfabc
status: generated
---

# Smart Test cautions

## What to watch for

Smart-test reads your coverage data, analyzes module structure with AST parsing, and generates pytest tests — all in a pipeline where a bad input at one stage silently degrades output at the next. The risks below are specific to that pipeline.

## Risk areas

### `parse_coverage_json()` raises on missing or malformed coverage files

`parse_coverage_json()` raises `FileNotFoundError` if the coverage file doesn't exist and `ValueError` if the JSON is structurally unexpected — including a distinct error if the top-level `files` key is missing. If you run smart-test before generating coverage data (for example, before any `pytest --cov` run), you'll hit this immediately.

**Mitigation:** Run `pytest --cov=<your-src-dir> --cov-report=json` before invoking smart-test. Confirm `coverage.json` exists at the path you're passing.

---

### `prioritize_modules()` silently drops modules below the threshold

`prioritize_modules()` filters out any module whose coverage is below `min_threshold` (default `50.0`). Modules with very low coverage — often the ones most in need of tests — are excluded from the output without any warning.

**Mitigation:** If the gap report looks shorter than expected, check whether your lowest-coverage modules are being filtered. You can lower or override `min_threshold` to include them.

---

### `group_into_batches()` caps output at five batches

`group_into_batches()` groups modules by package path and caps the result at `max_batches=5`. In a large codebase, modules beyond that limit are silently omitted from test generation.

**Mitigation:** For codebases with many low-coverage subsystems, run smart-test targeting specific subdirectories rather than the whole project at once. `ParallelTestGenerationWorkflow` supports a `top` parameter (default `200`) and a `batch_size` parameter (default `10`) for finer control.

---

### AST analysis produces incomplete signatures for dynamically constructed code

`ASTFunctionAnalyzer` derives function signatures — parameters, return types, raised exceptions, decorators — from static AST inspection. Dynamically generated functions, heavily decorated callables, or code using `__getattr__` tricks may yield incomplete `FunctionSignature` or `ClassSignature` data, which causes `generate_test_for_function()` and `generate_test_for_class()` to produce tests with missing assertions or wrong instantiation patterns.

**Mitigation:** Review generated tests for dynamic or heavily decorated functions before committing them. Treat generated tests as a starting point, not a finished suite.

---

### Generated tests use `"test_value"` as the default string parameter

`get_param_test_values()` returns `"test_value"` as the literal test value for string parameters. Tests generated for functions that validate, transform, or reject specific string formats will pass the generation step but may assert incorrect behavior.

**Mitigation:** After generation, search the output for `"test_value"` and replace it with domain-appropriate inputs — especially for functions that parse, sanitize, or pattern-match strings.

---

### Private helpers change without notice

Internal functions and constants prefixed with `_` (including `_SUBAGENT_NAMES`, `_SYSTEM_PROMPT`, and `_TASK_PROMPT_TEMPLATE` in both workflow packages) are not part of the public API and can change between releases. Both `TestAuditWorkflow` and `TestGenerationWorkflow` expose only their `execute()` method as a stable entry point.

**Mitigation:** Depend on `execute()` and the public exports listed in each package's `__all__`. Avoid referencing underscore-prefixed names in downstream code or tests.

## Source files

- `src/attune/workflows/test_gen/**`
- `src/attune/workflows/test_audit/**`
- `src/attune/workflows/test_gen_parallel.py`

**Tags:** `tests`, `coverage`, `generation`
