# Decisions: attune-verify — Generation Fact-Checker

Design decisions for [attune-verify](requirements.md) beyond the
Phase-1 requirements and Phase-2 design. Newest first.

---

## D1 (2026-06-04): Deterministic resolution is authoritative for entity existence; the semantic judge must be cross-checked against it
**Status:** approved — folds into a `design.md` Phase-2 revision and a
`tasks.md` item.

### Evidence — dogfood, 2026-06-04

Regenerated six stale attune-ai help features
(`cli`, `release-prep`, `memory`, `agents`, `models`,
`configuration`) through attune-author's LLM polish pass, then judged
each `reference.md` with attune-rag's
`FaithfulnessJudge.score(query, answer, passages)` against the feature
source — the exact rag-adapter path `design.md` specs. Every flagged
"unsupported" claim was then cross-checked against the **complete,
untruncated** source tree (grep for `def`/`class`):

| feature | judge score | flagged | real-in-source | genuine hallucinations |
|---------|-------------|---------|----------------|------------------------|
| cli | 0.927 | 7 | 7 | 0 |
| release-prep | 1.000 | 0 | 0 | 0 |
| memory | 1.000 | 0 | 0 | 0 (51 source files dropped from context) |
| agents | 1.000 | 0 | 0 | 0 |
| models | 1.000 | 0 | 0 | 0 |
| configuration | 0.975 | 2 | 2 | 0 |

**All 9 flagged claims were false positives** — real symbols the judge
could not see because they fell outside its `passages` window.
attune-author's polish was actually 100% faithful on all six features.
The dogfood used attune-rag **0.1.23 unmodified**; no rag change was
needed to consume `FaithfulnessJudge`.

### The finding

The semantic judge's accuracy on **entity-existence** claims is
bounded by the completeness of `passages` — and that bound breaks
exactly where it matters most. High-file-count features (`memory` = 75
source files) overflow any context window, so the judge confidently
reports real symbols as "unsupported." A naive **union** of
deterministic and semantic findings would surface every one of these
as a hallucination: the tool cries wolf precisely on the largest, most
valuable targets.

The deterministic checkers have **no such bound**.
`importlib.find_spec`, AST resolution, captured `--help`, and
filesystem stats check against the **real environment**, not a window.
A symbol either resolves or it does not.

### Decision

**Deterministic resolution is authoritative for "does this named
entity exist?" The semantic layer is operationally barred from being
the thing that flags an entity as fake.** Two parts:

1. **Division of labor (reaffirms `requirements.md`, now
   load-bearing).** The semantic layer judges only the meaning-level
   class the deterministic checkers cannot — insecure examples,
   missing security notes, ungrounded claims, semantic mismatch.
   `requirements.md` already scopes it this way *in intent*; today's
   data shows the boundary must be **enforced operationally**, because
   `FaithfulnessJudge` does not respect it on its own (it flagged
   entity-existence claims in every run that had any).

2. **Cross-check suppression (the enforcement mechanism).** Any
   semantic finding whose evidence names an entity that the
   deterministic resolvers **can** resolve is **suppressed as a
   context-truncation false positive** — not surfaced. This is what
   made today's "0 hallucinations" result trustworthy.

### Implementation — carries to design.md / tasks.md

- **v1 (pragmatic):** run both layers, then post-filter — drop any
  semantic finding whose named entity resolves deterministically.
  Cheap; ~the grep-rescue prototyped today.
- **v2 (by construction):** scope the judge prompt to non-entity
  claims, and/or classify each semantic claim (entity-existence vs
  meaning) and route entity claims to the deterministic resolver.
  Eliminates the false-positive class upstream rather than filtering
  it after.
- **`design.md` gap to fix:** the current design presents the
  deterministic and semantic layers as **parallel and independent**
  ("a failure in one does not abort the others" — union semantics).
  This decision makes them **compose**: the deterministic layer
  disciplines the semantic one. The "Public API" and data-model
  sections need a Phase-2 revision describing the suppression step.

