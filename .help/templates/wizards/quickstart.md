---
type: quickstart
name: wizards-quickstart
feature: wizards
depth: quickstart
generated_at: 2026-06-23T22:36:36.999673+00:00
source_hash: 0383bd1ba48703a82f700d50a22fc06aa7d00b38cf01550ca0a1f41adea84bc0
status: generated
---

# Multi-step guided interactive workflows that walk users through complex tasks

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
