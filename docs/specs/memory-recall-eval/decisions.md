# Decisions: Memory Recall-Accuracy Eval

**Status:** shipped (2026-07-20) — benchmark run, verdict: keep
as-is, no tuning owed (final entry below).

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

## 2026-07-01 — Run 3: cross-process persistence confirmed

**Question:** Runs 1–2 captured and queried within the *same*
`PersonalMemory` instance and process. Does recall survive process
death — i.e., is the store genuinely file-backed with no hidden
in-process state?

**Method:** added `--phase persistence` to
[scripts/memory_recall_eval.py](../../../scripts/memory_recall_eval.py):
the corpus is captured by one subprocess, which then **exits** (taking
its `PersonalMemory` instance with it); a second subprocess constructs
a brand-new instance pointed at the same on-disk `global_root` and runs
the identical query set. Results pass back via a JSON file (not stdout
— `attune_rag`'s structlog lines print to stdout and corrupt inline
JSON; noted here in case a future consumer tries to pipe it).

**Result: identical to Run 2 in every dimension.**

- hit@1 = 18/18 (100%), hit@3 = 18/18 (100%)
- Positive top-1 scores: `[4.5, 7.0, 8.0, 9.0, 10.0, 10.0, 10.0, 11.5,
  12.0, 12.5, 13.0, 14.0, 14.0, 14.5, 16.5, 18.5, 18.5, 21.0]` — same
- Negative top-1 scores: `[0.0, 2.5, 2.5, 3.0, 5.5]` — same, including
  the same soft-overlap case (`test-flake-quarantine-policy` at 5.5)

**Verdict: persistence holds.** Capture-side writes are durable and the
query side reconstructs retrieval purely from disk — no warm-instance
advantage, no cold-start penalty, no state lost at process exit. The
"probably fine mechanically" assumption from the session handoff is now
a measured fact. The single-process default (`--phase all`) reproduces
the same numbers, so the two methodologies are interchangeable for
future runs; use `--phase persistence` when the change under test
touches serialization or file layout.

## 2026-07-01 — Sanity check: `MemoryGraph.find_similar` (deferred non-goal, spot-checked)

The non-goals deferred `MemoryGraph` recall to a future experiment;
given Run 1 found `PersonalMemory.query()` silently dead, a cheap
spot-check was worth it. Done during the first real curated-memory
captures (see
`docs/specs/memory-nodetype-friction-log/decisions.md`, Friction C):

- **Not the dead-path class.** A verbatim node name self-matches at
  score 1.0 — the mechanism (Jaccard word-overlap over
  name/description, type/file bonuses) works.
- **But the default `threshold=0.5` mutes realistic queries.** A
  natural paraphrase ("recall benchmark persistence numbers") scored
  0.301 / 0.125 against nodes it should plausibly find — both filtered
  at the default. Callers get `[]` for anything short of near-verbatim
  names, which *reads* like the query() bug from the outside.
- **Workaround:** pass `threshold≈0.25`, or use
  `PersonalMemory.query()` for text recall.

No full ground-truthed benchmark run for `find_similar` yet — this was
a spot-check, not Run 4. If curated-graph usage grows (friction-log
spec), rerun this corpus's methodology against `find_similar` with a
tuned threshold.

## 2026-07-13 — Re-filed from trap-battery: style rules are structurally unreachable by BOTH recall surfaces

**Finding (from the trap-battery phase-1 forensics — see
[benchmarks/trap_battery_results_2026-07-13.md](../../../benchmarks/trap_battery_results_2026-07-13.md)
and `docs/specs/trap-battery/decisions.md`):** the `question-shape`
trap's ON≈OFF result has a structural cause on the recall-triggering
axis, independent of the pilot's injection-arms confound:

- **JIT (PreToolUse) path: no matching moment.** The trap's only
  allowed tool is `Read`, and the JIT matcher covers
  `AskUserQuestion|Bash|Edit` — a rule about the shape of the FINAL
  MESSAGE has no tool-call decision point at all, so PreToolUse
  recall can never carry it.
- **Prompt-time (UserPromptSubmit) path: below the floor.** Direct
  execution of `lesson_recall.py` on the trap prompt returns nothing —
  the lesson scores under the 8.0 relevance floor. Nothing about a
  "summarize/answer" prompt surface-matches a rule about response
  formatting.

