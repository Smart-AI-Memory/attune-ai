---
type: quickstart
feature: smart-test
depth: quickstart
generated_at: 2026-04-14T14:44:23.036453+00:00
source_hash: fba1c2a2d71f311df2cc2ff7847b4a7e0af065ff31f1020498301ed7bcfe4c56
status: generated
---

# Generate tests for untested Python code

Analyze your codebase and automatically create pytest tests for functions with low coverage.

```python
from attune.workflows.test_gen import TestGenerationWorkflow

# Generate tests for untested functions
workflow = TestGenerationWorkflow()
result = workflow.execute(path="src/myproject")
print(result.content)
```

## Generate tests in three steps

1. **Run the test generator on your source code:**
   ```python
   from attune.workflows.test_gen import TestGenerationWorkflow

   workflow = TestGenerationWorkflow()
   result = workflow.execute(path="src/myproject")
   ```

2. **View the generated test files:** The workflow creates pytest-compatible test files in your specified output directory. Each test includes edge cases and parameter validation.

3. **Run your new tests:** Execute `pytest tests/` to verify the generated tests pass and check your new coverage percentage.

## Expected output

The workflow returns a structured report showing:
- Functions analyzed and test files created
- Coverage gaps identified and addressed
- Specific test cases generated for each function

```
## Summary
Analyzed 15 functions, designed 45 test cases, generated 8 test files.

## Coverage
Current coverage: 67% → Target coverage: 85%

## Test Gaps
- payment_processor.py: Missing error handling tests
- user_validator.py: No edge case coverage for email validation
```

## Next steps

Run `ParallelTestGenerationWorkflow` to generate tests for multiple modules simultaneously and speed up coverage improvement across your entire codebase.
