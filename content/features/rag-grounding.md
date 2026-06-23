---
feature: rag-grounding
summary: RAG-grounded code generation — retrieves attune context and emits answers with source citations
tags: [rag, retrieval, grounding, faithfulness, citation]
source_globs:
  - src/attune/workflows/rag_code_gen.py
nav:
  help: rag-grounding
  mkdocs:
    how-to: how-to/rag-grounding
    architecture: architecture/rag-grounding
    reference: reference/rag-grounding
---

## Overview

RAG grounding anchors generated code and explanations to **retrieved
attune documentation**, so every answer cites real APIs, workflow
names, and CLI commands instead of inventing them. The workflow
retrieves context from a RAG corpus (attune-help by default), feeds a
citation-forced prompt to a single Claude Agent SDK call, and returns a
`WorkflowResult` whose output ends with a markdown `## Sources` block
for provenance.

The class is **`RagCodeGenWorkflow`**. Note the naming: the **feature**
(and this help topic) is `rag-grounding`, while the **workflow slug**
registered for the CLI is `rag-code-gen` — both name the same
`RagCodeGenWorkflow`.

Two things distinguish it from the other SDK workflows:

- **Retrieval happens before the LLM call.** A synchronous
  `attune_rag.RagPipeline` fetches grounding passages first; the single
  agent then generates against them. There are no subagents.
- **Faithfulness is enforced.** The system prompt forbids inventing
  attune features and wraps retrieved passages in `<passage>` sentinels
  as prompt-injection defense.

You reach it these ways:

- the Python API — `from attune.workflows import RagCodeGenWorkflow`;
- the CLI — **`attune workflow run rag-code-gen`**;
- the **`/rag-code-gen`** skill, inside a Claude Code conversation.

`execute` is async — `await` it.

## Concepts

### Retrieve, then generate

`RagCodeGenWorkflow` runs two stages — `retrieve` (zero-LLM,
tagged `CHEAP`) and `generate` (`CAPABLE`):

1. **Retrieve.** `attune_rag.RagPipeline().run(query, k=k,
   prompt_variant="citation")` fetches `k` grounding passages and
   builds an augmented prompt. Passages arrive wrapped in
   `<passage>...</passage>` tags.
2. **Generate.** A single Claude Agent SDK call (the `rag-generator`
   agent, tools `Read` / `Glob` / `Grep`) generates against the
   augmented prompt. The result text is concatenated with a markdown
   citations block.

### Faithfulness and prompt-injection defense

The system prompt instructs the model to cite only what the retrieved
context attests and never to invent attune features. Because retrieved
content arrives inside `<passage>` tags, the prompt treats everything
inside them as documentation — even a literal `</passage>` escape is
read as content, not a command. Claim hallucination and prompt
injection are separate threat models; the workflow guards both.

### `execute` is async and `query` is required

`execute(**kwargs)` is a coroutine — `await` it (or use `asyncio.run`).
`query` is required; an empty/whitespace query returns a failed
`WorkflowResult` ("query argument is required") rather than raising.
The supported kwargs:

| kwarg | Default | Meaning |
|-------|---------|---------|
| `query` | — (required) | The coding request to ground and answer. |
| `k` | `3` | Number of grounding passages to retrieve. |
| `depth` | `"standard"` | `"quick"` / `"standard"` / `"deep"` — sets max turns and budget. |
| `feedback` | `None` | `"good"` / `"bad"` — records feedback on every cited template. |
| `model` | `None` | Optional generation model override (allowlisted against `MODEL_REGISTRY`). |
| `path` | `os.getcwd()` | Working directory scoping the agent's `Read`/`Glob`/`Grep` tools. |
| `cwd` | — | **Deprecated** alias for `path` (emits `DeprecationWarning`). |

A non-integer `k` or an unknown `model` returns a failed
`WorkflowResult` rather than crashing.

### Depth controls turns and budget

| Depth | Max agent turns | Budget cap |
|-------|-----------------|------------|
| `quick` | 6 | $2 |
| `standard` | 12 | $10 |
| `deep` | 24 | $25 |

An unrecognized depth falls back to the standard budget (12 turns).
`deep` additionally enables extended thinking. Override the cap with
`ATTUNE_MAX_BUDGET_USD`.

### attune-rag is a core dependency

Retrieval needs the `attune-rag` package — a **core** dependency (the
legacy `[rag]` extra is an empty back-compat placeholder). If it's
missing, the first `execute` raises a `RuntimeError` pointing at
`pip install attune-rag`.

### Output carries its provenance

The generated text is followed by a markdown `## Sources` block (built
by `attune_rag.provenance.format_citations_markdown`) with clickable
links to the cited attune-help templates. `metadata` carries a
structured `citation` dict (query, retriever, hits with
`template_path` / `category` / `score`), plus `fallback_used`,
`confidence`, and `retrieval_ms`.

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

## Comparison

RAG grounding is the **citation-forced generation** workflow. It is
distinct from a plain code-generation call and from documentation
retrieval:

| Tool | Role |
|------|------|
| `rag-grounding` (this feature, slug `rag-code-gen`) | Retrieve attune context, then generate a cited answer. |
| `doc-gen` | Generate documentation from your source code (no RAG retrieval). |
| `rag_knowledge_query` (MCP) | Query the attune-help corpus directly, without an LLM generation step. |

