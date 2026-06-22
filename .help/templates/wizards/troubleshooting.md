---
type: troubleshooting
feature: wizards
depth: troubleshooting
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 322dc43a8cc4749920887d066cffb815d8c6faee0b2e93968e78ac53228d58b1
status: generated
---

# Troubleshoot wizards

## Before you start

The wizards feature provides XML-enhanced interactive workflows for Attune AI. These multi-step guided processes help with debugging, refactoring, release preparation, security audits, and test generation.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `ValueError: Cannot write wizard YAML` | File permissions on the target directory and available disk space |
| `ValueError: Cannot delete built-in wizard` | Whether you're trying to delete a built-in wizard (only custom wizards can be deleted) |
| Wizard step skipped unexpectedly | The step's `condition` function and the current `WizardSession` state |
| `WizardResult.success` is `False` but no error message | The `WizardResult.error` field and exception handling in `BaseWizard.run()` |
| Wizard hangs on a step | Token limits (`max_tokens`) and provider response timeouts |
| Empty or malformed wizard output | The `prompt_template` and `prompt_context_template` for the failing step |

## Step-by-step diagnosis

1. **Reproduce the failure with a minimal wizard run.**
   Create a simple test that calls `BaseWizard.run()` with the same `initial_context` that triggers the issue. This isolates the problem from surrounding application logic.

2. **Check wizard registration and retrieval.**
   Verify the wizard is properly registered by running:
   ```python
   from attune.wizards import list_wizards, get_wizard
   print([w.wizard_id for w in list_wizards()])
   wizard_class = get_wizard("your-wizard-id")
   print(f"Found: {wizard_class}")
   ```

3. **Enable debug logging and examine step execution.**
   Set logging to `DEBUG` level before running the wizard. Look for patterns in the step processing, particularly around `build_prompt_context()` and `process_step_result()` calls.

4. **Inspect the `WizardResult` object.**
   After a failed run, examine these fields in order:
   - `WizardResult.error` - Contains the failure reason
   - `WizardResult.steps_completed` - Shows how far the wizard got
   - `WizardResult.collected_data` - Reveals what data was gathered
   - `WizardResult.total_cost` and `total_duration_ms` - Indicates resource usage

5. **Validate step configuration.**
   For each failing step, check:
   - `step_type` matches the intended execution mode
   - `prompt_template` is not None for steps that need AI interaction
   - `questions` list is properly defined for form-based steps
   - `tier` setting matches your provider capabilities

## Common fixes

- **Fix wizard registration errors.**
  ```python
  from attune.wizards import register_wizard
  register_wizard("my-wizard", MyWizardClass)
  ```
  Ensure you call `register_wizard()` before trying to retrieve the wizard with `get_wizard()`.

- **Resolve custom wizard file permissions.**
  ```bash
  # Make wizard directory writable
  chmod 755 ~/.attune/wizards/
  # Check available disk space
  df -h ~/.attune/
  ```

- **Fix step condition logic.**
  If steps are skipping unexpectedly, verify the condition function:
  ```python
  # In your WizardStep definition
  condition=lambda session: session.collected_data.get('prerequisite_done', False)
  ```

- **Adjust token limits for complex steps.**
  Increase `max_tokens` for steps that generate long outputs:
  ```python
  WizardStep(
      id="analysis",
      step_type=StepType.QUESTION,
      max_tokens=8192  # Increase from default 4096
  )
  ```

- **Handle missing ask_user_callback.**
  For interactive wizards, ensure you provide a callback function:
  ```python
  def my_callback(question):
      return input(f"{question}: ")

  wizard = MyWizard(ask_user_callback=my_callback)
  ```

## Source files

- `src/attune/wizards/base.py` - `BaseWizard` class and core logic
- `src/attune/wizards/types.py` - Data structures (`WizardStep`, `WizardConfig`, etc.)
- `src/attune/wizards/registry.py` - Wizard registration and management
- `src/attune/wizards/builtin/` - Built-in wizard implementations

**Tags:** `wizards`, `interactive`
