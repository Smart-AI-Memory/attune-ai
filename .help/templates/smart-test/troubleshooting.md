---
type: troubleshooting
feature: smart-test
depth: troubleshooting
generated_at: 2026-04-14T14:43:49.735267+00:00
source_hash: fba1c2a2d71f311df2cc2ff7847b4a7e0af065ff31f1020498301ed7bcfe4c56
status: generated
---

# Troubleshoot smart test

## Before you start

Find untested code and generate pytest tests with edge cases.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `FileNotFoundError: Coverage file not found` | Run `pytest --cov --cov-report=json` to generate coverage.json before using test generation |
| `ValueError: Invalid coverage JSON` | Verify coverage.json is valid JSON with `python -m json.tool coverage.json` |
| Generated tests have syntax errors | Check that AST analysis completed successfully by running `ASTFunctionAnalyzer().analyze(code, file_path)` on the target module |
| Test generation hangs or times out | Verify the target module doesn't have circular imports or module-level code that blocks during import |
| Generated tests are empty or minimal | Check if the target module has functions with type hints - the analyzer depends on type information for meaningful test cases |

## Step-by-step diagnosis

1. **Reproduce the failure with a single module.**
   Isolate the issue by testing one module at a time:
   ```bash
   python -c "from attune.workflows.test_gen import generate_test_for_function; print(generate_test_for_function('your.module', {'name': 'func_name'}))"
   ```

2. **Check coverage data availability.**
   Test generation requires existing coverage data:
   ```bash
   pytest --cov=your_package --cov-report=json
   ls -la coverage.json
   ```

3. **Verify AST analysis works.**
   Test the function analyzer directly on your target code:
   ```python
   from attune.workflows.test_gen.analyzer import ASTFunctionAnalyzer
   analyzer = ASTFunctionAnalyzer()
   with open('your_file.py') as f:
       functions, classes = analyzer.analyze(f.read(), 'your_file.py')
   print(f"Found {len(functions)} functions, {len(classes)} classes")
   ```

4. **Test workflow execution step by step.**
   Run the workflow components individually to isolate the failing step:
   - Coverage parsing: `parse_coverage_json('coverage.json')`
   - Module prioritization: `prioritize_modules(modules)`
   - Test template generation: `generate_test_template_with_ai(module_path, structure)`

## Common fixes

- **Missing coverage data:** Run `pytest --cov=your_package --cov-report=json` before test generation. The workflow requires coverage.json to identify low-coverage modules.

- **Invalid module paths:** Ensure the module paths in your coverage report match your actual file structure. Use absolute imports in your test target modules.

- **Type hint issues:** Add type hints to function parameters and return values. The test generator uses these for creating meaningful test cases:
  ```python
  # Before
  def process_data(data):
      return data.upper()

  # After
  def process_data(data: str) -> str:
      return data.upper()
  ```

- **Workflow configuration errors:** Check that your XML config includes the required subagent names. The TestGenerationWorkflow expects 'function-identifier', 'test-designer', and 'test-writer' subagents.

- **Memory issues with large codebases:** Use the batch processing feature for large projects:
  ```python
  workflow = ParallelTestGenerationWorkflow()
  result = workflow.execute(top=50, batch_size=5)  # Process fewer modules at once
  ```

## Source files

- `src/attune/workflows/test_gen/**`
- `src/attune/workflows/test_audit/**`
- `src/attune/workflows/test_gen_parallel.py`

**Tags:** `tests`, `coverage`, `generation`
