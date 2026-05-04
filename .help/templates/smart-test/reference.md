---
type: reference
feature: smart-test
depth: reference
generated_at: 2026-05-04T02:25:12.897458+00:00
source_hash: b86ac2f6972679ac24d0b4be339fa687398a6c09ee172583c670574d00d15c9f
status: generated
---

# Smart Test reference

Analyze test coverage gaps and generate pytest tests for untested code paths.

## Classes

| Class | Description |
|-------|-------------|
| `ModuleCoverage` | Coverage data for a single module |
| `TestAuditWorkflow` | Autonomous test coverage audit with Agent SDK subagents |
| `ASTFunctionAnalyzer` | AST-based function analyzer for accurate test generation |
| `FunctionSignature` | Detailed function analysis for test generation |
| `ClassSignature` | Detailed class analysis for test generation |
| `TestGenerationWorkflow` | SDK-native test generation with three specialized subagents |
| `TestGenerationTask` | Tracks the state of a single test generation task |
| `ParallelTestGenerationWorkflow` | Generate and complete behavioral tests in parallel using multi-tier LLMs |

### ModuleCoverage Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | `str` | | Module file path |
| `stmts` | `int` | | Total statements in module |
| `covered` | `int` | | Number of covered statements |
| `missing_lines` | `list[int]` | `[]` | Line numbers without coverage |
| `pct` | `float` | `0.0` | Coverage percentage |
| `priority` | `float` | `0.0` | Priority score for test generation |

### FunctionSignature Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | | Function name |
| `params` | `list[tuple[str, str, str | None]]` | | Parameters as (name, type, default) tuples |
| `return_type` | `str | None` | | Return type annotation |
| `is_async` | `bool` | | Whether function is async |
| `raises` | `set[str]` | | Exception types that can be raised |
| `has_side_effects` | `bool` | | Whether function has side effects |
| `docstring` | `str | None` | | Function docstring |
| `complexity` | `int` | `1` | Cyclomatic complexity score |
| `decorators` | `list[str]` | `[]` | Applied decorators |

### ClassSignature Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | | Class name |
| `methods` | `list[FunctionSignature]` | | Class methods |
| `init_params` | `list[tuple[str, str, str | None]]` | | Constructor parameters |
| `base_classes` | `list[str]` | | Inherited classes |
| `docstring` | `str | None` | | Class docstring |
| `is_enum` | `bool` | `False` | Whether class is an enum |
| `is_dataclass` | `bool` | `False` | Whether class is a dataclass |
| `required_init_params` | `int` | `0` | Number of required constructor parameters |

### TestGenerationTask Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `module_path` | `str` | | Path to module being tested |
| `coverage` | `float` | | Current coverage percentage |
| `output_path` | `str` | | Path where test file will be written |
| `status` | `str` | `'pending'` | Task status |

## Methods

### TestAuditWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `execute` | `**kwargs: Any` | `WorkflowResult` | Run coverage audit with subagents |

### ASTFunctionAnalyzer

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | | | Initialize analyzer |
| `analyze` | `code: str, file_path: str = ''` | `tuple[list[FunctionSignature], list[ClassSignature]]` | Extract functions and classes from code |
| `visit_FunctionDef` | `node: ast.FunctionDef` | `None` | Visit function definition node |
| `visit_AsyncFunctionDef` | `node: ast.AsyncFunctionDef` | `None` | Visit async function definition node |
| `visit_ClassDef` | `node: ast.ClassDef` | `None` | Visit class definition node |

### TestGenerationWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `**kwargs: Any` | | Initialize workflow |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Generate tests using subagents |

### ParallelTestGenerationWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `default_context` | `xml_config: dict | None = None` | `WorkflowContext` | Create default workflow context |
| `discover_low_coverage_modules` | `top_n: int = 200` | `list[tuple[str, float]]` | Find modules with lowest coverage |
| `analyze_module_structure` | `file_path: str` | `dict[str, Any]` | Extract module structure for test generation |
| `generate_test_template_with_ai` | `module_path: str, structure: dict[str, Any]` | `str` | Generate test template using AI |
| `complete_test_with_ai` | `template: str, module_path: str` | `str` | Complete test implementation using AI |
| `process_module_batch` | `modules: list[tuple[str, float]], output_dir: Path, batch_size: int = 10` | `list[TestGenerationTask]` | Process multiple modules in parallel |
| `execute` | `top: int = 200, batch_size: int = 10, output_dir: str = 'tests/behavioral/generated', **kwargs` | `WorkflowResult` | Execute parallel test generation |

## Functions

| Function | Parameters | Returns | Raises | Description |
|----------|------------|---------|---------|-------------|
| `parse_coverage_json` | `json_path: str` | `list[ModuleCoverage]` | `FileNotFoundError`, `ValueError` | Parse pytest-cov's coverage.json output |
| `prioritize_modules` | `modules: list[ModuleCoverage], min_threshold: float = 50.0` | `list[ModuleCoverage]` | | Sort modules by priority and filter below threshold |
| `group_into_batches` | `modules: list[ModuleCoverage], max_batches: int = 5` | `list[dict]` | | Group modules into batches by subsystem |
| `format_test_gen_report` | `result: dict, input_data: dict` | `str` | | Format test generation output as human-readable report |
| `generate_test_for_function` | `module: str, func: dict` | `str` | | Generate executable tests for a function based on AST analysis |
| `generate_test_cases_for_params` | `params: list` | `dict` | | Generate test cases based on parameter types |
| `get_type_assertion` | `return_type: str` | `str | None` | | Generate assertion for return type checking |
| `get_param_test_values` | `type_hint: str` | `list[str]` | | Get test values for a single parameter based on its type |
| `generate_test_for_class` | `module: str, cls: dict` | `str` | | Generate executable test class based on AST analysis |
| `main` | | `None` | | CLI entry point for test generation workflow |

### Exception Messages

| Exception | Message |
|-----------|---------|
| `FileNotFoundError` | `'Coverage file not found: {...}'` |
| `ValueError` | `'Invalid coverage JSON at {...}: {...}'` |
| `ValueError` | `"Unexpected coverage JSON structure in {...}: 'files' key missing or not a dict"` |

### get_param_test_values Return Values

```python
['"test_value"']
```

## Constants

| Constant | Values | Description |
|----------|--------|-------------|
| `DEFAULT_SKIP_PATTERNS` | `['.git', '.hg', '.svn', 'node_modules', 'bower_components', 'vendor', '__pycache__', '.mypy_cache', '.pytest_cache', '.ruff_cache', '.hypothesis', 'venv', '.venv', 'env', '.env', 'virtualenv', '.virtualenv', '.tox', '.nox', 'build', 'dist', 'eggs', '.eggs', 'site-packages', '.idea', '.vscode', 'migrations', 'alembic', '_build', 'docs/_build']` | Directories to skip during analysis |
