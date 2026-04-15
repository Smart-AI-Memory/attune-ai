---
type: tip
feature: doc-gen
depth: tip
generated_at: 2026-04-14T14:46:49.006874+00:00
source_hash: 67aadd029bbf773d9f478a4d4c750e25344dc6b0bd9e1edadbcf5151d83f3bff
status: generated
---

# Tip: working effectively with doc gen

## Use the workflow's built-in cost tracking to avoid LLM token surprises

The `DocGenCostMixin` tracks token usage across all three subagents (outline-planner, content-writer, polish-reviewer) and provides real-time cost estimates. Check costs before processing large codebases to avoid unexpected bills.

The mixin is already integrated into `DocumentGenerationWorkflow`, so you get automatic cost reporting in the workflow result without any additional setup.

**Tags:** `docs`, `documentation`, `generation`
