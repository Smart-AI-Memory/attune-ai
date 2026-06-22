---
type: warning
feature: wizards
depth: warning
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 322dc43a8cc4749920887d066cffb815d8c6faee0b2e93968e78ac53228d58b1
status: generated
---

# Wizards cautions

## What to watch for

The wizards framework provides multi-step guided workflows that can accumulate significant LLM costs and execute long-running operations. Several design patterns in the framework can lead to unexpected behavior if not handled carefully.

## Risk areas

### Cost accumulation in wizard runs

The `BaseWizard.run()` method executes multiple LLM calls across wizard steps, but cost tracking happens per step rather than with upfront validation. A wizard with many steps or high `max_tokens` values can exceed your budget before completion. Check the `estimated_cost_range` in `WizardConfig` before starting expensive wizards, and monitor `total_cost` in partial results.

### Step condition evaluation timing

The `condition` field in `WizardStep` gets evaluated during wizard execution, not at registration time. If your condition function depends on external state (file existence, network connectivity), it can cause steps to be skipped unexpectedly when that state changes between wizard initialization and step execution.

### Custom wizard persistence edge cases

`save_custom_wizard()` overwrites existing files without confirmation and can raise `ValueError` for filesystem issues that aren't obvious from the error message. The function creates the wizard directory if it doesn't exist, but won't create intermediate parent directories. Always verify the base directory structure exists before saving.

### Registry state inconsistency

The wizard registry is module-global state. Calling `register_wizard()` multiple times with the same `wizard_id` silently overwrites the previous registration. In test environments, this can cause tests to interfere with each other if they register wizards with identical IDs.

### Step result processing mutations

The `process_step_result()` method in wizard subclasses receives the raw result dictionary and can modify it in place. Changes made during processing affect the `collected_data` field in `WizardResult`, which can cause downstream steps to see modified data they weren't expecting.

## How to avoid problems

1. **Validate cost limits upfront.** Check `estimated_cost_range` and set reasonable `max_tokens` values for each step. Consider implementing cost guards that halt execution if `total_cost` approaches your budget.

2. **Make step conditions resilient.** Write condition functions that handle missing files, network timeouts, and other transient failures gracefully. Return `False` rather than raising exceptions when external dependencies aren't available.

3. **Use unique wizard IDs in tests.** Include test method names or random suffixes in wizard IDs when registering test wizards to avoid registry collisions between test runs.

4. **Copy result data before processing.** If you need to modify step results in `process_step_result()`, work on a copy to avoid affecting the original data that gets stored in `WizardResult.collected_data`.

5. **Verify directory structure for custom wizards.** Before calling `save_custom_wizard()`, ensure the base directory and any parent directories exist and are writable.

## Source files

- `src/attune/wizards/**`

**Tags:** `wizards`, `interactive`