Reach for **rag-grounding** when you want a generated answer that cites
real attune APIs/CLI/workflows; reach for `rag_knowledge_query` when
you just want the retrieved passages.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'RagCodeGenWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `error` is `"query argument is required"` | `execute` called with an empty/missing `query` | Pass a non-empty `query` | high |
| `RuntimeError: ... needs the attune-rag package ...` | `attune-rag` (a core dependency) is not installed | `pip install attune-rag` | high |
| `error` is `"RAG retrieval failed: ..."` | The pipeline raised (corpus I/O, connection, timeout, bad variant) | Check corpus availability / connectivity; retry | medium |
| `error` is `"k argument must be an integer ..."` | `k` wasn't an int (e.g. `k="bad"`) | Pass an integer `k` | low |
| `error` is `"unknown model ..."` | `model` isn't in `MODEL_REGISTRY` | Use a registered model id, or omit `model` | low |
| `DeprecationWarning` about `cwd=` | Passing the deprecated `cwd` alias | Use `path=` instead | low |

### Risk areas

- **The async call is easy to get wrong.** `execute` is a coroutine;
  forgetting to `await` it is the most common mistake.
- **`attune-rag` must be installed.** It's a core dependency, not an
  optional extra — the workflow can't retrieve without it.
- **Slug vs. feature name.** The CLI slug is `rag-code-gen`; the
  feature/help topic is `rag-grounding`.

### Diagnosis order

1. Confirm you are awaiting: `await workflow.execute(query="...")`.
2. Check `result.success`; if `False`, read `result.error`.
3. If the error mentions attune-rag, `pip install attune-rag`.
4. For a retrieval failure, check corpus availability and connectivity.
5. Inspect `result.metadata["citation"]` to see what was retrieved.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic source
> of truth fed by four channels — unmatched user queries, telemetry
> error-frequency, GitHub issues, and these author-curated seeds —
> merged, deduplicated, and frequency-ranked by the FAQ Generator (see
> doc-stack D3, and the help-docs-single-source spec's decisions.md D6).
> This section is **not** projected verbatim as the FAQ; it contributes
> the feature's author-curated seed questions.

- **Q:** What does rag-grounding do?
  **A:** It retrieves attune documentation and generates an answer that
  cites real APIs/workflows/CLI commands — never invented ones —
  ending with a `## Sources` block.
- **Q:** Why is the CLI slug `rag-code-gen` but the feature
  `rag-grounding`?
  **A:** Both name the same `RagCodeGenWorkflow`. `rag-code-gen` is the
  registered workflow slug; `rag-grounding` is the feature/help topic.
- **Q:** Are the calls async?
  **A:** Yes — `execute` is a coroutine. `await` it or use
  `asyncio.run`.
- **Q:** Do I need attune-rag installed?
  **A:** Yes — it's a core dependency. Without it the workflow raises a
  `RuntimeError` pointing at `pip install attune-rag`.
- **Q:** How do I control how much context is retrieved?
  **A:** Set `k` (number of passages, default 3) and `depth` (turn /
  budget tier).

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `RagCodeGenWorkflow` and its async `execute`, and the
  `WorkflowResult` it returns. Names with a leading underscore —
  `_get_pipeline`, `_run_agent_generate`, `_record_feedback` — are
  internal.
- **Prefer `path` over `cwd`.** `cwd` is a deprecated alias kept for
  back-compat; pass `path=` to scope the agent's file tools.
- **Use `k` and `depth` to tune cost.** Fewer passages and a shallower
  depth make a cheaper, faster run.
- **Read the citations.** The `## Sources` block and
  `metadata["citation"]` let you verify each claim against the real
  attune-help template.

## Design & extension

### Design decisions

- **Retrieve before generate, no subagents.** Retrieval is synchronous
  and zero-LLM; a single agent generates against the augmented prompt.
  Keeping it one agent makes the cost and provenance easy to reason
  about.
- **Faithfulness by construction.** The citation-forced system prompt
  plus `<passage>` sentinels make the model cite retrieved sources and
  resist prompt injection — claim hallucination and injection are
  guarded as separate threat models.
- **Provenance travels with the answer.** Citations are appended to
  the output and mirrored as a structured `metadata["citation"]` dict,
  so both humans and programs can trace every claim.
- **Inputs are validated and scoped.** `query`, `k`, and `model` are
  validated up front (structured `WorkflowResult` errors, not crashes),
  and the agent's file tools are scoped to `path` (default the caller's
  cwd) to contain prompt-injected reads.

### Extension points

- **Change retrieval breadth:** set `k`.
- **Trade cost vs. depth:** choose `depth` (`quick` / `standard` /
  `deep`) or set `ATTUNE_MAX_BUDGET_USD`.
- **Override the model:** pass a registered `model` id.
- **Record feedback:** pass `feedback="good"` / `"bad"` to score the
  cited templates via `record_template_feedback`.
- **Scope file access:** pass `path=` to bound the agent's
  `Read`/`Glob`/`Grep` tools.
