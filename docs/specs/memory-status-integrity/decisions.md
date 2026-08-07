# memory-status-integrity — decisions

Chair: Patrick. Decisions are recorded when made, with the evidence that
drove them, so a later session can tell a ruling from a habit.

---

## D1 — Label, never suppress by age (recorded 2026-08-07)

**Question (requirements OQ4):** past some unverified-age threshold,
should a curated memory stop being injected at SessionStart and move to
recall-on-demand only, or should it only ever be labelled?

**Ruling:** **Label. Never suppress by age.** No curated memory is
removed from service by a clock. The only thing that takes a memory out
of circulation is a human `wrong` verdict (R3) — a decision, not an
elapsed interval.

Patrick delegated this call on 2026-08-07 and asked for the reasoning to
be recorded.

### The decisive evidence: age is anti-correlated with wrongness

The obvious design — expire what's old — assumes age predicts falsity.
Measured against the live corpus, it predicts the opposite.

Type composition of the oldest bucket (36 files, all stamped
2026-06-02):

| Type | Count |
|---|---|
| `feedback` | 30 |
| `user` | 5 |
| `lesson` | 1 |

35 of 36 are settled process rules and user profile — the memories least
likely to be false and most expensive to lose. `feedback_one_question_at_a_time`
(surfaced 2026-05-21) is among the oldest files in the corpus and is
still exactly true; it governed the shape of the very conversation that
produced this spec.

Meanwhile, both memories that actually rotted were `project_*` and
comparatively young:

| Rotted memory | Age when it misled |
|---|---|
| `project_pip_audit_broken` | ~8 weeks |
| `project_rag_gate_corpus_stale` | **hours** |

An age threshold tuned to catch the 8-week case would not have touched
the hours-old case. A threshold tuned to catch the hours-old case would
evict essentially the entire corpus, starting with the `feedback` rules
that make the agent usable.

**Age-based suppression would silence the safest memories and retain the
dangerous ones.** That is not a tuning problem — the mechanism points the
wrong way, and no threshold fixes a sign error.

### Supporting argument 1 — the error costs are asymmetric

| Failure | Cost | Visibility |
|---|---|---|
| Labelled memory is over-trusted anyway | status quo, plus a warning | visible, recoverable |
| A **true**, load-bearing memory is suppressed | session re-derives or contradicts a settled decision | **silent, unrecoverable** |

Suppression converts a loud failure into a quiet one. That is precisely
the absence-as-success class R5 and R6 exist to eliminate — a capped or
filtered result that reads as "nothing here" is indistinguishable from
"nothing stored."

### Supporting argument 2 — suppression destroys the review loop

D6 of `curated-memory-productionization` fixed the durable tier's regime
as **human review verdicts**. A verdict requires a human to see the
memory. Suppress it and it can never be reviewed: the corpus silently
bifurcates into *served* and *forgotten-but-present*, and rot becomes
invisible rather than repaired. Suppression does not implement D6's
regime; it starves it.

### Supporting argument 3 — labelling demonstrably works on this reader

The reader of a curated memory is a model, so "does the label work?" is
an empirical question, not a matter of taste.

Receipt from the originating session (2026-08-06): the harness stamped
`This memory is 27 days old… Verify against current code before
asserting as fact` on a memory file read during the investigation. It
changed the agent's behavior in-session — a downstream claim sourced
from `product.md` was hedged and flagged for verification rather than
asserted. The label lands because it is in context at the moment of use,
which is exactly where a staleness signal has leverage and an offline
expiry policy has none.

### The strongest counter-argument, and why it loses

**Context budget is real.** SessionStart hydrated 989 lessons in the
originating session; the curated corpus is 266 files. Injecting
everything forever is not free, and suppression is the obvious lever.

It loses because it treats a **volume** problem as a **staleness**
problem. The two are independent, and the type-composition data shows
what happens when they are conflated: expiry evicts the cheapest,
highest-reuse rules first, because those are the oldest. Volume is
solved by ranking and relevance (R6), which reduces what is *served*
without deciding what is *true*.

### The binary was false — the third path

The question offered label-or-suppress. The design takes neither
extreme:

> Staleness × recall-frequency escalates a memory to a **review
> prompt** — a request for a verdict — not to suppression.

High-risk memories get *more* attention, not less. This is the only one
of the three options that actually advances D6's regime, and it inverts
suppression's failure mode: instead of quietly removing a memory nobody
reviews, it loudly surfaces the memory most in need of review.

### Consequences

- No age threshold anywhere in the design removes content from a recall
  result or from SessionStart injection.
- R2's annotation is mandatory on every surface; it is the entire
  mitigation for the label-only posture and cannot be deferred.
- The acceptance test pins this: a change that starts suppressing by age
  must fail loudly (see requirements § Acceptance, row 2).
- Revisit only on evidence that labels are being ignored in practice —
  i.e. a recorded instance of an agent asserting a visibly-labelled
  stale claim as fact. Absent that receipt, this stays settled.

