---
type: warning
name: wizards-warning
feature: wizards
depth: warning
generated_at: 2026-06-23T22:36:36.999673+00:00
source_hash: 0383bd1ba48703a82f700d50a22fc06aa7d00b38cf01550ca0a1f41adea84bc0
status: generated
---

# Multi-step guided interactive workflows that walk users through complex tasks

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'BaseWizard.run' was never awaited` | `run()` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `AttributeError: 'NoneType' object has no attribute ...` after `get_wizard` | The wizard id is unknown; `get_wizard` returned `None` | Check `get_wizard(id) is not None`; list ids with `list_wizards()` | high |
| A `question` step never prompts / hangs | No `ask_user_callback` wired (outside Claude Code) | Pass an `ask_user_callback` to the wizard, or run via the `/wizard` skill | medium |
| `WizardResult.success` is `False` with a populated `error` | A step failed (LLM call, validation, or an aborted confirm) | Read `result.error` and `result.steps_completed` to see where it stopped | medium |
| Custom wizard not found by `get_wizard` | It was never `register_wizard`'d (or `save_custom_wizard`'d) | Register the class or save the definition first | low |

### Risk areas

- **`run()` is async.** Forgetting to `await` it is the most common
  mistake.
- **There is no registry class.** Use the module-level functions
  (`list_wizards`, `get_wizard`, …) — not a `WizardRegistry`.
- **`question` steps need a callback.** Outside the `/wizard` skill,
  supply an `ask_user_callback` or the wizard can't collect input.

### Diagnosis order

1. Confirm you are awaiting: `await get_wizard(id)().run()`.
2. Confirm the id exists: `get_wizard(id) is not None` /
   `list_wizards()`.
3. On failure, read `result.error` and `result.steps_completed`.
4. If a `question` step stalls, check the `ask_user_callback` wiring.