**Consequence for this spec:** recall evals scoped to content recall
(hit@k on topical queries) cannot see this failure class. A
style/format rule is only live if (a) some surface fires at
message-composition time or (b) the prompt-time scorer can match
rules by APPLICABILITY (the reply will contain a closing question)
rather than topical overlap. Neither exists today — style rules are
dead weight in the corpus until one does.

**Disposition:** recorded here as a known structural gap; the
trap-battery phase-2 redesign owns the measurement side
(UserPromptSubmit-carried rules measure prevention; JIT-carried rules
measure recovery only). No eval re-run scheduled against style rules
until a carrying surface exists.

## 2026-07-14 — Injection feedback signal, step 1: complete per-surfacing capture records

**Context:** the recommit (2026-07-14 triage) points this spec at the
memory-as-insurance feedback signal — label each injection acted-on /
ignored / wrong so the noise denominator builds itself
(`project_memory_as_insurance`). Prerequisite audit found the capture
side incomplete; this entry records the design shipped to close it.

**What the audit found (pre-change state):**

- `plugin/hooks/lesson_recall.py` (prompt-time recall) emitted **no
  telemetry at all** — it computed `lesson_id` + score per hit, then
  discarded them. The largest hole: prompt-time surfacings were
  invisible to any later analysis. Corollary:
  `benchmarks/trap_battery.py`'s comment claiming "every
  jit_recall/lesson_recall fire appends a line" was false — the
  phase-2 runs (2026-07-13/14) undercounted prompt-time injections in
  their telemetry receipts (caveat now recorded at the
  `MEMORY_EVENTS_LOG` definition).
- `jit_recall` logged `tool` + `rules` + size but no join key and no
  record of WHICH gate (substring/regex/tool-keyed) fired each rule.
- `session_recall` logged only an aggregate entry count — not which
  findings were surfaced.
- No event anywhere carries an `acted_on`/`ignored`/`wrong` verdict;
  the only outcome signal is `memory_feedback` (stash deletion), which
  covers stashed findings, not surfaced rules/lessons.

**Design shipped (capture side):** every injection surface now writes
a complete, joinable surfacing record to
`~/.attune/telemetry/memory_events.jsonl`:

- **`lesson_recall` (new event):** `lessons` (parallel `scores`),
  `surfacing_id`, `injected_chars`/`est_tokens`.
- **`jit_recall` (enriched):** adds `surfacing_id` and `triggers`
  (parallel to `rules`; values `tool` | `substring` | `regex` |
  `substring+regex`).
- **`session_recall` (enriched):** adds `surfacing_id` and
  `finding_ids` (ids of the findings actually rendered; id-less
  records still count in `entries`).
- **`surfacing_id`** (12-hex uuid per event) is the join key a later
  verdict event references; per-item verdicts key on
  `(surfacing_id, lesson_id|rule_id|finding_id)`.

Receipts: unit suites green (125 tests across the four hook suites;
the one failure is the pre-existing real-Ollama environmental flake,
confirmed failing on the untouched baseline) + live subprocess
round-trips of both hooks with an isolated `ATTUNE_HOME` showing the
new records on disk.

**Step 2 (scoped, not built — the verdict scorer):** the Stop hook
(`plugin/hooks/session_stash.py`) already parses the transcript tail
at end-of-session; it is the natural place to correlate the session's
surfacing records against the transcript and emit a `memory_signal`
verdict per surfacing (`acted_on` / `ignored` / `wrong`), reusing its
Ollama-with-fallback pattern — with `unscored` (not a guessed
heuristic label) when Ollama is unavailable, because a garbage label
is worse than none. Plus an `ops/data.py` reader that turns verdicts
into the noise denominator `estimate_intervention_signal`'s caption
says is missing. Design pass owed before build.

## 2026-07-20 — Design approved: OQ1–OQ4 ruled (chair: Patrick)

Design pass for this spec's own content (the PersonalMemory
recall-accuracy benchmark — NOT the feedback-signal step-2 scorer,
which is homed in `docs/specs/memory-feedback-signal/`; the
cross-stamped status line pointing there is corrected as part of
this entry). All four open questions ruled as recommended
(`1a 2a 3a 4a`); see [design.md](design.md) for the full option
text.

- **D1 — Harness home: standalone script**
  (`scripts/eval_personal_memory_recall.py`). Zero CI surface, no
  marker plumbing; matches R6 "cheap, not infrastructure."
- **D2 — Corpus write path: real `capture()` under a keyless env**
  (`ANTHROPIC_API_KEY=""`). Exercises the actual write path the MCP
  tools use; polish degrades to the deterministic skeleton, zero
  spend, zero variance.