---

## D2 — P2's cost objection withdrawn; the premise was false (recorded 2026-08-07)

The requirements originally argued that adding a `verified:` key was
expensive because `memory_lint.py` is vendored across the four-sibling
hook closure tracked by `project_hooks_canonical_drift`, so a schema
change would require a closure re-sync.

**Measured: false.** `memory_lint.py` exists at exactly one path,
`~/.claude/hooks/memory_lint.py`, with a co-located `test_memory_lint.py`.
It is present in none of the five repos (attune-ai, attune-rag,
attune-gui, attune-help, attune-author).

The schema amendment is one file and one test. P2 is materially cheaper
than the requirements claimed, and the phase split is now justified by
*sequencing* (P1 needs no schema at all) rather than by cost avoidance.

Recorded because the false premise was load-bearing in the original
phase argument, and a later reader would otherwise inherit it.

---

## D4 — The enforcement code is the authority, not the prose (recorded 2026-08-07)

Three claims in the requirements draft were derived from documentation
and were false. Each was caught only by running the thing:

| Claim | Source of the error | Reality |
|---|---|---|
| "7 schema violations" | `~/.claude/CLAUDE.md` says no keys beyond the fixed set | `memory_lint.py:188-194` deliberately tolerates provenance keys; **1** violation corpus-wide |
| "a write-triggered linter can never find pre-existing drift" (R5) | inferred from the hook's PostToolUse registration | `--check-all` + `all_memory_dirs()` already exist |
| "the corpus is clean, 0 violations" | read `--check-all` output through `tail -25` and never saw the first block | 1 violation — a missing `MEMORY.md` pointer |

**Ruling:** where prose and enforcement code disagree about a rule, the
code is authoritative and the sweep must match it. `curated_audit.py`
now mirrors the linter's provenance tolerance and its "a bare `stem.md`
mention counts as indexed" rule, with the reasons recorded at both call
sites so a later reader does not re-tighten them.

**Why this is recorded rather than quietly fixed:** the failure mode is
the spec's own subject. A confident claim, sourced from a stale
document, survived into a requirements doc and was nearly built on. The
third row is worse than the first two — that one was not a bad source
but a truncated command, an unforced error of the kind that produces
false "all clear" reports.

Two mitigations fall out of this and are already in the design:

- The live-corpus **receipt** (not a test) is what caught all three. It
  stays mandatory before any claim about corpus state.
- Agreement between two independent implementations is a signal worth
  keeping. `curated_audit` and `memory_lint` now cross-check each
  other; on the first clean run they found the same single violation.

---

## D3 — The sweep is a library in attune-ai, not a personal script (recorded 2026-08-07)

There are two curated corpora with different owners:

| Corpus | Files | Owner |
|---|---|---|
| `~/.claude/**/memory/` | 266 | harness-native; linted by a personal hook outside every repo |
| `~/.attune/memory/` | 16 | attune-shipped (`src/attune/memory/personal.py`) |

Writing the sweep as a personal script would fix Patrick's corpus and
ship nothing. Writing it only against `~/.attune/memory/` would ship a
feature exercised by 16 files while the 266-file corpus keeps rotting.

**Decision:** the mechanism lands in attune-ai as a **path-parameterized
library** over "a directory of frontmattered markdown memories," with
both corpora as callers. The personal hook calls into it; the product
uses it for its own store.

This also gives P1 an honest test surface: the logic is exercised by
hermetic fixtures, and the 266-file corpus becomes a *receipt* run
rather than a test dependency — real-corpus assertions in CI would
violate the home-directory isolation guard
(`project_test_isolation_home_dir_leaks`).

---

## D5 — Post-merge review findings and their fixes (recorded 2026-08-07)

