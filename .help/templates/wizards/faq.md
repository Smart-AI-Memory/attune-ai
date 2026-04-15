---
type: faq
feature: wizards
depth: faq
generated_at: 2026-04-14T15:28:39.160037+00:00
source_hash: 655cede9671032e7ccc7f39a9f47afbc96ce8855aa0b1bbe2c6567c1a091bf8b
status: generated
---

# Wizards FAQ

## What are wizards?

Interactive, multi-step workflows that guide you through complex tasks like debugging, refactoring, security audits, and test generation.

## When should I use wizards?

Use wizards when you need guided assistance with development tasks that involve multiple steps or decisions. For example, use the DebugWizard when troubleshooting issues, or the RefactorWizard when restructuring code.

## Which wizards are available?

Attune includes five built-in wizards:

- **DebugWizard** - Helps troubleshoot code issues
- **RefactorWizard** - Guides code restructuring
- **ReleasePrepWizard** - Assists with release preparation
- **SecurityWizard** - Performs guided security audits
- **TestGenWizard** - Helps generate test code

## How do I run a wizard?

Get a wizard class using `get_wizard()`, then create an instance and call `run()`:

```python
from attune.wizards import get_wizard

wizard_class = get_wizard("debug")
wizard = wizard_class()
result = wizard.run(initial_context={"file": "my_script.py"})
```

## How do I see all available wizards?

Call `list_wizards()` to get configuration details for all registered wizards, including estimated cost and duration.

## Can I create custom wizards?

Yes. Either extend `BaseWizard` for programmatic wizards or use `save_custom_wizard()` to create YAML-defined wizards that follow a structured format.

## How do I debug wizard issues?

Run `pytest -k "wizards" -v` to verify the wizard system works correctly. If your specific wizard fails, check the `WizardResult.error` field for error details, or add logging to your wizard's `build_prompt_context()` and `process_step_result()` methods.

## Where are the source files?

- `src/attune/wizards/**`

**Tags:** `wizards`, `interactive`
