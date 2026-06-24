---
name: rag-grounding
source: content/features/rag-grounding.md
tags:
- rag
- retrieval
- grounding
- faithfulness
- citation
type: note
---

# RAG-grounded code generation — retrieves attune context and emits answers with source citations

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
