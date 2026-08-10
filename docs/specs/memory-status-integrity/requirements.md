# memory-status-integrity

**Status:** approved (2026-08-09) — chair approved advancing past
requirements; OQ2/OQ4 resolved, R5 retired; P1 shipped; P2 opened
with both residual rulings (D7), attune-ai side complete; P3 opened
with the measure-first gate executed (D8 — curated serve telemetry
must be instrumented before the ranking term; OQ3 pulled into P3)
**Owner:** Patrick (chair)
**Origin:** Banked 2026-07-10 as a named future spec in
`project_memory_layer_audit_todo`, gated on `spec-status-integrity`
shipping. That gate closed 2026-07-11 (10/10, attune-ai #1317).

**Sibling:** [memory-claim-verification](../memory-claim-verification/requirements.md)
owns the **raw auto-stashed tier** and names the curated tier a non-goal.
This spec is that non-goal, scoped. The two must not converge — see
"The regime is fixed" below.

---

## Problem

The curated tier (`/remember` → markdown under `.claude/**/memory/`,
indexed by `MEMORY.md`, hydrated into Redis at SessionStart) has **no
concept of verification.** Files carry a creation date by mtime and
nothing else. Nothing re-reads a curated claim against reality, and
nothing tells a reading session how long it has been since anyone did.

Unlike the raw tier, there is no TTL, no recency decay, and no rejection
counter. A curated memory is written once and served with full authority
forever.

### Measured drift, 2026-08-06

Live count over the global corpus (`~/.claude/memory/`) plus the attune
project corpus:

| Signal | Measurement |
|---|---|
| Curated memories linted by `memory_lint.py --check-all` | **269** across 13 corpora |
| Total swept (adds `~/.attune/memory/<topic>/`) | 271 |
| **Schema / link / pointer violations** | **1** (a missing `MEMORY.md` pointer) |
| Largest single corpus (`projects/…-attune-ai/memory`) | 107 files |
| attune project corpus (26 files) — days since any write | 26 (last: 2026-07-11) |
| Files last written 2026-06-02 / 2026-07-02 (global corpus) | 36 / 27 |

### Correction, 2026-08-07 — the integrity premise was false

An earlier draft claimed 7 schema violations and argued that "the corpus
drifted from its own schema" because `memory_lint.py` is a PostToolUse
hook that can only lint on write. **Both claims were wrong**, and the
error is worth recording because it is the exact failure this spec
exists to prevent — a confident assertion derived from a document
rather than from the enforcement mechanism.

- The 7 files carry `node_type:`, which `~/.claude/CLAUDE.md` describes
  as forbidden. The **linter deliberately tolerates it**
  (`memory_lint.py:188-194`): it is provenance injected by the Claude
  Code auto-memory graph, and is flagged only when used as a
  *substitute* for `metadata.type`. The prose is a simplification; the
  code is the authority.
- `memory_lint.py` **already has** `--check-all` and `all_memory_dirs()`,
  which sweeps every per-project corpus. A comment records a 2026-07-02
  fix for precisely the gap the draft claimed was open.
- Running the real thing: **1 violation across 269 files.**

**What survives, and is now the sharper argument:** the corpus has
essentially no schema, link, or pointer rot. Structural integrity is
already solved and already swept. The *only* untracked failure mode left
is the one nothing measures — whether a claim is still true. That is a
narrower and better-motivated problem than the one the draft described.

Two readings from the measurement still stand, because both were
observed directly rather than inferred:

1. **Writes are bursty, not organic.** 63 files in the global corpus
   share two timestamps. Those are bulk migrations, not acts of
   confirmation — which is exactly why mtime cannot stand in for
   verification.
2. **The attune project corpus is 26 days cold** while PRs #45–#50
   shipped in that window. Every one of those 26 files asserts a July
   world, and nothing anywhere records that fact.

### The two proof cases (2026-07-10)

| Memory | Failure |
|---|---|
| `project_pip_audit_broken` | Claimed attune-ai CI red since May. Green since ≤2026-07-08. Was about to be repeated to Patrick as pushback; a one-command verify caught it. Deleted same day. |
| `project_rag_gate_corpus_stale` | Said "full-25 go/no-go pending" *hours after* attune-author #96 completed. Nearly triggered a duplicate $3–8 API spend. |

**These two cases point in opposite directions, and that is the whole
design.** The pip-audit memory rotted over ~8 weeks — that is a
staleness problem this spec owns. The rag-gate memory was wrong within
**hours** — no age-based mechanism can catch it, and pretending
otherwise is how this spec fails. Operational truth belongs to the
short-term regime.

---

## The regime is fixed

**D6** of `curated-memory-productionization` (complete, 2026-07-03)
ratified that the two layers fail in opposite ways and need opposite
truth-maintenance regimes:

- **Operational / short-term** — stale is *worse than nothing* (a stale
  "merge PR X" causes a wrong action). Regime: **machine verification
  against ground truth at load time.**
- **Durable / curated** — stale *fails softly*. Regime: **human review
  verdicts over time (keep / wrong / sharper).**

Merging them "would drown the review loop in expiring churn AND leave
operational truth policed by a mechanism too slow for it — breaking
both."

**Consequence for this spec:** machine-verifying curated claims is
excluded by prior decision, not by preference. This spec surfaces
staleness and collects human verdicts. It never auto-edits, never
auto-expires, and never adjudicates whether a curated claim is true.

**D8**'s barbell verdict adds a delivery constraint: hook-driven layers
demonstrably empower in-session; the structured layers (MemoryGraph,
personal memory, Redis-via-MCP) are "mature but unoccupied — empty
stores, and failures go unnoticed." **This ships on the hook path.**

---

## The principle: age is not the signal — unreviewed-ness is

A curated memory's risk is a function of time since the last **human
verdict**, not time since creation or time since last edit.

mtime is the wrong proxy in both directions:

- Reformatting a memory, or a bulk migration, makes a false claim look
  freshly confirmed. 63 of 110 files have exactly this problem.
- Re-confirming a memory *without editing it* — the most common
  verification outcome — leaves no trace at all.

**Requirement: a curated memory must record when a human last rendered
a verdict on it, and every surface that serves it must show how long
ago that was.**

---

## Requirements

### R1 — `verified:` is a first-class, distinct field

Curated frontmatter gains `verified: <ISO date>`, separate from creation.
Additive and backward compatible: absent `verified:` reads as
"never verified", which is the honest default for all 110 existing files.

`memory_lint.py` enforces an exact, closed key set ("No `node_type`, no
top-level `type:`, no other keys"), so adding a key requires amending
the linter.

**Correction (2026-08-07, measured):** an earlier draft of this
requirement claimed the linter is part of the vendored sibling closure
tracked by `project_hooks_canonical_drift`, making P2 expensive. That is
**false**. `memory_lint.py` exists at exactly one path —
`~/.claude/hooks/memory_lint.py` — and in none of the five repos
(attune-ai, rag, gui, help, author). It has a local `test_memory_lint.py`
beside it. The schema amendment touches one file with one test, not a
10-file cross-repo closure. P2 is substantially cheaper than stated.
See OQ2.

### R2 — Every recall surface displays unverified-age

A reader must see staleness without having to ask for it:

```
[project] attune-ai specs live in docs/specs/   ⟨61 days unverified⟩
```

The harness already does this for direct file reads — an unprompted
`This memory is 27 days old… Verify against current code before
asserting as fact.` banner appeared on 2026-08-06. That is proof of
concept, and it covers exactly one surface.

The surfaces attune owns and must cover:

- `/recall` and `session_memory_recall`
- the SessionStart hydration line — it announced **989 lessons** this
  session with no age signal on any of them
- `MEMORY.md` index rendering, where the pointer is often all a session
  reads

### R3 — Verdicts are recorded, not inferred

Per D6 the regime is human verdicts. Three outcomes, each with a
distinct effect:

| Verdict | Effect |
|---|---|
| **keep** | stamp `verified:` = today. No content change. |
| **wrong** | delete the file *and* its `MEMORY.md` pointer, atomically. |
| **sharper** | edit content, stamp `verified:`. |

"keep" is the load-bearing one: it is the only way a true-but-old memory
can become fresh without being edited, and its absence today is why
mtime lies.

### R4 — The sweep is advisory and never writes

A `--check-all`-style sweep over the corpus reports, and only reports:

- unverified-age distribution, ranked (R6)
- schema violations in pre-existing files — the 7 known offenders are
  the receipt
- `[[link]]` integrity, including the `[[?slug]]` deliberate-unresolved form
- `MEMORY.md` pointer integrity in both directions: files with no
  pointer, pointers with no file

No auto-edit, no auto-delete, no auto-verify. The report is input to
R3's human loop.

**Scope note (2026-08-07):** for the harness-native corpus the integrity
checks duplicate `memory_lint.py`, which already reports them. They are
retained because the sweep also covers corpora that have **no** linter —
attune's own `~/.attune/memory/` store — and because agreement between
two independent implementations is itself a useful signal. On the first
live run they agreed exactly: both found the same single violation. The
genuinely new capability in R4 is the staleness ranking, not the
integrity checks.

### ~~R5 — Linting must be sweepable~~ — RETIRED 2026-08-07

**Already implemented.** `memory_lint.py` has `--check-all` and
`--fix-all`, and `all_memory_dirs()` covers the global corpus, every
per-project corpus, and attune's curated store. The premise that a
write-triggered linter could never find pre-existing drift was false.

The hook is deliberately left untouched: it is stdlib-only and
fail-open, and importing attune into it would cost both properties for
no gain. Staleness is served by a separate advisory sweep (R4).

### R6 — Review budget is bounded by rank, not by corpus size

110 files is more than anyone will review, and D6 warns explicitly about
drowning the review loop. The sweep must **rank** rather than enumerate:
staleness × how often the memory is actually served.

A 200-day-unverified memory nothing ever recalls is near-zero risk. An
8-week-old memory injected into every session — which is precisely what
`project_pip_audit_broken` was — is the whole problem. Unranked output
is a wall that gets ignored, which is indistinguishable from no sweep.

---

## Acceptance — pin both directions

The regression replays the two 2026-07-10 proof cases, and **must
produce opposite outcomes**:

| Case | Required outcome |
|---|---|
| `project_pip_audit_broken` (8 weeks stale, high recall) | surfaces **top-ranked** in the sweep, and carries a visible unverified-age at recall, before it can be repeated |
| `project_rag_gate_corpus_stale` (wrong within hours) | **NOT flagged by this mechanism** — it was hours old. The test pins that the curated sweep does not claim it. |

A change that catches both is as wrong as one that catches neither: the
second row is a boundary marker. If a later change makes the curated
sweep start machine-verifying claims in order to catch the rag-gate
case, this test must fail loudly — that is the D6 violation, and it
breaks both layers. Same discipline as
`tests/unit/ci/test_platform_compat_scanner.py`, where every
false-positive class is paired with its true positive.

Additional receipts:

- **Live-corpus receipt, not mocked** — the sweep runs against the real
  110-file corpus and reports the 7 known `node_type` violations. A
  mocked corpus would pass by construction.
- **Backward compatibility** — all 110 existing files, none of which
  have `verified:`, lint clean and recall correctly as "never verified".
- **No writes** — the sweep leaves the corpus byte-identical. Assert on
  hashes before and after.

---

## Non-goals

- **Machine-verifying curated claims.** Excluded by D6, not by taste.
- **Auto-editing, auto-deleting, or auto-expiring any curated memory.**
- **TTL or recency decay on the curated tier.** That is the raw tier's
  model and it is wrong here — it deletes true-but-old memories while
  doing nothing about young-but-false ones.
- **The raw session-stash tier** → `memory-claim-verification`.
- **Operational handoff state** → the short-term reconciler path named
  in D6.
- **Improving what gets written.** Authoring quality is a separate
  problem from truth maintenance.

---

## Phases

**P1 — display unverified-age + advisory sweep (R2, R4, R5, partial R6).**
Independently shippable, zero enforcement, zero schema change if
unverified-age is derived from mtime as a stopgap. Catches the
pip-audit class immediately. Worth shipping alone.

**P2 — the `verified:` field and the verdict loop (R1, R3).** Carries
the schema amendment and the sibling-closure re-sync. This is where the
real cost is.

**P3 — recall-frequency ranking (full R6).** Needs recall telemetry that
may not exist yet; measure before building.

---

## Open questions

1. **Does `verified:` live in frontmatter or in the Redis/graph layer?**
   Proposal: **frontmatter** — it is diffable, survives a Redis flush,
   and D8 found the structured stores unoccupied. Redis stays a
   projection.

2. ~~**Schema-amendment blast radius.**~~ **RESOLVED 2026-08-07 by
   measurement.** The premise was false — `memory_lint.py` is not
   vendored anywhere; it lives only at `~/.claude/hooks/memory_lint.py`
   with a co-located test. One file, one test. The cost objection to P2
   is withdrawn.

3. **What drives the review cadence?** `spec-status-integrity` settled on
   a weekly issue. Symmetry argues for the same here rather than a new
   mechanism. Riding an existing hook also satisfies D8.

4. ~~**Label, or suppress?**~~ **RULED 2026-08-07 (Patrick delegated the
   call): label, never suppress by age.** Nothing is removed from
   service by a clock — only by a human `wrong` verdict. The decisive
   evidence is that **age is anti-correlated with wrongness in this
   corpus**: the oldest bucket (36 files, 2026-06-02) is 30 `feedback`
   + 5 `user` + 1 `lesson`, i.e. settled process rules and profile —
   the least likely to be false and the most expensive to lose. The two
   memories that actually rotted were `project_*` and young. Age-based
   suppression would evict the safest memories and retain the dangerous
   ones. Full reasoning and the rejected alternatives are recorded in
   [decisions.md](decisions.md) §D1.
