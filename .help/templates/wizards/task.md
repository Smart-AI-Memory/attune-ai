---
type: task
name: wizards-task
feature: wizards
depth: task
generated_at: 2026-06-23T22:36:36.999673+00:00
source_hash: 0383bd1ba48703a82f700d50a22fc06aa7d00b38cf01550ca0a1f41adea84bc0
status: generated
---

# Multi-step guided interactive workflows that walk users through complex tasks

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
