---
type: error
feature: smart-test
depth: error
generated_at: 2026-04-14T14:43:13.910169+00:00
source_hash: fba1c2a2d71f311df2cc2ff7847b4a7e0af065ff31f1020498301ed7bcfe4c56
status: generated
---

# Smart Test errors

Errors that occur during automated test generation, coverage analysis, and AST-based code inspection for Python projects.

## Common error signatures

- `FileNotFoundError: Coverage file not found: {...}` — Coverage JSON file is missing or path is incorrect
- `ValueError: Invalid coverage JSON at {...}: {...}` — Coverage JSON contains malformed data
- `ValueError: Unexpected coverage JSON structure in {...}: 'files' key missing or not a dict` — Coverage JSON has unexpected structure
- `SyntaxError` during AST parsing — Source code contains invalid Python syntax
- `AttributeError` when analyzing AST nodes — Code structure doesn't match expected patterns
- Import errors when generating test templates — Target modules can't be imported for analysis

## Where errors originate

Test generation failures typically start in these components:

- **Coverage parsing**: `parse_coverage_json()` fails when pytest-cov output is missing, corrupted, or has unexpected structure
- **AST analysis**: `ASTFunctionAnalyzer.analyze()` encounters syntax errors or unsupported language constructs in source files
- **Template generation**: `generate_test_for_function()` and `generate_test_for_class()` fail when function signatures contain complex type hints or decorators
- **Workflow execution**: `TestGenerationWorkflow.execute()` and `ParallelTestGenerationWorkflow.execute()` encounter filesystem permissions issues or module import failures

## How to diagnose

1. **Verify coverage data exists**. Check that `coverage.json` exists at the expected path and contains valid JSON. Run `pytest --cov=your_package --cov-report=json` to regenerate if needed.

2. **Test AST parsing separately**. If analysis fails, try parsing the problematic file with Python's `ast` module directly: `ast.parse(open('file.py').read())`. Syntax errors in the source will surface immediately.

3. **Check module importability**. Ensure target modules can be imported from the test generation environment. Missing dependencies or circular imports cause template generation to fail silently.

4. **Validate file permissions**. Test generation workflows write output files. Verify the target directory exists and is writable, especially when using `output_dir` parameter.

5. **Enable debug logging**. Set logging level to DEBUG before running workflows to see detailed AST traversal and template generation steps.

## Source files

- `src/attune/workflows/test_gen/**`
- `src/attune/workflows/test_audit/**`
- `src/attune/workflows/test_gen_parallel.py`

**Tags:** `tests`, `coverage`, `generation`