- **D3 — Negative-query FP criterion: self-calibrating threshold.**
  FP = a negative query whose top-1 score ≥ the minimum top-1 score
  among correctly-answered positive queries; degenerate cases
  reported as "criterion inapplicable," never a fake rate.
- **D4 — Report destination: script prints a paste-ready markdown
  block**; the agent writes the single dated decisions.md entry
  (R5). No script write-access to spec files.

Execution armed: T1–T4 per design.md's task blocks.

## 2026-07-20 — Benchmark run 1: results + verdict (T3)

Run per D1–D4: `ANTHROPIC_API_KEY="" .venv/bin/python
scripts/eval_personal_memory_recall.py` — 18-entry corpus (4 kinds),
26 positive / 6 negative hand-authored queries, isolated tmp roots
(global + explicit project root, neither under `~/.attune` or the
repo), keyless so `capture()` stayed on the deterministic skeleton
path. Retriever in play: `KeywordRetriever` (lexical), per-query
~3 ms.

**Numbers:**

- **hit@1: 25/26 (96%)**
- **hit@3: 26/26 (100%)**
- **FP rate: 0/6 (0%)** — D3 criterion; threshold = min
  correct-positive top-1 score (3.0); three negatives returned zero
  hits outright, three returned weak hits (score 2.5) below
  threshold.

**The one hit@1 miss (concrete example):** "where should API keys be
stored on this machine?" → `keyless-test-runs` at rank 1 and the
expected `secret-storage-location` at rank 2 with IDENTICAL scores
(5.0 vs 5.0) — a tie-break ordering loss, not a retrieval miss.

**Verdict: keep as-is.** Write-then-recall round-trips correctly;
ranking is accurate at k=3 with zero false-positive over-confidence
on no-match queries. No tuning owed. Honest caveat for future
readers: the retriever is keyword-based, so these numbers cover
natural-question phrasing with SOME vocabulary overlap (how people
actually query); pure-paraphrase robustness with zero shared terms
is untested and would be the first probe if a live recall complaint
ever contradicts this verdict. Longitudinal re-runs stay a
non-goal (R6) unless that happens.

## 2026-07-20 — Close-out (T4): spec shipped

All Done-when items met: corpus + ground truth exist
(`scripts/eval_personal_memory_recall.py`, self-cross-checking),
benchmark run once against current `PersonalMemory`, this file
carries the numbers + failure example + verdict. Status flipped to
shipped across the three phase files; the cross-stamped status line
was corrected in the design-approval entry above.

## 2026-08-28 — Re-run (chair-directed): D3's zero-FP verdict no longer holds

R6 made longitudinal re-runs a non-goal "unless a live recall complaint
ever contradicts this verdict". This run was chair-directed rather than
complaint-driven, so R6 is not amended — the chair asked for a recall
quality measurement while assessing whether the Redis/memory
implementation was acceptable.

Run exactly as run 1 (D1–D4): `ANTHROPIC_API_KEY=""
scripts/eval_personal_memory_recall.py`, 18-entry corpus, 26 positive /
6 negative queries, isolated tmp roots, keyless.

| metric | 2026-07-20 (run 1) | 2026-08-28 | delta |
|---|---|---|---|
| hit@1 | 25/26 (96%) | 24/26 (92%) | −1 query |
| hit@3 | 26/26 (100%) | 26/26 (100%) | unchanged |
| FP rate (D3) | **0/6 (0%)** | **2/6 (33%)** | **regressed** |
| threshold (min correct-positive top-1) | 3.0 | 3.5 | — |

**The run-1 verdict's load-bearing sentence — "ranking is accurate at
k=3 with zero false-positive over-confidence on no-match queries" — is
now false on its second clause.** Retrieval is unaffected: hit@3 is
still 26/26, so when the answer exists the corpus still surfaces it.
What degraded is the ability to tell that an answer does NOT exist.

**Probable cause: the retriever changed under us.** `attune-rag` was
locked 1.0.0 and then 1.1.0 on 2026-08-10 (#2033, #2034 — the latter
titled "abstention-by-default + confidence-gated retrieval"), both AFTER
run 1 on 2026-07-20. `KeywordRetriever` lives in that dependency, not in
this repo, so the scorer moved between baseline and re-run. Corpus drift
is not excluded but the dependency bump is the stronger hypothesis and
was not chased further.

