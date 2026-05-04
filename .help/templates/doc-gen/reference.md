---
type: reference
feature: doc-gen
depth: reference
generated_at: 2026-05-04T02:26:09.249962+00:00
source_hash: 40c128b66a197e8117c6093f1f637e47e612fceae7fd2f94851a5a1d91120296
status: generated
---

# Doc-gen reference

Generate documentation from source code using a multi-stage workflow that orchestrates specialized subagents for outline planning, content writing, and polishing.

## Classes

| Class | Description |
|-------|-------------|
| `DocumentGenerationWorkflow` | Generate new documentation from source code using coordinated subagents |
| `APIReferenceMixin` | Extract and generate API reference sections from source code |
| `ChunkedGenerationMixin` | Handle large documentation generation through chunked operations |
| `DocGenCostMixin` | Track and manage token costs during documentation generation |
| `OutlineStageMixin` | Generate structured documentation outlines from codebase analysis |
| `PolishStageMixin` | Review and polish generated documentation for final output |
| `WriteStageMixin` | Generate documentation content from outlined structure |

### DocumentGenerationWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `default_context` | `xml_config: dict \| None = None` | `WorkflowContext` | Create default workflow context for documentation generation |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Execute the documentation generation workflow |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `format_doc_gen_report` | `result: dict, input_data: dict` | `str` | Format document generation output as a human-readable report |

## Constants

| Constant | Values | Description |
|----------|--------|-------------|
| `DOC_GEN_STEPS` | (exported in `__all__`) | Documentation generation workflow steps |
| `TOKEN_COSTS` | (exported in `__all__`) | Token cost tracking configuration |
| `_SUBAGENT_NAMES` | `['outline-planner', 'content-writer', 'polish-reviewer']` | Names of specialized documentation subagents |
| `_SYSTEM_PROMPT` | `'You are a documentation generation orchestrator...'` | System prompt for workflow coordination |
| `_TASK_PROMPT_TEMPLATE` | Template string | Task prompt template for documentation generation |
