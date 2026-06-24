---
name: deep-review
source: content/features/deep-review.md
tags:
- review
- security
- quality
- tests
- comprehensive-review
type: task
---

# Multi-pass code review across security, quality, and test gaps

## Tasks

### Review a path from the CLI

**Goal:** run a one-off review over a directory without writing
any Python.

**Steps:**

```bash
# Default depth (standard) over a directory:
attune workflow run deep-review --path src/

# Deep review, JSON output for a pre-merge gate:
attune workflow run deep-review --path src/ --depth deep --json

# Narrow to the security pass via JSON input:
attune workflow run deep-review --path src/ --input '{"focus": ["security"]}'
```

**Verify:** `--path` / `-p` defaults to the current directory;
`--depth` accepts `quick`, `standard`, or `deep`; `--json` / `-j`
emits machine-readable output. There is no dedicated `--focus`
flag — pass `focus` through `--input` as JSON. Use
`attune workflow info deep-review` to confirm registration and
`attune workflow list` to see it alongside the other workflows.

### Call the review from Python

**Goal:** drive deep-review from a hook or pre-merge gate and act
on the result.

**Steps:**

```python
import asyncio

from attune.workflows import DeepReviewAgentSDKWorkflow


async def main() -> None:
    workflow = DeepReviewAgentSDKWorkflow()
    result = await workflow.execute(path="src/api/", depth="deep")

    if not result.success:
        print("review failed:", result.error)
        return

    print(result.final_output)
    for action in result.suggestions:
        print(action)


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. A completed
review returns `success=True` with the report in `final_output`;
a failure returns `success=False` with a populated `error` and
`error_type`. `metadata` echoes the `path`, `depth`, `max_turns`,
and active `focus`.

### Run only the passes you need

**Goal:** scope the review to one or two domains instead of all
three.

**Steps:**

```python
import asyncio

from attune.workflows import DeepReviewAgentSDKWorkflow


async def main() -> None:
    workflow = DeepReviewAgentSDKWorkflow()

    # Security pass only:
    sec = await workflow.execute(path="src/auth/", focus=["security"])
    print(sec.final_output)

    # Security + quality, skip test gaps:
    both = await workflow.execute(
        path="src/auth/", focus=["security", "quality"]
    )
    print(both.final_output)


asyncio.run(main())
```

**Verify:** `focus` accepts any subset of `"security"`,
`"quality"`, `"test-gaps"`. Only the named passes run, and
`metadata["focus"]` reflects the active set. An all-invalid
`focus` returns `success=False` with an "Invalid focus values"
error naming the valid options.
