---
type: reference
feature: smart-test
depth: reference
generated_at: 2026-04-14T14:42:45.299597+00:00
source_hash: fba1c2a2d71f311df2cc2ff7847b4a7e0af065ff31f1020498301ed7bcfe4c56
status: generated
---

# Smart Test reference

## Classes

### Test Generation Classes

| Class | Description |
|-------|-------------|
| `ASTFunctionAnalyzer` | AST-based function analyzer for accurate test generation |
| `TestGenerationWorkflow` | SDK-native test generation with three specialized subagents |
| `ParallelTestGenerationWorkflow` | Generate and complete behavioral tests in parallel using multi-tier LLMs |

### Test Audit Classes

| Class | Description |
|-------|-------------|
| `TestAuditWorkflow` | Autonomous test coverage audit with Agent SDK subagents |
| `TestGenerationTask` | Tracks the state of a single test generation task |

### Data Model Classes

| Class | Description |
|-------|-------------|
| `FunctionSignature` | Detailed function analysis for test generation |
| `ClassSignature` | Detailed class analysis for test generation |
| `ModuleCoverage` | Coverage data for a single module |

## Methods

### ASTFunctionAnalyzer

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `self` | None | Initialize analyzer |
| `analyze` | `self, code: str, file_path: str = ''` | `tuple[list[FunctionSignature], list[ClassSignature]]` | Analyze Python code and extract function and class signatures |
| `visit_FunctionDef` | `self, node: ast.FunctionDef` | `None` | Visit function definition node |
| `visit_AsyncFunctionDef` | `self, node: ast.AsyncFunctionDef` | `None` | Visit async function definition node |
| `visit_ClassDef` | `self, node: ast.ClassDef` | `None` | Visit class definition node |

### TestGenerationWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `self, **kwargs: Any` | `None` | Initialize workflow |
| `execute` | `self, **kwargs: Any` | `WorkflowResult` | Execute test generation workflow |

### TestAuditWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `execute` | `self, **kwargs: Any` | `WorkflowResult` | Execute test coverage audit |

### ParallelTestGenerationWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `default_context` | `cls, xml_config: dict \| None = None` | `WorkflowContext` | Create default workflow context |
| `discover_low_coverage_modules` | `self, top_n: int = 200` | `list[tuple[str, float]]` | Find modules with lowest test coverage |
| `analyze_module_structure` | `self, file_path: str` | `dict[str, Any]` | Analyze Python module structure using AST |
| `generate_test_template_with_ai` | `self, module_path: str, structure: dict[str, Any]` | `str` | Generate test template using AI |
| `complete_test_with_ai` | `self, template: str, module_path: str` | `str` | Complete test implementation using AI |
| `process_module_batch` | `self, modules: list[tuple[str, float]], output_dir: Path, batch_size: int = 10` | `list[TestGenerationTask]` | Process batch of modules for test generation |
| `execute` | `self, top: int = 200, batch_size: int = 10, output_dir: str = 'tests/behavioral/generated', **kwargs` | `WorkflowResult` | Execute parallel test generation workflow |

## Dataclass Fields

### FunctionSignature Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | - | Function name |
| `params` | `list[tuple[str, str, str \| None]]` | - | Parameter information (name, type, default) |
| `return_type` | `str \| None` | - | Function return type |
| `is_async` | `bool` | - | Whether function is async |
| `raises` | `set[str]` | - | Exception types the function raises |
| `has_side_effects` | `bool` | - | Whether function has side effects |
| `docstring` | `str \| None` | - | Function docstring |
| `complexity` | `int` | `1` | Function complexity score |
| `decorators` | `list[str]` | `field(default_factory=list)` | Function decorators |

### ClassSignature Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | - | Class name |
| `methods` | `list[FunctionSignature]` | - | Class methods |
| `init_params` | `list[tuple[str, str, str \| None]]` | - | Constructor parameters |
| `base_classes` | `list[str]` | - | Base class names |
| `docstring` | `str \| None` | - | Class docstring |
| `is_enum` | `bool` | `False` | Whether class is an enum |
| `is_dataclass` | `bool` | `False` | Whether class is a dataclass |
| `required_init_params` | `int` | `0` | Number of required constructor parameters |

