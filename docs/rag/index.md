# RAG-grounded code generation

Introduced in attune-ai v6.1.0 as the optional `[rag]`
extra. Backed by the standalone
[attune-rag](https://github.com/Smart-AI-Memory/attune-rag)
package.

## Install

```bash
pip install attune-ai
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

## Graceful behavior when `attune-rag` is missing

`attune-rag` is a **core dependency** — `pip install attune-ai` always
brings it. (A legacy `[rag]` extra existed as an empty back-compat
alias and was deleted 2026-07-17.) So this path only fires on a broken
or partial install, and the remediation names the real package:

- The `rag-code-gen` workflow still loads but
  `execute()` returns a `WorkflowResult` with
  `success=False` and a hint to reinstall with
  `pip install attune-rag`
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

## Retrieval quality

See the benchmark harness at
[github.com/Smart-AI-Memory/attune-rag](https://github.com/Smart-AI-Memory/attune-rag/blob/main/tests/golden/queries.yaml)
and the decision record at
[embeddings-decision-2026-04-17.md](embeddings-decision-2026-04-17.md).

Current (keyword retriever + category-biased weighting,
15 golden queries against the attune-help 0.7.0 corpus):

| Metric | Value |
|---|---|
| Precision@1 | **73.3%** |
| Recall@3 | 86.7% |

The local-ONNX-embeddings (`fastembed`) track is deferred
— tuning cleared the pre-committed 70% P@1 gate on the
keyword retriever alone. See
[embeddings-decision-2026-04-17.md](embeddings-decision-2026-04-17.md)
for the decision matrix and gate definitions.

## Faithfulness & citation grounding

attune-rag 0.1.3 made **citation-forced prompting** the
default, delivering **0.996 mean per-claim faithfulness —
over 99% of generated claims are grounded in their cited
passages (under 1% hallucinated per claim)**. Retrieval is
identical across variants (P@1 = 73.3% in all three rows
below) — the gain is pure prompting. The per-query bucket
rate (the conservative "any ungrounded claim disqualifies
the response" measurement) is shown alongside for
completeness; the per-claim number is the right answer to
"how trustworthy is each statement":

| Prompt variant | Per-claim faithfulness | Per-query hallucination |
|---|---|---|
| baseline (no grounding rule) | 0.938 | 46.67% |
| strict ("answer only from context") | 0.968 | 26.67% |
| **citation** (default) | **0.996** | **6.67%** |

Every claim the model makes must be followed by a
`[P1]`/`[P2]` marker pointing at the passage that supports
it. No citation = no claim; the model refuses rather than
guessing. Full methodology and raw JSON:

- [faithfulness-decision-2026-04-19.md](faithfulness-decision-2026-04-19.md)
  — decision writeup with pre-committed gate (≥ 0.85 mean
  faithfulness to ship)
- [ab-report-2026-04-19.json](ab-report-2026-04-19.json)
  — machine-readable results, all four variants,
  per-query judgments

attune-rag 0.1.5 additionally wraps retrieved passages in
`<passage id="P1">...</passage>` sentinel tags with a
system-prompt injection-defense clause — adversarial
bytes inside a corpus document are treated as data, not
instructions.

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
