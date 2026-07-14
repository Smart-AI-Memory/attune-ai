---
type: quickstart
name: spec-engine-quickstart
feature: spec-engine
depth: quickstart
generated_at: 2026-07-14T15:59:02.694082+00:00
source_hash: 657458c4d06bb198d067760775b69a5c87288113feaddb9cdaf3df631c188617
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
