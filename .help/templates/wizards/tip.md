---
type: tip
name: wizards-tip
feature: wizards
depth: tip
generated_at: 2026-06-23T22:36:36.999673+00:00
source_hash: 0383bd1ba48703a82f700d50a22fc06aa7d00b38cf01550ca0a1f41adea84bc0
status: generated
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
