# Rag Grounding

## Quickstart

Ask a grounded question and print the answer with its sources.
`execute` is a coroutine, so drive it with `asyncio.run`:

```python
import asyncio

from attune.workflows import RagCodeGenWorkflow


async def main() -> None:
    workflow = RagCodeGenWorkflow()
    result = await workflow.execute(query="How do I run a security audit?")

    print(result.success)        # True on a completed run
    print(result.final_output)   # generated answer + a ## Sources block


asyncio.run(main())
```

`k` defaults to 3 and `depth` to `"standard"`, so
`execute(query=...)` is equivalent.

## Tasks

### Generate a grounded answer from Python

**Goal:** answer a coding question grounded in attune docs, with
citations.

**Steps:**

```python
import asyncio

from attune.workflows import RagCodeGenWorkflow


async def main() -> None:
    workflow = RagCodeGenWorkflow()
    result = await workflow.execute(query="How do I customize release gates?", k=5)

    if not result.success:
        print("generation failed:", result.error)
        return

    print(result.final_output)               # answer + ## Sources
    print(result.metadata["citation"])       # structured provenance


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. `k` controls how
many passages are retrieved. The output ends with a `## Sources` block;
`metadata["citation"]["hits"]` lists each cited template with its
`template_path`, `category`, and `score`.

### Run it from the CLI

**Goal:** get a grounded answer without writing Python.

**Steps:**

```bash
# query is passed as JSON input; the workflow slug is rag-code-gen:
attune workflow run rag-code-gen --input '{"query": "how do I run a security audit?"}'

# deeper run, JSON output:
attune workflow run rag-code-gen --input '{"query": "...", "k": 5}' --depth deep --json
```

**Verify:** the slug is `rag-code-gen` (not `rag-grounding`, which is
the feature/help name). `--input` / `-i` takes JSON carrying `query`
(and optional `k`); `--depth` accepts `quick` / `standard` / `deep`;
`--json` / `-j` emits machine-readable output.

### Tune retrieval breadth and cost

**Goal:** trade grounding breadth against speed and cost.

**Steps:**

```python
import asyncio

from attune.workflows import RagCodeGenWorkflow


async def main() -> None:
    workflow = RagCodeGenWorkflow()
    result = await workflow.execute(query="explain the memory tiers", k=2, depth="quick")
    print(result.final_output)


asyncio.run(main())
```

**Verify:** lower `k` retrieves fewer passages (faster, narrower
grounding); `quick` uses the smallest turn budget (6) and lowest cap
($2). `metadata["retrieval_ms"]` reports retrieval time.

## Reference

The public surface is `RagCodeGenWorkflow`, re-exported from
`attune.workflows`.

### `RagCodeGenWorkflow` — `attune.workflows.rag_code_gen`

| Symbol | Purpose |
|--------|---------|
| `RagCodeGenWorkflow(**kwargs)` | Construct the workflow (pipeline is lazily initialized on first `execute`). |
| `RagCodeGenWorkflow.execute(**kwargs)` | **Async.** Retrieve + generate. Honors `query` (required), `k`, `depth`, `feedback`, `model`, `path` (and deprecated `cwd`). Returns a `WorkflowResult`. |
| `RagCodeGenWorkflow.name` | The registered CLI slug, `"rag-code-gen"`. |
| `RagCodeGenWorkflow.stages` | `["retrieve", "generate"]` — retrieve at `CHEAP` (zero-LLM), generate at `CAPABLE`. |

### Depth → turns and budget

| Depth | Max turns | Budget cap | Notes |
|-------|-----------|------------|-------|
| `quick` | 6 | $2 | Narrowest, cheapest. |
| `standard` | 12 | $10 | Default. |
| `deep` | 24 | $25 | Enables extended thinking. |

### `WorkflowResult` fields read after a run

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the run completed. |
| `final_output` | `Any` | Generated answer followed by a `## Sources` citations block. |
| `summary` | `str \| None` | Short overview. |
| `metadata` | `dict` | `query`, `depth`, `max_turns`, `citation` (structured provenance), `fallback_used`, `confidence`, `retrieval_ms`, `feedback_recorded`. |
| `error` | `str \| None` | Failure reason (e.g. missing `query`, bad `k`, unknown `model`, RAG retrieval failure). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Python | `await RagCodeGenWorkflow().execute(query=<q>, k=<n>, depth=<d>)`. |
| CLI | `attune workflow run rag-code-gen --input '{"query": "<q>"}' [--depth ...] [--json]`. |
| Skill | `/rag-code-gen` in a Claude Code conversation. |

There is no dedicated MCP tool for this workflow.

<!-- attune-generated: source_hash=80d56595472151a9fe49e1354a100b17b22eefbeaefb0d01d9a569f85b28b5a4 feature=rag-grounding kind=how-to generated_at=2026-06-23 -->
