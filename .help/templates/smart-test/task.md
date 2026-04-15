---
type: task
feature: smart-test
depth: task
generated_at: 2026-04-14T14:42:29.119707+00:00
source_hash: fba1c2a2d71f311df2cc2ff7847b4a7e0af065ff31f1020498301ed7bcfe4c56
status: generated
---

# Work with smart test

Use smart test when you need to analyze code coverage gaps and automatically generate pytest tests for untested functions and classes.

## Prerequisites

- Access to the project source code
- Python environment with pytest and coverage tools installed
- Understanding of AST analysis and test generation workflows

## Identify your workflow

Choose the appropriate workflow based on your testing needs:

1. **For basic test generation**: Use `TestGenerationWorkflow` to analyze individual modules and generate tests using AST-based function analysis.

2. **For coverage auditing**: Use `TestAuditWorkflow` to audit existing test coverage and identify priority modules for testing.

3. **For parallel test generation**: Use `ParallelTestGenerationWorkflow` to generate tests for multiple low-coverage modules simultaneously.

## Generate tests for a single module

1. Import the test generation workflow:
   ```python
   from attune.workflows.test_gen.workflow import TestGenerationWorkflow
   ```

2. Initialize the workflow:
   ```python
   workflow = TestGenerationWorkflow()
   ```

3. Execute test generation for your target module:
   ```python
   result = workflow.execute(module_path="src/your_module.py")
   ```

4. Review the generated test report to verify coverage improvements.

## Audit test coverage across modules

1. Generate a coverage report using pytest:
   ```bash
   pytest --cov=src --cov-report=json:coverage.json
   ```

2. Parse the coverage data:
   ```python
   from attune.workflows.test_audit.coverage_parser import parse_coverage_json
   modules = parse_coverage_json("coverage.json")
   ```

3. Prioritize modules by coverage gaps:
   ```python
   from attune.workflows.test_audit.coverage_parser import prioritize_modules
   priority_modules = prioritize_modules(modules, min_threshold=50.0)
   ```

4. Run the audit workflow:
   ```python
   from attune.workflows.test_audit.workflow import TestAuditWorkflow
   audit = TestAuditWorkflow()
   audit_result = audit.execute(src_path="src/")
   ```

## Generate tests in parallel for multiple modules

1. Initialize the parallel workflow:
   ```python
   from attune.workflows.test_gen_parallel import ParallelTestGenerationWorkflow
   workflow = ParallelTestGenerationWorkflow()
   ```

2. Execute parallel test generation:
   ```python
   result = workflow.execute(
       top=50,  # Number of lowest-coverage modules to target
       batch_size=10,  # Modules to process simultaneously
       output_dir="tests/behavioral/generated"
   )
   ```

3. Verify the generated test files in your output directory.

## Verify test generation success

1. **Check generated test files**: Ensure test files appear in your specified output directory with valid Python syntax.

2. **Run the generated tests**: Execute `pytest tests/behavioral/generated/ -v` to confirm all generated tests pass.

3. **Measure coverage improvement**: Run `pytest --cov=src --cov-report=term-missing` to verify coverage has increased for targeted modules.

4. **Review test quality**: Check that generated tests include edge cases, error handling, and appropriate assertions for return types.

## Key files

- `src/attune/workflows/test_gen/workflow.py` - Main test generation workflow
- `src/attune/workflows/test_gen/ast_analyzer.py` - AST-based code analysis
- `src/attune/workflows/test_gen/test_templates.py` - Test code generation functions
- `src/attune/workflows/test_audit/workflow.py` - Coverage audit workflow
- `src/attune/workflows/test_gen_parallel.py` - Parallel test generation
