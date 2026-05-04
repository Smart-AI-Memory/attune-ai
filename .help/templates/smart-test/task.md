---
type: task
feature: smart-test
depth: task
generated_at: 2026-05-04T02:24:55.684375+00:00
source_hash: b86ac2f6972679ac24d0b4be339fa687398a6c09ee172583c670574d00d15c9f
status: generated
---

# Work with smart test

Use smart test when you need to modify how the system analyzes test coverage or generates pytest files.

## Prerequisites

- Access to the project source code
- Understanding of pytest and coverage analysis concepts

## Identify which component to modify

Smart test has three main workflows, each handling different responsibilities:

| Component | Purpose | Key files |
|-----------|---------|-----------|
| **Test audit** | Parse coverage reports and prioritize gaps | `src/attune/workflows/test_audit/` |
| **Test generation** | Generate pytest files from AST analysis | `src/attune/workflows/test_gen/` |
| **Parallel generation** | Orchestrate large-scale test generation | `src/attune/workflows/test_gen_parallel.py` |

Choose the component that matches your change:
- Coverage parsing issues → test audit workflow
- Generated test quality → test generation workflow
- Performance or batching → parallel generation workflow

## Modify coverage analysis

1. **Locate the parsing function you need to change:**
   - `parse_coverage_json()` — Reads pytest-cov JSON output
   - `prioritize_modules()` — Ranks modules by coverage gaps
   - `group_into_batches()` — Organizes modules into logical groups

2. **Update the ModuleCoverage dataclass** if you need new fields:
   ```python
   @dataclass
   class ModuleCoverage:
       path: str
       stmts: int
       covered: int
       missing_lines: list[int] = field(default_factory=list)
       pct: float = 0.0
       priority: float = 0.0
   ```

3. **Test your changes** with a real coverage.json file:
   ```bash
   pytest tests/ -k "coverage_parser"
   ```

## Modify test generation

1. **Choose the right generation function:**
   - `generate_test_for_function()` — Creates tests for individual functions
   - `generate_test_for_class()` — Creates test classes for class methods
   - `generate_test_cases_for_params()` — Generates parameter combinations

2. **Update the AST analyzer** if you need new function metadata:
   ```python
   # FunctionSignature tracks function details
   # ClassSignature tracks class details
   ```

3. **Modify test templates** by editing the string generation logic in each function

4. **Verify generated tests are valid** by running them:
   ```bash
   python -m pytest generated_test_file.py -v
   ```

## Modify parallel orchestration

1. **Update batch processing** in `ParallelTestGenerationWorkflow`:
   - `discover_low_coverage_modules()` — Finds modules needing tests
   - `process_module_batch()` — Handles batches in parallel
   - `analyze_module_structure()` — Extracts module information

2. **Adjust batch sizing** by modifying the `batch_size` parameter default

3. **Change AI model selection** in the workflow context

## Test your changes

Run the smart test skill to verify your modifications work end-to-end:

```bash
# Test coverage parsing
/smart-test src/your_module/ --approach gap-analysis

# Test generation
/smart-test src/your_module/ --approach generate-tests

# Test full workflow
/smart-test src/your_module/ --approach both
```

Your changes work correctly when the skill produces valid gap analysis reports and runnable pytest files.
