---
name: wizards
source: content/features/wizards.md
tags:
- wizards
- interactive
type: comparison
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
