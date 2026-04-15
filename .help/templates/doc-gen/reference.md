---
type: reference
feature: doc-gen
depth: reference
generated_at: 2026-04-14T14:45:36.201441+00:00
source_hash: 67aadd029bbf773d9f478a4d4c750e25344dc6b0bd9e1edadbcf5151d83f3bff
status: generated
---

# Doc Gen reference

## Classes

| Class | Description |
|-------|-------------|
| `DocumentGenerationWorkflow` | Generate new documentation from source code (creation) |
| `APIReferenceMixin` | Mixin providing API reference extraction and generation for doc generation |
| `ChunkedGenerationMixin` | Mixin providing chunked generation and display utilities for doc generation |
| `DocGenCostMixin` | Mixin providing cost management for document generation |
| `OutlineStageMixin` | Mixin providing the outline generation stage |
| `PolishStageMixin` | Mixin providing the polish (final review) stage |
| `WriteStageMixin` | Mixin providing the write (content generation) stage |

### DocumentGenerationWorkflow methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `default_context` | `xml_config: dict \| None = None` | `WorkflowContext` | Create default workflow context |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Execute the documentation generation workflow |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `format_doc_gen_report` | `result: dict, input_data: dict` | `str` | Format document generation output as a human-readable report |

## Constants

| Constant | Value |
|----------|-------|
| `DOC_GEN_STEPS` | Workflow step definitions |
| `TOKEN_COSTS` | Cost tracking configuration |

## Subagents

The workflow uses three specialized subagents:

| Subagent | Purpose |
|----------|---------|
| `outline-planner` | Structure documentation and plan content organization |
| `content-writer` | Generate comprehensive documentation content |
| `polish-reviewer` | Review and refine final documentation output |
