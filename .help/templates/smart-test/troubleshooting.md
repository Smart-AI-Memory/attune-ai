---
type: troubleshooting
name: smart-test-troubleshooting
feature: smart-test
depth: troubleshooting
generated_at: 2026-05-16T06:19:45.807645+00:00
source_hash: 2ed25e274258323117a16cf96fcb5bf0a40e45a9bb8c246d4abfdc74365cfabc
status: generated
---

# Troubleshoot smart-test

## Symptom table

| If you observe | Check |
|----------------|-------|
| `FileNotFoundError: Coverage file not found` | Confirm `coverage.json` exists at the path you passed. Run `pytest --cov --cov-report=json` first to generate it. |
| `ValueError: Invalid coverage JSON` or `'files' key missing` | Open the JSON file and verify it is valid and produced by pytest-cov. A truncated or empty file causes this error in `parse_coverage_json()`. |
| Coverage gap report is empty or missing modules | Check that `prioritize_modules()` isn't filtering everything out — the default `min_threshold` is `50.0`. Modules above 50% coverage are excluded by design. |
| Generated tests reference the wrong function signatures | The `ASTFunctionAnalyzer` parsed stale source. Confirm you're pointing smart-test at the current file, not a compiled `.pyc` or cached copy. |
| No tests generated for a module | Verify the module isn't matched by `DEFAULT_SKIP_PATTERNS` (e.g., paths containing `migrations`, `alembic`, `venv`, `build`, or `dist` are skipped automatically). |
| Parallel workflow stalls or produces no output | `ParallelTestGenerationWorkflow` batches up to 200 modules in groups of 10 by default. If `discover_low_coverage_modules()` returns an empty list, coverage data is missing or all modules exceed the threshold. |
| Workflow exits with no report | Check that `TestAuditWorkflow.execute()` or `TestGenerationWorkflow.execute()` received valid `src_path` / `path` kwargs — omitting them produces no subagent output to synthesize. |

## Diagnose the problem

Work through these steps in order — each one is cheaper than the next.

### 1. Confirm coverage data exists

Smart-test reads `coverage.json` produced by pytest-cov. If that file is missing or malformed, nothing downstream works.

```bash
pytest --cov=src --cov-report=json
ls -lh coverage.json   # should be non-empty
python -c "import json; json.load(open('coverage.json'))"  # validates JSON
```

If the last command raises an error, regenerate the file before proceeding.

### 2. Check what modules are being picked up

Run `parse_coverage_json()` directly to confirm the parser sees your modules:

```python
from src.attune.workflows.test_audit.coverage_parser import parse_coverage_json, prioritize_modules

modules = parse_coverage_json("coverage.json")
print(f"{len(modules)} modules parsed")

prioritized = prioritize_modules(modules, min_threshold=0.0)  # lower threshold to see everything
for m in prioritized[:10]:
    print(m.path, m.pct)
```

If `modules` is empty, the `files` key is missing from your coverage JSON — regenerate it. If `prioritized` is much shorter than `modules`, your modules are above the 50% threshold and filtered out intentionally.

### 3. Check DEFAULT_SKIP_PATTERNS

If a module you expect to see is absent from the gap report, verify its path doesn't match a skip pattern:

```python
from src.attune.workflows.test_gen.test_templates import DEFAULT_SKIP_PATTERNS

target = "src/your/module/path"
matched = [p for p in DEFAULT_SKIP_PATTERNS if p in target]
print(matched)  # non-empty means the module is being skipped
```

Common surprises: paths containing `migrations`, `alembic`, `build`, or `dist`.

### 4. Verify AST analysis on the target module

If tests are generated with wrong signatures, check what `ASTFunctionAnalyzer` actually sees:

```python
from src.attune.workflows.test_gen.test_templates import ASTFunctionAnalyzer

analyzer = ASTFunctionAnalyzer()
code = open("src/your/module.py").read()
functions, classes = analyzer.analyze(code, file_path="src/your/module.py")
for f in functions:
    print(f.name, f.params, f.return_type)
```

If the output doesn't match the current source, you're reading the wrong file or a stale version.

### 5. Run the related tests

```bash
pytest -k "smart_test or test_audit or test_gen" -v
```

A failing test here often pins down exactly which component is misbehaving and provides fixtures you can reuse when writing a reproduction case.

## Common fixes

**Coverage JSON is missing or stale**
Generate it before running smart-test:
```bash
pytest --cov=src --cov-report=json
```

**All modules filtered out by `min_threshold`**
The default threshold is `50.0` — modules with ≥50% coverage are excluded from the gap report. If you want to generate tests for well-covered modules too, call `prioritize_modules()` with a higher threshold or pass `min_threshold=0.0` to include everything:
```python
prioritize_modules(modules, min_threshold=0.0)
```

**Module skipped by DEFAULT_SKIP_PATTERNS**
Move generated or vendored code out of `src/`, or restructure so the path doesn't contain a skip token (`migrations`, `build`, `dist`, `venv`, etc.). You cannot override `DEFAULT_SKIP_PATTERNS` without modifying the source.

**Wrong function signatures in generated tests**
This means `ASTFunctionAnalyzer` parsed the wrong file. Pass the absolute path to `analyze()` and confirm the file reflects your latest changes — if you've edited the module but haven't saved, or if your editor writes to a temp file, the analyzer sees stale code.

**Workflow kwargs missing**
`TestAuditWorkflow.execute()` requires `src_path`; `TestGenerationWorkflow.execute()` requires `path`. Omitting either produces an empty report with no subagent output. Check your invocation:
```python
workflow = TestAuditWorkflow()
result = workflow.execute(src_path="src/")  # required
```

**Parallel workflow produces no output**
`ParallelTestGenerationWorkflow.discover_low_coverage_modules()` returns an empty list when no modules fall below the coverage threshold, or when coverage data is absent entirely. Confirm coverage data exists (step 1) and that at least one module has a gap worth filling.

**Dependency version mismatch**
Smart-test uses pytest-cov to produce its input data. If the JSON structure changes across versions, `parse_coverage_json()` raises `ValueError`. Run:
```bash
pip show pytest-cov
```
and confirm you're on a version that produces a `files`-keyed JSON object.

## Source files

- `src/attune/workflows/test_audit/` — `TestAuditWorkflow`, `parse_coverage_json()`, `prioritize_modules()`, `group_into_batches()`
- `src/attune/workflows/test_gen/` — `TestGenerationWorkflow`, `ASTFunctionAnalyzer`, `generate_test_for_function()`, `generate_test_for_class()`
- `src/attune/workflows/test_gen_parallel.py` — `ParallelTestGenerationWorkflow`

**Tags:** `tests`, `coverage`, `generation`

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 45 (code fence) | error | `from src.attune.workflows.test_audit.coverage_parser import …` — module not importable |
| Line 62 (code fence) | error | `from src.attune.workflows.test_gen.test_templates import …` — module not importable |
