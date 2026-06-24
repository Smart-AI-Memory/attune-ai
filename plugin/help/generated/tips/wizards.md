---
name: wizards
source: content/features/wizards.md
tags:
- wizards
- interactive
type: tip
---

# Multi-step guided interactive workflows that walk users through complex tasks

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  the registry functions plus `BaseWizard`, `ConfigDrivenWizard`, the
  `WizardConfig` / `WizardStep` / `WizardResult` dataclasses, `StepType`,
  and `WizardSession` — all from `attune.wizards`.
- **`await` the run.** `run()` is the only async method; the registry
  functions are sync.
- **Use the skill for interactive runs.** `/wizard` wires the
  `ask_user_callback` to `AskUserQuestion`; a bare Python run needs you
  to supply one for `question` steps.
- **Discover before you run.** `list_wizards()` gives ids, names,
  domains, and cost/duration estimates.
