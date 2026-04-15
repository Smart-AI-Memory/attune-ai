---
type: tip
feature: wizards
depth: tip
generated_at: 2026-04-14T15:28:57.267201+00:00
source_hash: 655cede9671032e7ccc7f39a9f47afbc96ce8855aa0b1bbe2c6567c1a091bf8b
status: generated
---

# Tip: working effectively with wizards

## Extend BaseWizard, don't configure from scratch

Inherit from `BaseWizard` and override `build_prompt_context()` and `process_step_result()` instead of creating config-driven wizards from YAML. The built-in wizards like `DebugWizard` and `RefactorWizard` show this pattern consistently.

You get type safety, IDE support, and easier testing compared to string-based configuration. The tradeoff is less runtime flexibility — you can't modify wizard behavior without code changes.

## Source files

- `src/attune/wizards/**`

**Tags:** `wizards`, `interactive`