### Side findings worth recording

- Three features (`release-prep`, `agents`, `models`) judged with
  **0 supported and 0 flagged** — the judge found no checkable
  structural claims in their `reference.md`. That is a **content**
  signal (thin or non-structural reference docs), not a faithfulness
  signal; "score 1.0" there is degenerate. A real verify run should
  report "0 verifiable entities" distinctly from "all entities
  verified."
- The composition is attune-verify's value-add, not new judging.
  rag grounds and judges; attune-verify brackets the output by making
  deterministic existence authoritative over the judge.

### Status reconciliation — flagged, not resolved here

`design.md` and `tasks.md` headers read "Phase 2/3, awaiting review"
(2026-06-02), but `~/attune-verify` already has `src/`, `tests/`, and
the author-#351 regression fixture committed. Implementation has
started; the spec status should be reconciled with reality (per the
`spec-status-self-truthing` concern). Out of scope for this decision —
noted for a status pass.

---

## D-T7 — author integration: keep both, defer consolidation (2026-06-09)

**Context.** T7 was framed as "wire `attune_verify.verify()` into
attune-author's polish pass (return, not hard-gate)." Investigating it
after shipping attune-verify 0.2.0 found the premise is **obsolete**:
attune-author **already fact-checks post-polish via its own mature
`fact_check/` subsystem** (its own `polish-fact-check` spec).

**What author already has** (verified in `~/attune-author`):

- `generator._run_fact_check()` runs after every polished file
  (`generator.py:619`); CLI exposes `--fact-check` / `--no-fact-check`.
- Modes via `ATTUNE_AUTHOR_FACT_CHECK`: `soft` (default — appends an
  `## Unresolved references` block), `strict` (raise `FactCheckError`,
  opt-in), `off`. Opportunistic — never breaks the polish pipeline.
- A 1191-LOC subsystem: `check_polished_file()` →
  `FactCheckReport`/`FactCheckConfig` (per-project config from
  `pyproject.toml`, per-file skips), `report.py` formatting,
  `apply_soft_fail`, plus **five** checks — `python_refs` (resolves full
  dotted paths + attributes), `cli_refs` (version-aware `--help`),
  `md_links`, `numeric_refs`, and `tutorial_static_check` (a
  static-analysis check attune-verify does not have).

So author's polish **already does exactly what T7 specified** — just via
its own implementation, not the `attune_verify` library. With the 0.2.0
backport (full dotted-path resolution), the two are now at **functional
parity on the four shared checks**.

**Decision: keep both; do NOT force author to delegate now.**

- **attune-verify** stays the standalone family library for *other*
  consumers — the attune-ai `/verify` skill, future external users, and
  the semantic/Judge + rag layers author lacks.
- **author `fact_check/`** stays as author's integrated, richer,
  already-shipped subsystem (config, report formatting, soft-fail block,
  tutorial static check).
- Forcing author to delegate to `attune_verify` today would be a
  **downgrade** (lose `tutorial_static_check`, report/config richness)
  unless attune-verify first absorbs those — a multi-release effort with
  no acute pain to justify it.

**T7 disposition: satisfied-independently / consolidation deferred.**
The integration T7 called for already exists; the *real* remaining work
is consolidation, tracked below as future, not blocking.

**Future path (option C, when it bites).** Single source of truth =
attune-verify absorbs author's richness (`tutorial_static_check`,
config-from-pyproject, report/soft-fail formatting), then author's
`fact_check/` becomes a thin delegation shim. Gate this on a real
trigger: drift pain between the two implementations (the "two parallel
generators drift" lesson), or a third consumer needing the richer
surface. The 0.2.0 backport already narrowed the drift surface (imports
now match).

**Drift mitigation until then.** Both resolve imports/flags/links/counts;
the 0.2.0 backport aligned the import checker. If they diverge again,
prefer porting the improvement into *both* (cheap) or starting the
consolidation (option C). A periodic parity check across the two
`python_refs`/`imports` checkers is worth a follow-up if drift recurs.
