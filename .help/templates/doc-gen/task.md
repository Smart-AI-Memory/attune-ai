---
type: task
feature: doc-gen
depth: task
generated_at: 2026-05-04T02:25:57.849088+00:00
source_hash: 40c128b66a197e8117c6093f1f637e47e612fceae7fd2f94851a5a1d91120296
status: generated
---

# Work with doc gen

Use doc gen when you need to generate documentation from source code — docstrings, readme sections, or API references.

## Set up your environment

1. **Navigate to the document generation module**
   ```bash
   cd src/attune/workflows/document_gen/
   ```

2. **Review the workflow structure**
   Examine the main entry point to understand the current generation pipeline:
   - `DocumentGenerationWorkflow` orchestrates three specialized subagents
   - Each subagent handles outline planning, content writing, or final polish
   - The workflow produces structured markdown output

## Modify generation behavior

1. **Choose the right mixin for your change**
   Each mixin handles a specific stage:
   - `OutlineStageMixin` — controls documentation structure planning
   - `WriteStageMixin` — handles content generation
   - `PolishStageMixin` — manages final review and formatting
   - `ChunkedGenerationMixin` — breaks large codebases into manageable pieces
   - `DocGenCostMixin` — tracks token usage and generation costs

2. **Update the workflow configuration**
   Modify `default_context()` in `DocumentGenerationWorkflow` to change:
   - Which subagents run in the pipeline
   - Default parameters for each generation stage
   - Cost limits or chunking thresholds

3. **Customize the output format**
   Edit `format_doc_gen_report()` in `report_formatter.py` to change:
   - Report structure and sections
   - How generation results are displayed
   - Progress indicators or completion status

## Test your changes

1. **Run the doc generation tests**
   ```bash
   pytest -k "doc_gen" -v
   ```

2. **Verify workflow execution**
   Test the complete pipeline by running:
   ```bash
   python -m attune.workflows.document_gen --path ./test_module
   ```

You know the changes work when the workflow executes without errors and produces documentation in the expected format with your modifications applied.

## Key files to modify

- `src/attune/workflows/document_gen/workflow.py` — Main workflow orchestration
- `src/attune/workflows/document_gen/report_formatter.py` — Output formatting
- Individual mixin files for stage-specific behavior changes
