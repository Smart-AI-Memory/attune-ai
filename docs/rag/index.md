# RAG-grounded code generation

Introduced in attune-ai v6.1.0 as the optional `[rag]`
extra. Backed by the standalone
[attune-rag](https://github.com/Smart-AI-Memory/attune-rag)
package.

## Install

```bash
pip install 'attune-ai[rag]'
```

This pulls in `attune-rag` and its bundled
`[attune-help]` corpus (633 templates across concepts,
quickstarts, tasks, references, errors, warnings, faqs,
and more).

## What it does

When you ask for code, attune-rag retrieves the most
relevant attune-help templates for your query, builds an
augmented prompt that clearly separates grounding context
from the user request, and feeds it to Claude. The output
comes back with a `## Sources` section listing clickable
links to every template that grounded the generation, so
you can verify the output against the authoritative source.

## Two surfaces

### 1. `rag-code-gen` workflow

```bash
attune workflow run rag-code-gen \
  --input '{"query": "how do I run a security audit?"}'
```

Returns a `WorkflowResult` whose `final_output` includes:

- The generated code or explanation
- A `## Sources` block with markdown links to the attune-help
  templates that grounded the answer

Kwargs:

| Arg | Type | Default | Notes |
|---|---|---|---|
| `query` | str | required | Your coding request |
| `k` | int | 3 | Max grounding docs to retrieve |
| `depth` | str | `standard` | `quick` / `standard` / `deep`. Controls max_turns + budget. |
| `feedback` | str | `None` | `good` / `bad`. Records verdict against every cited template via `help/feedback.py`. |
| `model` | str | `None` | Optional model override |

### 2. `rag_knowledge_query` MCP tool

For use from Claude Code or any MCP client. Returns
retrieval hits + an augmented prompt string. **Does not
call an LLM** — you or your agent do that separately.

```json
{
  "name": "rag_knowledge_query",
  "arguments": {
    "query": "how do I run a security audit?",
    "k": 3
  }
}
```

Returns:

```json
{
  "success": true,
  "fallback_used": false,
  "confidence": 1.0,
  "elapsed_ms": 58.0,
  "corpus": "attune-help",
  "retriever": "KeywordRetriever",
  "augmented_prompt": "### CONTEXT...\n### USER REQUEST...",
  "hits": [
    {
      "template_path": "concepts/tool-security-audit.md",
      "category": "concepts",
      "score": 9.0,
      "excerpt": "Security audit scans for vulnerabilities..."
    }
  ]
}
```

## Graceful behavior when the extra isn't installed

Without `pip install 'attune-ai[rag]'`:

- The `rag-code-gen` workflow still loads but
  `execute()` returns a `WorkflowResult` with
  `success=False` and a clear "install
  attune-ai\[rag\]" hint
- The `rag_knowledge_query` MCP tool remains registered in
  the schema; the handler returns a structured
  `{success: false, error, cause}` dict pointing at the
  install command

No exception propagates to the CLI or MCP dispatcher.

## Feedback and learning

If you pass `feedback="good"` or `feedback="bad"` to
`rag-code-gen`, the workflow calls
`attune.help.feedback.record_template_feedback` for every
cited template. These verdicts feed `get_template_confidence`
so future grounding can bias toward historically-good
templates. Silent usage does not record anything.

## Baseline retrieval quality

See the benchmark harness at
[github.com/Smart-AI-Memory/attune-rag](https://github.com/Smart-AI-Memory/attune-rag/blob/main/tests/golden/queries.yaml)
and the decision record at
[embeddings-decision-2026-04-17.md](embeddings-decision-2026-04-17.md).

Baseline (keyword retriever, 15 golden queries against
attune-help 0.5.1):

| Difficulty | Precision@1 | Recall@3 |
|---|---|---|
| Easy (5) | 80% | 100% |
| Medium (4) | 100% | 100% |
| Hard (6) | 0% | 0% |
| Overall | 53% | 60% |

The hard queries all fail with the same pattern —
lesson/error files with query keywords in their filenames
outrank the concept files that answer the question.
Targeted fix is category-biased keyword weighting
(planned for attune-rag v0.1.x); local ONNX embeddings
via `fastembed` are queued as a v0.2.0 fallback if
tuning plateaus below 70% P@1.

## Using attune-rag standalone

attune-rag is LLM-agnostic and corpus-pluggable. You can
use it outside attune-ai with any LLM:

```bash
pip install 'attune-rag[attune-help,claude]'
```

```python
import asyncio
from attune_rag import RagPipeline

async def main():
    pipeline = RagPipeline()  # defaults to AttuneHelpCorpus
    response, result = await pipeline.run_and_generate(
        "How do I run a security audit with attune?",
        provider="claude",
    )
    print(response)
    print("Sources:", [h.template_path for h in result.citation.hits])

asyncio.run(main())
```

See the [attune-rag README](https://github.com/Smart-AI-Memory/attune-rag#readme)
for OpenAI and Gemini quickstarts and for using your own
markdown corpus.
