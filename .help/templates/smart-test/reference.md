---
type: reference
name: smart-test-reference
feature: smart-test
depth: reference
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: b1325f36412cbd67b36481e0f150de834b91392f8fa17c843f8aecd357d18b07
status: generated
---

# Smart Test reference

Find coverage gaps in your codebase and generate pytest tests with edge cases, boundary values, and error paths.

## Classes

| Class | Description |
|-------|-------------|
| `ModuleCoverage` | Coverage data for a single module. |
| `TestAuditWorkflow` | Autonomous test coverage audit with Agent SDK subagents. |
| `ASTFunctionAnalyzer` | AST-based function analyzer for accurate test generation. |
| `FunctionSignature` | Detailed function analysis for test generation. |
| `ClassSignature` | Detailed class analysis for test generation. |
| `TestGenerationWorkflow` | SDK-native test generation with three specialized subagents. |
| `TestGenerationTask` | Tracks the state of a single test generation task. |
| `ParallelTestGenerationWorkflow` | Generate and complete behavioral tests in parallel using multi-tier LLMs. |

### `ModuleCoverage` fields

`ModuleCoverage` is a dataclass.

| Field | Type | Default |
|-------|------|---------|
| `path` | `str` | — |
| `stmts` | `int` | — |
| `covered` | `int` | — |
| `missing_lines` | `list[int]` | `field(default_factory=list)` |
| `pct` | `float` | `0.0` |
| `priority` | `float` | `0.0` |

### `FunctionSignature` fields

`FunctionSignature` is a dataclass.

| Field | Type | Default |
|-------|------|---------|
| `name` | `str` | — |
| `params` | `list[tuple[str, str, str \| None]]` | — |
| `return_type` | `str \| None` | — |
| `is_async` | `bool` | — |
| `raises` | `set[str]` | — |
| `has_side_effects` | `bool` | — |
| `docstring` | `str \| None` | — |
| `complexity` | `int` | `1` |
| `decorators` | `list[str]` | `field(default_factory=list)` |

### `ClassSignature` fields

`ClassSignature` is a dataclass.

| Field | Type | Default |
|-------|------|---------|
| `name` | `str` | — |
| `methods` | `list[FunctionSignature]` | — |
| `init_params` | `list[tuple[str, str, str \| None]]` | — |
| `base_classes` | `list[str]` | — |
| `docstring` | `str \| None` | — |
| `is_enum` | `bool` | `False` |
| `is_dataclass` | `bool` | `False` |
| `required_init_params` | `int` | `0` |

### `TestGenerationTask` fields

`TestGenerationTask` is a dataclass.

| Field | Type | Default |
|-------|------|---------|
| `module_path` | `str` | — |
| `coverage` | `float` | — |
| `output_path` | `str` | — |
| `status` | `str` | `'pending'` |

### `TestAuditWorkflow` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `self, *, system_prompt_suffix: str = '', **kwargs: Any` | `None` | Initializes the workflow with an optional system prompt suffix. |
| `execute` | `self, **kwargs: Any` | `WorkflowResult` | Runs the coverage audit and returns a structured result. |

### `ASTFunctionAnalyzer` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `self` | — | Initializes the analyzer. |
| `analyze` | `self, code: str, file_path: str = ''` | `tuple[list[FunctionSignature], list[ClassSignature]]` | Parses source code and returns extracted function and class signatures. |
| `visit_FunctionDef` | `self, node: ast.FunctionDef` | `None` | Visits a function definition node during AST traversal. |
| `visit_AsyncFunctionDef` | `self, node: ast.AsyncFunctionDef` | `None` | Visits an async function definition node during AST traversal. |
| `visit_ClassDef` | `self, node: ast.ClassDef` | `None` | Visits a class definition node during AST traversal. |

### `TestGenerationWorkflow` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `self, **kwargs: Any` | — | Initializes the workflow. |
| `execute` | `self, **kwargs: Any` | `WorkflowResult` | Runs test generation with three specialized subagents and returns a structured result. |

