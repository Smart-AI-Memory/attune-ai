---
type: comparison
name: wizards-comparison
feature: wizards
depth: comparison
generated_at: 2026-06-23T22:36:36.999673+00:00
source_hash: 0383bd1ba48703a82f700d50a22fc06aa7d00b38cf01550ca0a1f41adea84bc0
status: generated
---

# Multi-step guided interactive workflows that walk users through complex tasks

## Comparison

Wizards differ from workflows in interaction model:

| | Wizards | Workflows |
|--|---------|-----------|
| Interaction | Interactive — collect input mid-run via `question`/`confirm` steps | Non-interactive — run to completion from inputs |
| Entry | `get_wizard(id)` + `await run()`, or `/wizard` skill | `attune workflow run <slug>` / the workflow class |
| Output | `WizardResult` (collected data + generated output) | `WorkflowResult` |

Reach for a **wizard** when the task needs the user in the loop
(answering questions, confirming gates); reach for a **workflow** when
the run is fully specified up front. Several builtins mirror a
workflow (`release-prep`, `security`, `test-gen`) but wrap it in a
guided, interactive flow.
