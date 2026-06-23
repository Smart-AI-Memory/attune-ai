# Wizards

## Quickstart

List the built-in wizards, then run one. `run()` is a coroutine, so
drive it with `asyncio.run`:

```python
import asyncio

from attune.wizards import get_wizard, list_wizards


async def main() -> None:
    for cfg in list_wizards():
        print(cfg.wizard_id, "-", cfg.name)

    wizard_cls = get_wizard("debug")
    if wizard_cls is not None:
        result = await wizard_cls().run()
        print(result.success, result.wizard_id)


asyncio.run(main())
```

`get_wizard` returns the wizard class (or `None` if the id is
unknown); instantiate it and `await run()`.

## Tasks

### Run a built-in wizard

**Goal:** run a guided wizard and read its result.

**Steps:**

```python
import asyncio

from attune.wizards import get_wizard


async def main() -> None:
    wizard_cls = get_wizard("security")
    if wizard_cls is None:
        print("unknown wizard")
        return

    result = await wizard_cls().run(initial_context={"path": "src/"})
    print("success:", result.success)
    print("output:", result.generated_output)
    print("cost:", result.total_cost)


asyncio.run(main())
```

**Verify:** `run()` is a coroutine — `await` it. The result is a
`WizardResult` with `success`, `collected_data`, `generated_output`,
`tasks`, `total_cost`, `total_duration_ms`, and `error` on failure.
`initial_context` seeds the run.

### Discover what's available

**Goal:** list the registered wizards and their metadata.

**Steps:**

```python
from attune.wizards import get_wizard, list_wizards

for cfg in list_wizards():
    print(f"{cfg.wizard_id}: {cfg.name} ({cfg.domain})")
    print(f"  ~{cfg.estimated_duration_minutes} min, {cfg.estimated_cost_range}")

cls = get_wizard("test-gen")   # -> TestGenWizard class, or None
```

**Verify:** `list_wizards()` returns `WizardConfig` objects (sync). The
five built-ins are `debug`, `refactor`, `release-prep`, `security`,
and `test-gen`. `get_wizard(id)` returns the class or `None`.

### Register a custom wizard

**Goal:** make your own wizard discoverable.

**Steps:**

```python
from attune.wizards import BaseWizard, register_wizard


class MyWizard(BaseWizard):
    def build_prompt_context(self, step):
        ...

    def process_step_result(self, step, result):
        ...


register_wizard("my-wizard", MyWizard)
```

**Verify:** after `register_wizard`, `get_wizard("my-wizard")` returns
your class and it appears in `list_wizards()`. For a config-only
wizard, build a `ConfigDrivenWizard(config, steps)` or persist a
definition with `save_custom_wizard(data)`.

## Reference

The public surface is the registry functions and the wizard
classes/dataclasses, all re-exported from `attune.wizards`.

### Registry functions — `attune.wizards`

| Function | Purpose |
|----------|---------|
| `list_wizards() -> list[WizardConfig]` | All registered wizard configs (built-in + custom). |
| `get_wizard(wizard_id) -> type[BaseWizard] \| None` | The wizard class for an id, or `None`. |
| `register_wizard(wizard_id, wizard_class) -> None` | Register a `BaseWizard` subclass. |
| `save_custom_wizard(wizard_data, base_dir=None) -> Path` | Persist a config-driven wizard definition; returns the saved path. |
| `delete_custom_wizard(wizard_id, base_dir=None) -> bool` | Remove a saved custom wizard. |

### Classes — `attune.wizards`

| Symbol | Purpose |
|--------|---------|
| `BaseWizard(ask_user_callback=None, provider=None, **kwargs)` | Abstract base; async `run(initial_context=None) -> WizardResult`; hooks `build_prompt_context(step)` and `process_step_result(step, result)`. |
| `ConfigDrivenWizard(config, steps, **kwargs)` | A wizard built from a `WizardConfig` + `list[WizardStep]`, no subclass needed. |
| `WizardSession` | Per-run session state. |
| `TaskDecomposer` / `DecomposedTask` | Back the `task_decompose` step type (XML task decomposition). |

### Dataclasses — `attune.wizards`

| Type | Fields |
|------|--------|
| `WizardConfig` | `wizard_id`, `name`, `description`, `domain`, `version`, `source`, `estimated_cost_range`, `estimated_duration_minutes`. |
| `WizardStep` | `id`, `name`, `description`, `step_type`, `prompt_template`, `tier`, `questions`, `condition`, `max_tokens`, `prompt_context_template`, `review_source_step_id`. |
| `WizardResult` | `wizard_id`, `run_id`, `success`, `steps_completed`, `collected_data`, `generated_output`, `tasks`, `total_cost`, `total_duration_ms`, `error`. |
| `StepType` | `question`, `llm_call`, `task_decompose`, `review`, `preview`, `confirm`. |

### Entry points

| Surface | Invocation |
|---------|------------|
| Python | `get_wizard(<id>)`, then `await <cls>().run()`; `list_wizards()` to discover. |
| Skill | `/wizard` in a Claude Code conversation. |

No `attune wizard` CLI command and no MCP tool exist for wizards.

<!-- attune-generated: source_hash=0383bd1ba48703a82f700d50a22fc06aa7d00b38cf01550ca0a1f41adea84bc0 feature=wizards kind=how-to generated_at=2026-06-23 -->
