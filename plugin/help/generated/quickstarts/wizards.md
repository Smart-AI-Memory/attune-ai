---
name: wizards
source: content/features/wizards.md
tags:
- wizards
- interactive
type: quickstart
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