### `ParallelTestGenerationWorkflow` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `default_context` | `cls, xml_config: dict \| None = None` | `WorkflowContext` | Returns the default workflow context, optionally configured with XML. |
| `discover_low_coverage_modules` | `self, top_n: int = 200` | `list[tuple[str, float]]` | Returns the top N modules ranked by lowest coverage. |
| `analyze_module_structure` | `self, file_path: str` | `dict[str, Any]` | Analyzes a module's structure and returns a summary dict. |
| `generate_test_template_with_ai` | `self, module_path: str, structure: dict[str, Any]` | `str` | Generates a test file template for the given module using an LLM. |
| `complete_test_with_ai` | `self, template: str, module_path: str` | `str` | Completes a test template into a full test file using an LLM. |
| `process_module_batch` | `self, modules: list[tuple[str, float]], output_dir: Path, batch_size: int = 10` | `list[TestGenerationTask]` | Processes a batch of modules and returns generation task results. |
| `execute` | `self, top: int = 200, batch_size: int = 10, output_dir: str = 'tests/behavioral/generated', **kwargs` | `WorkflowResult` | Runs parallel test generation across low-coverage modules and returns a structured result. |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `parse_coverage_json` | `json_path: str` | `list[ModuleCoverage]` | Parse pytest-cov's coverage.json output. |
| `prioritize_modules` | `modules: list[ModuleCoverage], min_threshold: float = 50.0` | `list[ModuleCoverage]` | Sort modules by priority and filter below threshold. |
| `group_into_batches` | `modules: list[ModuleCoverage], max_batches: int = 5` | `list[dict]` | Group modules into batches by subsystem (package path). |
| `format_test_gen_report` | `result: dict, input_data: dict` | `str` | Format test generation output as a human-readable report. |
| `generate_test_for_function` | `module: str, func: dict` | `str` | Generate executable tests for a function based on AST analysis. |
| `generate_test_cases_for_params` | `params: list` | `dict` | Generate test cases based on parameter types. |
| `get_type_assertion` | `return_type: str` | `str \| None` | Generate assertion for return type checking. |
| `get_param_test_values` | `type_hint: str` | `list[str]` | Get test values for a single parameter based on its type. |
| `generate_test_for_class` | `module: str, cls: dict` | `str` | Generate executable test class based on AST analysis. |
| `main` | — | `None` | CLI entry point for test generation workflow. |

### Raises

| Function | Exception | Message |
|----------|-----------|---------|
| `parse_coverage_json` | `FileNotFoundError` | `'Coverage file not found: {...}'` |
| `parse_coverage_json` | `ValueError` | `'Invalid coverage JSON at {...}: {...}'` |
| `parse_coverage_json` | `ValueError` | `"Unexpected coverage JSON structure in {...}: 'files' key missing or not a dict"` |

### `get_param_test_values` return values

`get_param_test_values` returns a `list[str]`. The list may contain the following literal value:

| Value |
|-------|
| `"test_value"` |

## Constants

| Constant | Type | Members |
|----------|------|---------|
| `AUDIT_SYSTEM_PROMPT` | `str` | System prompt for the coverage-auditor subagent. Instructs it to review module prioritization and return a JSON object with a `"modules"` key. |
| `PLAN_SYSTEM_PROMPT` | `str` | System prompt for the test-planner subagent. Instructs it to group modules into logical batches and return a JSON object with a `"batches"` key, each containing a `"task_xml"` field. |
| `BATCH_TASK_TEMPLATE` | `str` | XML task prompt template. Interpolation keys: `{batch_id}`, `{subsystem}`, `{target_pct}`, `{missing_lines_summary}`, `{source_path}`, `{key_signatures}`, `{test_path}`, `{test_class_specs}`, `{module}`. |
| `DEFAULT_SKIP_PATTERNS` | `list` | `'.git'`, `'.hg'`, `'.svn'`, `'node_modules'`, `'bower_components'`, `'vendor'`, `'__pycache__'`, `'.mypy_cache'`, `'.pytest_cache'`, `'.ruff_cache'`, `'.hypothesis'`, `'venv'`, `'.venv'`, `'env'`, `'.env'`, `'virtualenv'`, `'.virtualenv'`, `'.tox'`, `'.nox'`, `'build'`, `'dist'`, `'eggs'`, `'.eggs'`, `'site-packages'`, `'.idea'`, `'.vscode'`, `'migrations'`, `'alembic'`, `'_build'`, `'docs/_build'` |
| `_SUBAGENT_NAMES` (audit) | `list` | `'coverage-auditor'`, `'gap-analyzer'`, `'test-planner'` |
| `_SUBAGENT_NAMES` (gen) | `list` | `'function-identifier'`, `'test-designer'`, `'test-writer'` |

## Source files

- `src/attune/workflows/test_gen/**`
- `src/attune/workflows/test_audit/**`
- `src/attune/workflows/test_gen_parallel.py`

## Tags

`tests`, `coverage`, `generation`
