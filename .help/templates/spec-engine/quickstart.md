---
type: quickstart
name: spec-engine-quickstart
feature: spec-engine
depth: quickstart
generated_at: 2026-06-21T18:43:45.172614+00:00
source_hash: 2dfc8acb0ee448c292e20dbc3f8299d64331d1f378bbf85cced4377b5dc2b5d1
status: generated
---

# Spec-driven development with approval loops

## Quickstart

Run a spec plan end-to-end with quality gates from Python.
`PipelineOrchestrator.run_all` is an async coroutine, so drive it with
`asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.pipeline import PipelineOrchestrator, PipelineResult


async def main() -> None:
    orchestrator = PipelineOrchestrator(".claude/plans/my-feature.md")
    result: PipelineResult = await orchestrator.run_all()
    print(result.summary)   # human-readable run summary
    print(result.success)   # True if all tasks executed and passed gates


asyncio.run(main())
```

`summary` and `success` are properties — read them, don't call them.
Running this produces a `PipelineResult` with per-task outcomes, total
cost, and duration.

To skip quality gates during a quick smoke test, pass
`skip_gates=True` to the constructor.
