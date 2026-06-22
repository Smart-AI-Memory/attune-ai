---
type: quickstart
feature: wizards
depth: quickstart
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 322dc43a8cc4749920887d066cffb815d8c6faee0b2e93968e78ac53228d58b1
status: generated
---

# Quickstart: wizards

Run a built-in interactive wizard to guide you through common development tasks.

```python
from attune.wizards import DebugWizard

wizard = DebugWizard()
result = wizard.run({"error_message": "ImportError: No module named 'requests'"})
print(f"Debugging complete: {result.success}")
```

## Prerequisites

- Attune AI installed locally
- Python environment with the attune package available

## Run your first wizard

1. **Choose a built-in wizard.** Start with `DebugWizard` for troubleshooting errors:

```python
from attune.wizards import DebugWizard

wizard = DebugWizard()
```

2. **Run the wizard with context.** Provide an initial context like an error message or code snippet:

```python
result = wizard.run({"error_message": "ModuleNotFoundError: No module named 'pandas'"})
```

3. **Check the results.** The wizard returns a `WizardResult` with guidance and next steps:

```python
print(f"Success: {result.success}")
print(f"Generated guidance: {result.generated_output}")
print(f"Steps completed: {result.steps_completed}")
```

Expected output:
```
Success: True
Generated guidance: Install pandas using: pip install pandas
Steps completed: ['analyze_error', 'suggest_fix', 'verify_solution']
```

## Next steps

**Next:** Browse available wizards with `list_wizards()` to see RefactorWizard, SecurityWizard, and TestGenWizard options.
