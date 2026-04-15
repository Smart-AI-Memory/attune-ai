---
type: task
feature: wizards
depth: task
generated_at: 2026-04-14T15:27:06.883145+00:00
source_hash: 655cede9671032e7ccc7f39a9f47afbc96ce8855aa0b1bbe2c6567c1a091bf8b
status: generated
---

# Work with wizards

Use the wizards system when you need to guide users through complex, multi-step workflows like debugging, refactoring, or security audits with AI-powered assistance.

## Prerequisites

- Access to the project source code
- Understanding of the wizard system architecture in `src/attune/wizards/`

## Create a custom wizard

1. **Define the wizard configuration**

   Create a `WizardConfig` with your wizard's metadata:
   ```python
   config = WizardConfig(
       wizard_id="my-custom-wizard",
       name="My Custom Workflow",
       description="Guides through custom task X",
       domain="development",
       estimated_duration_minutes=10
   )
   ```

2. **Extend BaseWizard**

   Create a class that inherits from `BaseWizard`:
   ```python
   class MyWizard(BaseWizard):
       def build_prompt_context(self, step: WizardStep) -> PromptContext:
           # Build context specific to your wizard's needs
           pass

       def process_step_result(self, step: WizardStep, result: dict[str, Any]) -> None:
           # Handle the AI's response for each step
           pass
   ```

3. **Register your wizard**

   Make it available to users:
   ```python
   register_wizard("my-custom-wizard", MyWizard)
   ```

4. **Test the wizard**

   Verify it runs correctly:
   ```python
   wizard = get_wizard("my-custom-wizard")()
   result = wizard.run({"initial_param": "value"})
   assert result.success
   ```

## Use built-in wizards

1. **List available wizards**

   See what's already available:
   ```python
   configs = list_wizards()
   for config in configs:
       print(f"{config.wizard_id}: {config.description}")
   ```

2. **Get and run a wizard**

   Execute a specific wizard:
   ```python
   WizardClass = get_wizard("debug")
   wizard = WizardClass(ask_user_callback=my_callback)
   result = wizard.run({"error_message": "NoneType object has no attribute 'foo'"})
   ```

3. **Check the results**

   Review what the wizard accomplished:
   ```python
   if result.success:
       print(f"Completed {len(result.steps_completed)} steps")
       print(f"Generated output: {result.generated_output}")
   else:
       print(f"Failed: {result.error}")
   ```

## Save and manage custom wizards

1. **Save a wizard definition**

   Persist custom wizard configurations:
   ```python
   wizard_data = {
       "wizard_id": "my-wizard",
       "config": {"name": "My Workflow"},
       "steps": [...]
   }
   path = save_custom_wizard(wizard_data)
   print(f"Saved to {path}")
   ```

2. **Delete a custom wizard**

   Remove wizards you no longer need:
   ```python
   success = delete_custom_wizard("my-wizard")
   if success:
       print("Wizard deleted successfully")
   ```

## Verify success

Your wizard integration works correctly when:
- `list_wizards()` includes your wizard in the results
- Running your wizard returns a `WizardResult` with `success=True`
- The wizard completes all expected steps without errors
- Generated outputs match your workflow requirements