### ModuleCoverage Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | `str` | - | Module file path |
| `stmts` | `int` | - | Total statements in module |
| `covered` | `int` | - | Number of covered statements |
| `missing_lines` | `list[int]` | `field(default_factory=list)` | Line numbers not covered by tests |
| `pct` | `float` | `0.0` | Coverage percentage |
| `priority` | `float` | `0.0` | Priority score for test generation |

### TestGenerationTask Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `module_path` | `str` | - | Path to module being tested |
| `coverage` | `float` | - | Current coverage percentage |
| `output_path` | `str` | - | Path where test file will be written |
| `status` | `str` | `'pending'` | Task status |

## Functions

| Function | Parameters | Returns | Raises | Description |
|----------|------------|---------|---------|-------------|
| `format_test_gen_report` | `result: dict, input_data: dict` | `str` | - | Format test generation output as a human-readable report |
| `generate_test_for_function` | `module: str, func: dict` | `str` | - | Generate executable tests for a function based on AST analysis |
| `generate_test_cases_for_params` | `params: list` | `dict` | - | Generate test cases based on parameter types |
| `get_type_assertion` | `return_type: str` | `str \| None` | - | Generate assertion for return type checking |
| `get_param_test_values` | `type_hint: str` | `list[str]` | - | Get test values for a single parameter based on its type |
| `generate_test_for_class` | `module: str, cls: dict` | `str` | - | Generate executable test class based on AST analysis |
| `main` | - | `None` | - | CLI entry point for test generation workflow |
| `parse_coverage_json` | `json_path: str` | `list[ModuleCoverage]` | `FileNotFoundError`, `ValueError` | Parse pytest-cov's coverage.json output |
| `prioritize_modules` | `modules: list[ModuleCoverage], min_threshold: float = 50.0` | `list[ModuleCoverage]` | - | Sort modules by priority and filter below threshold |
| `group_into_batches` | `modules: list[ModuleCoverage], max_batches: int = 5` | `list[dict]` | - | Group modules into batches by subsystem (package path) |

### Function Return Values

#### get_param_test_values

Returns test values for parameter types:
- `"test_value"`

### Exception Messages

| Function | Exception | Message |
|----------|-----------|---------|
| `parse_coverage_json` | `FileNotFoundError` | `'Coverage file not found: {...}'` |
| `parse_coverage_json` | `ValueError` | `'Invalid coverage JSON at {...}: {...}'` |
| `parse_coverage_json` | `ValueError` | `"Unexpected coverage JSON structure in {...}: 'files' key missing or not a dict"` |

## Constants

### Skip Patterns

| Constant | Values |
|----------|--------|
| `DEFAULT_SKIP_PATTERNS` | `.git`, `.hg`, `.svn`, `node_modules`, `bower_components`, `vendor`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.hypothesis`, `venv`, `.venv`, `env`, `.env`, `virtualenv`, `.virtualenv`, `.tox`, `.nox`, `build`, `dist`, `eggs`, `.eggs`, `site-packages`, `.idea`, `.vscode`, `migrations`, `alembic`, `_build`, `docs/_build` |

### Subagent Names

| Constant | Values |
|----------|--------|
| `SUBAGENT_NAMES` | `function-identifier`, `test-designer`, `test-writer` |
| `SUBAGENT_NAMES` (audit) | `coverage-auditor`, `gap-analyzer`, `test-planner` |

### System Prompts

| Constant | Description |
|----------|-------------|
| `SYSTEM_PROMPT` | Test generation orchestrator prompt |
| `AUDIT_SYSTEM_PROMPT` | Test coverage analyst prompt |
| `PLAN_SYSTEM_PROMPT` | Test planning expert prompt |
| `TASK_PROMPT_TEMPLATE` | Template for test generation tasks |
| `BATCH_TASK_TEMPLATE` | XML template for batch test tasks |
