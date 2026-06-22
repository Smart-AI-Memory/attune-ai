---
type: tip
feature: wizards
depth: tip
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 322dc43a8cc4749920887d066cffb815d8c6faee0b2e93968e78ac53228d58b1
status: generated
---

# Tip: working effectively with wizards

## Extend BaseWizard, don't configure from scratch

Inherit from `BaseWizard` and override `build_prompt_context()` and `process_step_result()` instead of creating config-driven wizards from YAML. The built-in wizards like `DebugWizard` and `RefactorWizard` show this pattern consistently.

You get type safety, IDE support, and easier testing compared to string-based configuration. The tradeoff is less runtime flexibility — you can't modify wizard behavior without code changes.

## Source files

- `src/attune/wizards/**`

**Tags:** `wizards`, `interactive`
