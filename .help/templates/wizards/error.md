---
type: error
feature: wizards
depth: error
generated_at: 2026-04-14T15:27:42.839594+00:00
source_hash: 655cede9671032e7ccc7f39a9f47afbc96ce8855aa0b1bbe2c6567c1a091bf8b
status: generated
---

# Wizards errors

Failures in Attune AI's XML-enhanced wizard system, which provides guided multi-step workflows for development tasks like debugging, refactoring, and security audits.

## Common error signatures

- `ValueError: Cannot write wizard YAML: {error_details}` — Custom wizard save operations failed due to filesystem issues or invalid YAML structure
- `ValueError: Cannot delete built-in wizard: '{wizard_id}'` — Attempted to delete a built-in wizard (DebugWizard, RefactorWizard, etc.)
- `KeyError` or `None` returned from `get_wizard()` — Requested wizard ID not found in registry
- Step execution failures during `BaseWizard.run()` — Wizard step conditions, prompt generation, or result processing errors
- XML parsing errors in task decomposition — Invalid XML structure in decomposed task responses

## Where errors originate

Wizard errors typically start at these key entry points:

- **Registry operations**: `register_wizard()`, `get_wizard()`, `list_wizards()` — Wizard registration and lookup failures
- **Custom wizard management**: `save_custom_wizard()`, `delete_custom_wizard()` — File I/O and validation errors when persisting wizard definitions
- **Wizard execution**: `BaseWizard.run()` — Step processing, condition evaluation, and prompt context building failures
- **Step processing**: `build_prompt_context()`, `process_step_result()` — Individual wizard implementations failing to handle step data

## How to diagnose

1. **Check the wizard ID and registration status.** Use `list_wizards()` to verify the wizard exists and `get_wizard(wizard_id)` returns a valid class. Missing wizards return `None` rather than raising exceptions.

2. **Examine custom wizard YAML structure.** If `save_custom_wizard()` fails, validate that your wizard definition matches the expected schema with required fields like `wizard_id`, `name`, `description`, and properly formatted `steps`.

3. **Review step conditions and context.** When `BaseWizard.run()` fails mid-execution, check that step conditions (`WizardStep.condition`) evaluate correctly and that `build_prompt_context()` can access all required data from the wizard session.

4. **Validate filesystem permissions.** Custom wizard save/delete operations require write access to the wizard definitions directory. Permission errors manifest as `ValueError` with "Cannot write wizard YAML" messages.

5. **Check built-in wizard constraints.** Attempts to modify built-in wizards (DebugWizard, RefactorWizard, ReleasePrepWizard, SecurityWizard, TestGenWizard) will fail with explicit error messages about protected wizard IDs.

## Source files

- `src/attune/wizards/**`

**Tags:** `wizards`, `interactive`
