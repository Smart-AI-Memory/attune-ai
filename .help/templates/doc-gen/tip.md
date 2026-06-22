---
type: tip
feature: doc-gen
depth: tip
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: e72f8c7df1bc5e57a104c92b8ea7ec8a43b33084d7d1ab2add257441af45c122
status: generated
---

# Tip: working effectively with doc gen

## Use the workflow's built-in cost tracking to avoid LLM token surprises

The `DocGenCostMixin` tracks token usage across all three subagents (outline-planner, content-writer, polish-reviewer) and provides real-time cost estimates. Check costs before processing large codebases to avoid unexpected bills.

The mixin is already integrated into `DocumentGenerationWorkflow`, so you get automatic cost reporting in the workflow result without any additional setup.

**Tags:** `docs`, `documentation`, `generation`