A fresh-model review of the merged P1 (#1975) found three divergences,
two of them instances of the failure classes this spec exists to catch.
Fixed in the review follow-up PR; recorded so the pattern is legible.

1. **The sweep violated D4 itself.** `KNOWN_TYPES` included `lesson`,
   which the canonical linter's `ALLOWED_TYPES` rejects — so a
   `type: lesson` file activated provenance tolerance and became
   invisible to the sweep while the linter flagged it twice. Worse, the
   sweep never validated `metadata.type` at all, and for
   `~/.attune/memory` (no linter) the sweep is the only checker. Fix:
   `LINTER_ALLOWED_TYPES` mirrors the linter exactly; present-but-invalid
   types are reported (`invalid_types`); missing types deliberately are
   not (sweep roots may include non-curated-schema corpora where the
   linter claims no jurisdiction — value-drift is unambiguous, absence
   is not). `lesson` stays in `VOLATILITY_BY_TYPE`: ranking tolerance
   ≠ schema tolerance.

2. **R2 was marked done while half-delivered** — tasks.md row 5 said
   "done" with `recall_digest.py` and the hydration line unshipped:
   spec-status drift inside the anti-drift spec. Fix: digest cards now
   carry the age label (from `updated_at` — Redis nodes have no file
   path), row 5 split into 5a/5b/5c with honest statuses, and the
   hydration line recorded as external with its one-liner documented.

3. **Latent parser divergence (not yet fixed, tracked):** indented
   continuation lines outside `metadata:` (folded multi-line YAML
   `description: >`) parse as top-level keys and would false-positive;
   the canonical linter counts only non-indented keys. Zero live hits
   across the 271-file receipt, so deferred — P2 touches the parser
   anyway for `verified:` and should align this then.

Meta: the reviewer that caught these is the same class of reader the
age labels serve — the D4 lesson generalizes to "re-derive claims from
the artifact, not from the session that produced it."

---

## D6 — P2 scope, ratified from round-table `q-memory-system-deep-dive-001` (recorded 2026-08-07)

A three-model round table (Claude + Codex + Antigravity, 2 rounds)
deliberated the P2 design. Round 1 split three ways on the ranking
signal; round 2 converged. The chair promoted the converged scope.
Full transcript: `~/.attune/reports/roundtable/q-memory-system-deep-dive-001.md`.

**The motivating evidence (decisive, all seats):** the memory that
rotted *within hours* (`project_rag_gate_corpus_stale`) was project-type
at age ~0 — age × volatility ranked it **last on its most dangerous
day**. Project facts rot on *events* (commits, merges, closed issues,
moved paths), not on the clock. Age is the wrong primary signal for the
one type that rots fastest.

### Ratified P2 scope (the union every seat endorsed)

1. **Fix the frontmatter-parser divergence FIRST — promoted from
   "deferred" (D5 item 3) to a P2 gate.** `verified:` lives in
   frontmatter; if the audit parser and the canonical linter disagree on
   folded multi-line YAML, the field the whole loop depends on is
   unreliable on exactly the drifting files. Unanimous blocker.
2. **`verified:` as strict ISO date, distinct from mtime, human-set
   only**, plus **content-digest binding**: a substantive edit
   invalidates verification; a formatting-only change (canonicalised)
   preserves it. Keep an **append-only verdict history** (who / when /
   what-digest), not a bare mutable date — the failure mode to design
   against is a thoughtless "keep all" freshness button.
3. **keep / wrong / sharper verdict loop.** `wrong` **tombstones**, does
   not delete — deletion breaks `MEMORY.md` pointers and `[[links]]`,
   and "we believed X, it was wrong because Y" is itself high-value
   memory. `sharper` = edit + verify in one motion, name-stable.
   **Verdicts propagate to Redis immediately** (invalidate/rewrite the
   key), or a session recalls known-wrong memory for a full hydration
   cycle — failing the spec's own goal.
4. **Ref-triggered queue-jump for project-type memories.** Typed refs
   (`file:` / `sha:` / `pr:` / `issue:`) resolved by an **existence
   check** against local git (optionally `gh`) → flip to "review",
   floated above the age-ranked queue, trigger reason exposed. Sits
   inside D1 (only promotes into review, never demotes or hides) and D6
   of `curated-memory-productionization` (routes to a human, never
   auto-certifies).
5. **Render epistemic STATUS, not just age.** "N days unverified" is a
   number without calibration — the reading model has no base rate for
   90 days on reference vs project. Render a discrete tier
   (**settled / check-before-acting / suspect**) plus author-class and
   verification-state, and for "suspect + project" an explicit "verify
   against repo before acting" instruction on the card. **The raw tier
   (least trustworthy) currently has the least labelling and needs the
   strongest framing** — cross-links `memory-security-hardening` R1.

### Unresolved sub-decision left to the chair at design time

The one residual split, both sides inside D1/D6 — a one-line ranking
choice, not a blocker:

- **Ref-trigger as PRIMARY signal for project-type** (Codex,
  Antigravity), age × volatility demoted to tiebreaker; **vs.**
- **Ref-trigger as a cheap queue-jump BOOLEAN** layered on the
  age × volatility baseline (Claude) — verdict loop ships first, the
  boolean is an existence check only, fail-open, and is *cut entirely*
  if its implementation creeps toward the sibling spec's diff engine.

And the evidence source: **local-git-only** (Antigravity, keeps P2
self-contained) vs **allow `gh` for `pr:`/`issue:`** (Codex/Claude,
single existence check per ref, fail-open on unreachable).

**Moderator note:** Claude's boolean-with-hard-cap is the lower-risk
first cut — its hit-rate becomes the evidence that justifies building
the full ref engine in `memory-claim-verification`. But this is the
chair's call and both are ratifiable; recorded here unresolved rather
than forced.

### The binding constraint every seat named

The system's scarce resource is **one human's attention**. A stale
`verified:` date is **worse than none** (false endorsement), so
verified-age must re-enter ranking, never exempt a file; cap the review
queue (~3 per triage); one-keystroke verdicts. If P2 ceremony gets
abandoned, the corpus fills with stale endorsements — a worse end-state
than today's honest "unverified". Design for abandonment.
