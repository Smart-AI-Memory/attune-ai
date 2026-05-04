---
type: task
feature: wizards
depth: task
generated_at: 2026-05-04T02:40:00.202293+00:00
source_hash: 76c270cd6e9ba25a7ffd711122874b94ee586d10897f8210e8c4844f8ecd9f81
status: generated
---

# Work with wizards

Use wizards when you need to create guided, multi-step interactive workflows that collect user input and generate structured output.

## Prerequisites

- Access to the project source code
- Understanding of the wizard system architecture in `src/attune/wizards/`
- Python development environment configured

## Steps

1. **Choose your wizard approach**

   Determine whether to use a built-in wizard, extend an existing one, or create a custom wizard:
   - For debugging workflows, use `DebugWizard`
   - For code refactoring, use `RefactorWizard`
   - For security audits, use `SecurityWizard`
   - For test generation, use `TestGenWizard`
   - For release preparation, use `ReleasePrepWizard`

2. **Register or retrieve your wizard**

   For built-in wizards, retrieve them with:
   ```python
   from attune.wizards import get_wizard
   wizard_class = get_wizard("debug")  # or "refactor", "security", etc.
   ```

   For custom wizards, register them first:
   ```python
   from attune.wizards import register_wizard
   register_wizard("my-custom-wizard", MyCustomWizardClass)
   ```

3. **Configure wizard steps**

   Create `WizardStep` instances with the required fields:
   ```python
   from attune.wizards import WizardStep, StepType

   step = WizardStep(
       id="analyze-code",
       name="Code Analysis",
       description="Analyze the codebase for issues",
       step_type=StepType.QUESTION,
       prompt_template="What specific issues should I look for?",
       tier="capable"
   )
   ```

4. **Initialize and run the wizard**

   Create a wizard instance and execute it:
   ```python
   wizard = wizard_class(ask_user_callback=your_callback_function)
   result = wizard.run(initial_context={"project_path": "/path/to/project"})
   ```

5. **Process the wizard result**

   Handle the `WizardResult` object returned:
   ```python
   if result.success:
       print(f"Wizard completed {len(result.steps_completed)} steps")
       print(f"Generated output: {result.generated_output}")
       print(f"Total cost: ${result.total_cost:.2f}")
   else:
       print(f"Wizard failed: {result.error}")
   ```

6. **Save custom wizard definitions (optional)**

   For reusable custom wizards, save the configuration:
   ```python
   from attune.wizards import save_custom_wizard

   wizard_data = {
       "wizard_id": "my-workflow",
       "name": "My Custom Workflow",
       "description": "Custom workflow description",
       "steps": [/* step definitions */]
   }
   save_custom_wizard(wizard_data)
   ```

## Verification

Run your wizard and verify:
- All wizard steps execute in the correct order
- User input is collected and processed correctly
- The wizard generates the expected output format
- The `WizardResult` contains complete execution data
- Custom wizards appear in `list_wizards()` output

## Key files

- `src/attune/wizards/base.py` - `BaseWizard` abstract class
- `src/attune/wizards/types.py` - Data type definitions
- `src/attune/wizards/builtin.py` - Pre-built wizard implementations
- `src/attune/wizards/registry.py` - Wizard registration and management
