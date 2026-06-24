---
name: wizards
source: content/features/wizards.md
tags:
- wizards
- interactive
type: faq
---

# Wizards FAQ

## What are wizards?

Interactive, multi-step workflows that guide you through complex tasks
— collecting input via `question` steps, running LLM calls, decomposing
tasks, and gating on review/confirm — and return a `WizardResult` with
the collected data, generated output, and cost/duration.

## Which wizards are available?

Five ship built in (run `list_wizards()` to confirm):

- `debug` (`DebugWizard`) — systematic debugging
- `refactor` (`RefactorWizard`) — code restructuring with safety checks
- `release-prep` (`ReleasePrepWizard`) — release preparation
- `security` (`SecurityWizard`) — guided security audit
- `test-gen` (`TestGenWizard`) — interactive test generation

## How do I run a wizard?

`get_wizard(id)` returns the wizard class; instantiate it and `await`
its `run()` — `run()` is a coroutine:

```python
import asyncio

from attune.wizards import get_wizard


async def main() -> None:
    wizard_cls = get_wizard("debug")
    if wizard_cls is not None:
        result = await wizard_cls().run(initial_context={"file": "my_script.py"})
        print(result.success)


asyncio.run(main())
```

There is no `attune wizard` CLI command and no MCP tool — run wizards
through the Python API or the `/wizard` skill.

## Are the calls async?

`run()` is a coroutine — `await` it or use `asyncio.run`. The registry
functions (`list_wizards`, `get_wizard`) are synchronous.

## Is there a `WizardRegistry` class?

No. The registry is module-level functions in `attune.wizards`:
`list_wizards`, `get_wizard`, `register_wizard`, `save_custom_wizard`,
`delete_custom_wizard`.

## How do I see all available wizards?

Call `list_wizards()` — it returns a `WizardConfig` per registered
wizard, with id, name, domain, and estimated cost/duration.

## Can I create custom wizards?

Yes — subclass `BaseWizard` (implement `build_prompt_context` and
`process_step_result`) and `register_wizard(id, cls)`, or build a
`ConfigDrivenWizard(config, steps)` / persist one with
`save_custom_wizard(data)`.

## How do I debug a wizard failure?

Check `WizardResult.error` and `WizardResult.steps_completed` to see
where it stopped. If a `question` step stalls outside the `/wizard`
skill, wire an `ask_user_callback` into the wizard.

**Tags:** `wizards`, `interactive`
