# Decisions: Memory Recall-Accuracy Eval

Results and verdicts from running the benchmark described in
`requirements.md`. One dated entry per run.

---

## 2026-07-01 — Run 1: `PersonalMemory.query()` is completely broken

**Numbers:** hit@1 = 0/18 (0.0%), hit@3 = 0/18 (0.0%), false positives
= 0/5 (0.0%, vacuously — see below).

**Root cause (confirmed, not inferred):** `PersonalMemory.query()`
([personal.py:230](../../../src/attune/memory/personal.py#L230)) calls
`RagPipeline.run(query, k=k*2)` and does `for hit in results:` —
treating the return value as an iterable of hit dicts. But the
installed `attune_rag` (0.1.23) has `RagPipeline.run() -> RagResult`,
a dataclass that is **not iterable**. Every call raises
`TypeError: 'RagResult' object is not iterable`, caught by `query()`'s
broad `except Exception` (logged as `personal_memory_query_failed`),
and silently returns `[]`. Confirmed directly:

```
>>> for hit in pipeline.run("...", k=6): ...
TypeError: 'RagResult' object is not iterable
```

This means the entire `personal_memory_recall` MCP tool (and anything
else calling `PersonalMemory.query()`) has been returning empty
results unconditionally — not "weak recall," **zero recall, always**
— since whenever `attune_rag`'s `RagPipeline.run()` signature changed
to return `RagResult` instead of a list (0-hit-count events even log
success internally: `rag.run ... hit_count=1 ... confidence=1.0`, so
the underlying retrieval works fine, only the caller's unwrapping is
broken). The 0.0% false-positive rate is **not evidence of good
precision** — it's the same total failure applied to negative
queries too; both numbers are artifacts of the same bug, not signal.

**The real API** (confirmed via `src/attune/workflows/rag_code_gen.py`,
which already consumes `RagResult` correctly):
`rag_result.citation.hits` is a tuple of `CitedSource(template_path,
category, score, excerpt, ...)`. `query()` needs to iterate
`results.citation.hits` and read `.template_path`/`.category`/
`.score`/`.excerpt` instead of dict-style `.get(...)` on `results`
directly.

**Verdict: investigate → fix, not tune.** This is a plain integration
bug (API drift against a dependency), not a taxonomy or ranking-quality
question. Not scoped as a fix in this spec's non-goals originally, but
given the severity (100% of recall calls fail silently, in production,
via the MCP tool surface Patrick actually uses), flagged to Patrick for
an immediate fix rather than deferred as a "later" follow-up — see
session transcript 2026-07-01.

**Fixed same session** — `add_finding()`-adjacent bug, same root cause
class as the memory-nodetype-friction-log spec's fix note, different
file: `PersonalMemory.query()`
([personal.py:230-241](../../../src/attune/memory/personal.py#L230-L241))
now unwraps `rag_result.citation.hits` (each a `CitedSource` with
`.template_path`/`.category`/`.score`/`.excerpt`) instead of iterating
the `RagResult` dataclass directly, matching the pattern already used
correctly in `src/attune/workflows/rag_code_gen.py`.

## 2026-07-01 — Run 2: post-fix numbers

**hit@1 = 18/18 (100%), hit@3 = 18/18 (100%).** Every positive query
now returns its expected topic as the top result.

**False-positive rate: not a clean binary — reported as score
distributions instead.** The first pass used an arbitrary
`score > 0.3` cutoff, which was wrong: `score` is an **unbounded raw
keyword-overlap count**, not a normalized `[0,1]` confidence, so no
universal absolute threshold applies. Corrected methodology: report
sorted top-1 scores for positive vs. negative queries and let the gap
speak for itself.

- Positive-query top-1 scores (sorted): `[4.5, 7.0, 8.0, 9.0, 10.0,
  10.0, 10.0, 11.5, 12.0, 12.5, 13.0, 14.0, 14.0, 14.5, 16.5, 18.5,
  18.5, 21.0]`
- Negative-query top-1 scores (sorted): `[0.0, 2.5, 2.5, 3.0, 5.5]`

There's a real but **imperfect** separation: 4 of 5 negative queries
score well below the positive floor (4.5), but one — "What's our
policy on remote work days per week?" (top result:
`test-flake-quarantine-policy/reference.md`, score 5.5) — lands above
the lowest positive score (4.5, for "How long do we have to write a
postmortem?"). Both queries share the generic word "policy"/no
distinctive keyword overlap with their matched doc beyond incidental
word repetition — a real limitation of pure keyword-overlap retrieval
(`KeywordRetriever`), not a bug. A caller using a fixed score cutoff to
gate confidence would occasionally surface a wrong result as if it
were a real match, or suppress a genuine low-keyword-overlap match.

**Verdict: keep as-is for now, with a noted limitation.** Recall
accuracy (hit@1/hit@3) is excellent post-fix — 100% on this corpus.
Precision has a soft edge case inherent to keyword-only retrieval, not
worth chasing given `attune.memory.PersonalMemory` is still lightly
used; revisit if/when real usage surfaces an actual bad-match incident,
or if `attune_rag` grows a semantic retriever option.