**Concrete: one document is acting as an attractor.** Both false
positives resolve to the SAME topic at an IDENTICAL score:

- "which GraphQL schema versioning scheme do we use?" → `status-vocabulary` · 5.0 · FP
- "which CSS framework does the marketing site use?" → `status-vocabulary` · 5.0 · FP

Neither query shares subject matter with that document. At run 1 the
same six negatives produced three zero-hit results and three weak hits
(2.5) below a 3.0 threshold.

**Ruling (chair, 2026-08-28): record the measurement, do not fix.** The
run-1 decision to leave precision alone rested on the premise
"`attune.memory.PersonalMemory` is still lightly used". That premise was
previously unquantified; it is now measured and it HOLDS:

    ~/.attune/telemetry/memory_events.jsonl — 6,870 events
      lesson_recall   2,070      session_recall  1,559
      jit_recall      1,439      memory_signal   1,436
      personal_query     45   <- 0.65% of memory traffic

The surfaces carrying >99% of recall traffic are the hook/Redis paths,
not `PersonalMemory.query`. Tuning a keyword-overlap formula against an
18-document synthetic corpus to serve 0.65% of traffic — where ranking
is already perfect — is not a trade worth making today.

**Trip-wire (revisit when EITHER fires):**

1. `personal_query` exceeds ~5% of events in
   `memory_events.jsonl`, or
2. `PersonalMemory` gains a production consumer beyond the CLI
   (`cli_commands/memory_commands.py`) and the four
   `personal_memory_*` MCP tools.

**Fix direction — corrected 2026-08-28 by measurement, after an
earlier draft of this entry recommended the wrong thing.** The first
recommendation here was an "abstain path": surface a bounded confidence
and let `query()` return empty below a threshold. `RagResult` ALREADY
carries a bounded `confidence` (plus `fallback_used`), and
`PersonalMemory.query()` ([personal.py:285-294](../../../src/attune/memory/personal.py#L285))
discards it, ranking on raw `hit.score` instead — so the fix looked like
a few lines. Measured against this benchmark's own corpus and queries,
using the EXACT pipeline construction `personal.py` uses
(`DirectoryCorpus(root, summaries_file=_SUMMARIES_FILE, glob="**/*.md")`):

    confidence, positives (n=26): 0.875 x2, 1.0 x24
    confidence, negatives (n=6) : 0.0 x1, 0.5 x3, 1.0 x2

**Two of six negatives score confidence 1.0** — maximum confidence on
questions the corpus cannot answer. The minimum positive (0.875) sits
BELOW the maximum negative (1.0), so any threshold excluding the
negatives drops all 26 true positives. Confidence is not an abstain
signal on this corpus; it is over-confident on exactly the queries that
fail. (Constructing the same pipeline WITHOUT `summaries_file` moves
those two negatives from 1.0 down to 0.5 — the summaries file is
implicated in the over-confidence and is the first thing to look at.)

The remaining lever is the RETRIEVER, not the score. `attune-rag` 1.1.0
already ships `EmbeddingRetriever`, `HybridRetriever`,
`TransformerRetriever`, `LLMReranker` and `QueryExpander`, and
`RagPipeline(corpus, retriever, expander, reranker)` takes them as
constructor arguments — `PersonalMemory` passes none of them and gets
the `KeywordRetriever` default. Keyword-only retrieval failing on
"which X do we use?" phrasings that share generic vocabulary with an
unrelated document IS the documented failure mode, and semantic or
hybrid retrieval addresses it by construction. That is a configuration
change before it is a code change, but it adds a real dependency and
latency cost, so it needs its own measurement — not adoption on faith.

**Methodology warning for the next reader, learned the hard way in this
session.** There are TWO benchmark scripts and they are NOT
interchangeable:

- `scripts/eval_personal_memory_recall.py` — 26 positive / 6 negative.
  **This is the one run 1 used; it is the only valid baseline
  comparison.**
- `scripts/memory_recall_eval.py` — 18 positive / 5 negative, adds
  `--phase persistence` (run 3, cross-process).

They have different corpora and different query sets. This session first
compared the second script's output against run 1's numbers and derived
a "score separation regression" that was an artifact of comparing two
different benchmarks. Always re-run the SAME script whose numbers you
are comparing against.

For completeness, the other script's run today (not comparable to run 1,
recorded only so the number exists): hit@1 18/18, hit@3 18/18, and
identical results under `--phase persistence`, confirming recall
survives process death.
