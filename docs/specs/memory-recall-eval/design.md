# Design: Memory Recall-Accuracy Eval

**Status:** shipped (2026-07-20 — executed same day; benchmark
verdict in decisions.md)
**Requirements:** [requirements.md](requirements.md) ·
**Decisions:** [decisions.md](decisions.md)

---

## Architecture

One standalone, manually-run eval script; no durable infrastructure
(R6). Three pieces:

```text
scripts/eval_personal_memory_recall.py     # runner + metrics
  ├── CORPUS: ~18 hand-authored entries    # (topic, kind, content)
  ├── GROUND_TRUTH: query → expected topic # hand-authored (R3)
  │     ├── ~25 positive queries (1-2 per corpus entry)
  │     └── ≥5 negative queries (no good match — R4)
  └── run():
        tmp_root = tempfile.mkdtemp()                    # R1 isolation
        mem = PersonalMemory(global_root=tmp_root, ...)  # no project root
        for each corpus entry: mem.capture(topic, kind, content)
        for each query: hits = mem.query(q, k=3)
        metrics: hit@1, hit@3 (expected topic in result paths),
                 FP rate on negatives (criterion → OQ3)
        print a paste-ready markdown report block
```

The expected-topic check matches on the result's `path` field
(`.../<topic>/<kind>.md` — topic is recoverable from the path), so
ground truth stays a plain `(query, {expected_topics})` table with no
coupling to scores or excerpts.

Run keyless (`ANTHROPIC_API_KEY="" python scripts/…`) so
`capture()`'s polish step degrades to the deterministic skeleton path
and the run spends nothing and varies nothing (same empty-string
discipline as CI-keyless).

## Open questions (ruled 2026-07-20 — all option a; see decisions.md D1–D4)

- **OQ1 — Harness home.** (a) Standalone script under `scripts/`
  (RECOMMENDED — zero CI surface, no marker plumbing, matches R6
  "cheap, not infrastructure"); (b) pytest-marked test excluded from
  the default run (nicer fixtures, but adds marker/CI-exclusion
  plumbing for a run-once artifact).
- **OQ2 — Corpus write path.** (a) Real `capture()` under a keyless
  env (RECOMMENDED — exercises the actual write path incl. skeleton +
  summary generation, deterministic without a key); (b) write raw
  markdown files directly (fully controlled, but bypasses the write
  path the MCP tools actually use, weakening the verdict).
- **OQ3 — Negative-query FP criterion.** RAG always returns
  *something*, so "no match" needs a definition. (a) Relative
  threshold: FP = a negative query whose top-1 score ≥ the MINIMUM
  top-1 score among correctly-answered positive queries (RECOMMENDED —
  self-calibrating, no magic constant; degenerate cases — e.g. zero
  correct positives — reported as "criterion inapplicable" rather
  than a fake rate); (b) report-only: print negative-query top-1
  scores and let the verdict author judge (no automated rate — but
  "false-positive rate" is in Done-when); (c) fixed absolute score
  threshold (magic constant, brittle across pipeline changes).
- **OQ4 — Report destination.** (a) Script prints a paste-ready
  markdown block; the agent writes the dated `decisions.md` entry
  from it (RECOMMENDED — R5's "one clean entry" stays curated, no
  file-writing machinery); (b) script auto-appends to `decisions.md`
  (convenient, but a run-once script gains write access to a spec
  file for no real saving).

## Tasks

```xml
<task id="1" name="corpus-and-ground-truth">
  <objective>
    Author the benchmark corpus (~18 entries: 4 kinds, varied topics,
    realistic content per R2) and the hand-authored ground truth
    (~25 positive query→topic pairs, ≥5 negative queries) as data
    tables at the top of the eval script.
  </objective>
  <validation>
    <check>Every corpus entry has ≥1 positive query; every positive
      query's expected topic exists in the corpus (cross-check loop
      at script start)</check>
    <check>≥5 negative queries with no plausible corpus match (R4)</check>
  </validation>
  <risks>
    <risk severity="medium">Circular validation if queries are
      paraphrases of entry text — write queries the way a person asks
      ("what timeout did we pick for X?"), not by copying entry
      sentences (R3).</risk>
  </risks>
</task>

<task id="2" name="runner-and-metrics">
  <objective>
    Implement the isolated capture→query loop and metrics (hit@1,
    hit@3, FP rate per the ruled OQ3 criterion) in
    scripts/eval_personal_memory_recall.py; print a paste-ready
    markdown report (numbers + per-failure query/expected/got rows).
  </objective>
  <context>
    <existing-code path="src/attune/memory/personal.py">
      PersonalMemory(global_root=..., project_root=None);
      capture(topic, kind, content) writes root/topic/kind.md;
      query(q, k) returns dicts with path/summary/excerpt/score.
    </existing-code>
  </context>
  <validation>
    <check>Run is fully isolated: tmp root, keyless env; real
      ~/.attune and .attune/memory untouched (R1)</check>
    <check>Script exits nonzero if the corpus/ground-truth
      cross-check fails, so a broken table can't produce numbers</check>
  </validation>
</task>

<task id="3" name="run-and-verdict">
  <objective>
    Run the benchmark once against current PersonalMemory; record the
    dated decisions.md entry: hit@1/hit@3/FP numbers, 2-3 concrete
    failure examples, and a keep/tune/investigate verdict (R5).
  </objective>
  <validation>
    <check>decisions.md gains exactly one dated entry with all three
      numbers and a verdict line</check>
  </validation>
</task>

<task id="4" name="close-out">
  <objective>
    Flip spec status per the verdict (shipped if the eval delivered
    its number regardless of how good the number is), fix the
    cross-stamped status line that currently points at
    memory-feedback-signal work, and cross-link the verdict from the
    memory-subsystem-motivation memory.
  </objective>
</task>
```

## Sequencing

T1+T2 land together (one script), T3 is the run, T4 the close-out.
No CI, no new deps, no production-code changes — the only tracked
artifacts are the script, this design, and the decisions.md entries.
